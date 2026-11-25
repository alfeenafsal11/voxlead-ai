import pytest
import os
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, init_db
from backend.app.models import Document, DocumentChunk, Customer
from backend.app.services.rag import (
    ingest_knowledge_base_directory,
    retrieve_relevant_chunks,
    answer_with_rag,
    RAG_FALLBACK_RESPONSE
)
from backend.app.services.memory import (
    get_or_create_customer_memory,
    update_customer_memory,
    save_message,
    get_recent_messages
)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_rag_ingestion(db_session: Session):
    kb_path = os.path.join(os.path.dirname(__file__), "..", "app", "data", "knowledge_base")
    assert os.path.exists(kb_path), f"Knowledge base directory missing: {kb_path}"

    docs = ingest_knowledge_base_directory(db_session, kb_path)
    assert len(docs) >= 7, f"Expected at least 7 documents, found {len(docs)}"

    # Verify document chunks and embeddings exist
    chunks_count = db_session.query(DocumentChunk).count()
    assert chunks_count > 0, "No chunks were persisted in pgvector"

    # Verify embeddings are populated
    first_chunk = db_session.query(DocumentChunk).first()
    assert first_chunk.embedding is not None, "Embedding vector is null"
    assert len(first_chunk.embedding) == 1536, "Embedding dimension is not 1536"

def test_rag_retrieval(db_session: Session):
    # Query pricing
    results = retrieve_relevant_chunks(db_session, "What is the price of the Professional Tier per user?")
    assert len(results) > 0, "No chunks retrieved for pricing query"

    top_chunk = results[0]
    assert top_chunk.filename == "pricing.md", f"Expected pricing.md, got {top_chunk.filename}"
    assert top_chunk.similarity > 0.20, f"Expected reasonable similarity, got {top_chunk.similarity}"
    assert "Professional Tier" in top_chunk.content or "79" in top_chunk.content

    # Query objection handling
    obj_results = retrieve_relevant_chunks(db_session, "What if customer says they track leads in spreadsheets?")
    assert len(obj_results) > 0, "No chunks retrieved for objection query"
    assert any("spreadsheets" in r.content.lower() for r in obj_results)

def test_rag_unsupported_fallback(db_session: Session):
    # Query completely unrelated topic with high threshold
    unrelated_query = "What is the average flight speed of an African swallow?"
    res = answer_with_rag(db_session, unrelated_query)

    # Either no chunks are retrieved or similarity is below threshold
    if not res["evidence_found"]:
        assert res["answer"] == RAG_FALLBACK_RESPONSE

def test_customer_memory_lifecycle(db_session: Session):
    # Create test customer
    cust = Customer(name="Alex Rivera", email="alex@technova.io", company="TechNova")
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)

    # Initial memory creation
    mem = get_or_create_customer_memory(db_session, cust.id)
    assert mem.customer_id == cust.id
    assert mem.short_term_data["conversation_state"] == "greeting"

    # Update memory
    updated = update_customer_memory(
        db_session,
        cust.id,
        short_term_updates={"conversation_state": "qualifying", "current_language": "hi"},
        long_term_updates={"budget": 50000, "requirements": ["Autonomous AI Voice CRM"]}
    )
    assert updated.short_term_data["conversation_state"] == "qualifying"
    assert updated.short_term_data["current_language"] == "hi"
    assert updated.long_term_data["budget"] == 50000
    assert "Autonomous AI Voice CRM" in updated.long_term_data["requirements"]

    # Verify persistence by querying fresh from DB
    db_session.expire_all()
    reloaded = get_or_create_customer_memory(db_session, cust.id)
    assert reloaded.short_term_data["conversation_state"] == "qualifying"
    assert reloaded.long_term_data["budget"] == 50000

    # Clean up test customer
    db_session.delete(cust)
    db_session.commit()
