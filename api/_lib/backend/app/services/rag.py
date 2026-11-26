import os
import re
import math
import hashlib
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, select

from backend.app.config import settings
from backend.app.models import Document, DocumentChunk
from backend.app.schemas import RAGQueryResult

# Fallback response when no verified evidence is retrieved
RAG_FALLBACK_RESPONSE = (
    "I don't have verified information regarding this in our knowledge base. "
    "Would you like me to note this requirement for our solutions team, or discuss it during a scheduled demonstration?"
)

STOP_WORDS = {
    'what', 'is', 'the', 'of', 'in', 'to', 'for', 'a', 'an', 'and', 'are', 'per',
    'how', 'does', 'do', 'can', 'our', 'we', 'with', 'on', 'at', 'by', 'this', 'that', 'it'
}

def _generate_mock_embedding(text_content: str, dim: int = 1536) -> List[float]:
    """
    Generate a deterministic, normalized 1536-dimensional semantic vector
    based on word tokens and character n-grams. Allows pgvector cosine math
    to rank documents accurately without requiring external API calls.
    """
    vec = [0.0] * dim
    words = re.findall(r'\b\w+\b', text_content.lower())
    if not words:
        words = ["empty"]

    for word in words:
        is_stop = word in STOP_WORDS
        weight = 0.1 if is_stop else (2.0 + len(word))
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        for i in range(12):
            idx = (h >> (i * 5)) % dim
            vec[idx] += weight

        if len(word) >= 3 and not is_stop:
            for j in range(len(word) - 2):
                tri = word[j:j+3]
                ht = int(hashlib.md5(tri.encode("utf-8")).hexdigest(), 16) % dim
                vec[ht] += 0.5

    norm = math.sqrt(sum(x * x for x in vec))
    if norm > 0:
        return [x / norm for x in vec]
    return [0.0] * dim

def get_embedding(text_content: str) -> List[float]:
    """Retrieve embedding from OpenAI API or fallback to deterministic mock."""
    if settings.OPENAI_API_KEY and not settings.MOCK_MODE:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            resp = client.embeddings.create(
                input=text_content,
                model=settings.OPENAI_EMBEDDING_MODEL
            )
            return resp.data[0].embedding
        except Exception:
            # Safe fallback if API call fails
            return _generate_mock_embedding(text_content, settings.EMBEDDING_DIM)
    return _generate_mock_embedding(text_content, settings.EMBEDDING_DIM)

def chunk_text(content: str, chunk_size: int = 1800, chunk_overlap: int = 300) -> List[str]:
    """
    Split text into chunks of approx 500 tokens (1800 characters)
    with approx 75 tokens overlap (300 characters).
    """
    chunks = []
    start = 0
    content_len = len(content)

    while start < content_len:
        end = start + chunk_size
        if end >= content_len:
            chunks.append(content[start:].strip())
            break

        # Attempt to split on paragraph or sentence boundary
        split_idx = content.rfind("\n\n", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = content.rfind(". ", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = content.rfind("\n", start, end)
        if split_idx == -1 or split_idx <= start:
            split_idx = end

        chunks.append(content[start:split_idx].strip())
        start = max(start + 1, split_idx - chunk_overlap)

    return [c for c in chunks if len(c) > 20]

def extract_file_text(file_path: str) -> str:
    """Extract text from .md, .txt, or .pdf files."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in (".md", ".txt", ".json", ".csv"):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    elif ext == ".pdf":
        # Extract plain strings from PDF
        try:
            with open(file_path, "rb") as f:
                raw = f.read()
            # Simple text extraction for standard text streams
            text_parts = re.findall(rb'\(([^\)]+)\)\s*Tj', raw)
            if text_parts:
                return b" ".join(text_parts).decode("latin-1", errors="ignore")
        except Exception:
            pass
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

def ingest_document(
    db: Session,
    file_path: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    title: Optional[str] = None
) -> Document:
    """Ingest a single document, split into chunks, compute embeddings, and persist."""
    filename = os.path.basename(file_path)
    file_type = os.path.splitext(filename)[1].replace(".", "").lower() or "txt"
    content = extract_file_text(file_path)

    if not title:
        first_line = content.split("\n", 1)[0].replace("#", "").strip()
        title = first_line if first_line else filename

    # Remove existing document with same filename in tenant
    existing_doc = db.query(Document).filter(
        Document.tenant_id == tenant_id,
        Document.filename == filename
    ).first()

    if existing_doc:
        db.delete(existing_doc)
        db.flush()

    doc = Document(
        tenant_id=tenant_id,
        filename=filename,
        file_type=file_type,
        title=title,
        metadata_json={"source_path": file_path, "size_chars": len(content)}
    )
    db.add(doc)
    db.flush()

    chunks = chunk_text(content)
    for idx, c in enumerate(chunks):
        vec = get_embedding(c)
        token_count = max(1, len(c) // 4)
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=idx,
            content=c,
            token_count=token_count,
            embedding=vec
        )
        db.add(chunk)

    db.commit()
    db.refresh(doc)
    return doc

def ingest_knowledge_base_directory(
    db: Session,
    directory_path: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> List[Document]:
    """Ingest all markdown, txt, and pdf documents from a directory."""
    ingested = []
    if not os.path.exists(directory_path):
        return ingested

    for fname in os.listdir(directory_path):
        if fname.lower().endswith((".md", ".txt", ".pdf")):
            fpath = os.path.join(directory_path, fname)
            doc = ingest_document(db, fpath, tenant_id=tenant_id)
            ingested.append(doc)
    return ingested

def retrieve_relevant_chunks(
    db: Session,
    query: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    top_k: int = settings.RAG_TOP_K,
    similarity_threshold: float = settings.RAG_SIMILARITY_THRESHOLD
) -> List[RAGQueryResult]:
    """
    Retrieve top K relevant chunks using cosine similarity via pgvector.
    Returns empty list if similarity is below the threshold.
    """
    query_vector = get_embedding(query)

    # Use pgvector cosine distance: 1 - (embedding <=> query_vector) = cosine similarity
    # In pgvector with SQLAlchemy: DocumentChunk.embedding.cosine_distance(query_vector)
    query_dist = DocumentChunk.embedding.cosine_distance(query_vector)
    stmt = (
        select(
            DocumentChunk.id,
            Document.title,
            Document.filename,
            DocumentChunk.content,
            (1.0 - query_dist).label("similarity")
        )
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.tenant_id == tenant_id)
        .order_by(query_dist.asc())
        .limit(top_k)
    )

    results = db.execute(stmt).fetchall()

    filtered: List[RAGQueryResult] = []
    for row in results:
        chunk_id, doc_title, fname, chunk_content, sim = row
        sim_val = float(sim) if sim is not None else 0.0
        if sim_val >= similarity_threshold:
            filtered.append(
                RAGQueryResult(
                    chunk_id=str(chunk_id),
                    document_title=str(doc_title or fname),
                    filename=str(fname),
                    content=str(chunk_content),
                    similarity=round(sim_val, 4)
                )
            )

    return filtered

def answer_with_rag(
    db: Session,
    question: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> Dict[str, Any]:
    """Retrieve relevant chunks and synthesize answer. Fall back safely if unsupported."""
    chunks = retrieve_relevant_chunks(db, question, tenant_id=tenant_id)

    if not chunks:
        return {
            "answer": RAG_FALLBACK_RESPONSE,
            "evidence_found": False,
            "sources": []
        }

    # Strict anti-hallucination guardrail: verify that substantive subject terms from the question appear in retrieved chunks
    content_terms = {
        w for w in re.findall(r'\b\w{4,}\b', question.lower())
        if w not in STOP_WORDS and w not in {'voxlead', 'software', 'product', 'system', 'does', 'have', 'support', 'with'}
    }
    if content_terms:
        has_subject_match = any(any(t in c.content.lower() for t in content_terms) for c in chunks)
        if not has_subject_match:
            return {
                "answer": RAG_FALLBACK_RESPONSE,
                "evidence_found": False,
                "sources": []
            }

    sources = [
        {"title": c.document_title, "filename": c.filename, "similarity": c.similarity}
        for c in chunks
    ]
    context_text = "\n\n---\n\n".join([f"[{c.document_title}]: {c.content}" for c in chunks])

    # If OpenAI API is active and not mock mode, generate contextual response
    if settings.OPENAI_API_KEY and not settings.MOCK_MODE:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                f"You are the VoxLead AI sales assistant. Answer the customer's question strictly "
                f"using the provided verified context. If the context does not clearly address the question, "
                f"do not fabricate information; use the fallback message.\n\n"
                f"Verified Context:\n{context_text}\n\n"
                f"Customer Question: {question}\n\n"
                f"Answer:"
            )
            completion = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            answer = completion.choices[0].message.content.strip()
            return {"answer": answer, "evidence_found": True, "sources": sources}
        except Exception:
            pass

    # Deterministic answer synthesis for mock/offline execution
    best_chunk = chunks[0]
    extracted_answer = f"Based on our {best_chunk.document_title}: {best_chunk.content[:280]}..."
    return {
        "answer": extracted_answer,
        "evidence_found": True,
        "sources": sources
    }
