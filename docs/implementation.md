# VoxLead AI: Implementation Details & Engineering Guide

## 1. Technology Choices & Justification

- **Language & Runtime**: Python 3.11 with FastAPI. Chosen for high-throughput async I/O, native integration with AI SDKs, and type safety with Pydantic v2.
- **Database & Vector Store**: PostgreSQL 16 with the official `pgvector` extension. Using PostgreSQL for both relational entities and vector embeddings avoids the operational overhead and synchronization lag of running separate vector databases.
- **Frontend Stack**: React 18 with Vite. Delivers instant hot-reloading, fast production bundle builds (sub-4 seconds), and modular component architecture.
- **Voice Pipeline**: LiveKit Python client with WebRTC for bidirectional audio streaming, Deepgram for streaming STT, OpenAI GPT-4o for consultative reasoning, and ElevenLabs for low-latency streaming TTS.
- **Modular Monolith Architecture**: Colocating services within a single repository and runtime eliminates distributed network boundaries, serialization overhead, and microservice orchestration complexity while keeping code strictly modular.

---

## 2. Agent Implementation

The voice agent is designed around a consultative sales persona named **Ava**:
- **Tone**: Professional, empathetic, concise, and non-pushy.
- **Turn Constraint**: Keeps responses to 1-3 conversational sentences to maintain natural telephone conversational cadence.
- **One Question at a Time**: Asks only a single relevant qualifying question per turn.
- **Language Handling**: Automatically detects customer dialect (English or Hindi) and preserves the caller's preferred language throughout the interaction.
- **Prompt Architecture**: Includes explicit system instructions instructing the agent never to fabricate prices, terms, or specifications.

---

## 3. RAG Knowledge Pipeline

1. **Document Loading**: Supports `.md`, `.txt`, and `.pdf` documents stored in `backend/app/data/knowledge_base/`.
2. **Chunking**: Text is chunked into approx 500 tokens (1,800 characters) with approx 75 tokens overlap (300 characters), splitting gracefully across paragraph and sentence boundaries.
3. **Embedding Vector**: Generates 1,536-dimensional vectors using OpenAI `text-embedding-3-small`. In mock/offline mode, a deterministic term-frequency and n-gram hash algorithm generates normalized unit vectors to allow pgvector cosine distance operations to execute mathematically.
4. **Cosine Similarity Search**:
   ```sql
   SELECT document_chunks.id, documents.title, documents.filename, document_chunks.content,
          (1.0 - (document_chunks.embedding <=> query_vector)) AS similarity
   FROM document_chunks
   JOIN documents ON document_chunks.document_id = documents.id
   WHERE documents.tenant_id = :tenant_id
   ORDER BY document_chunks.embedding <=> query_vector ASC
   LIMIT :top_k;
   ```
5. **Anti-Hallucination Guardrail**: If similarity is below `settings.RAG_SIMILARITY_THRESHOLD` or if substantive query content keywords are absent from retrieved chunks, the system safely triggers `RAG_FALLBACK_RESPONSE`.

---

## 4. Customer Memory Design

Customer memory is bifurcated into two distinct layers stored in the `customer_memory` table:
- **Short-Term Memory (`short_term_data`)**:
  - `conversation_state`: Tracking progress (greeting, qualifying, objection_handling, booking_proposed, appointment_confirmed, call_completed).
  - `current_language`: Active preferred language (`en` or `hi`).
  - `known_qualification_fields`: Extracted fields gathered in current call.
  - `pending_business_actions`: Actions awaiting confirmation.
- **Long-Term Memory (`long_term_data`)**:
  - `customer_profile`: Contact details, company, industry.
  - `requirements`: Aggregated business needs across interactions.
  - `budget` & `purchase_timeline`: Budget and timeline history.
  - `previous_objections`: Logged objections to prevent repeating past answers.
  - `previous_interaction_summaries`: History of completed call summaries.

---

## 5. Deterministic Lead Scoring (BANT)

Scoring is calculated deterministically across 5 criteria (max 100 points):
1. **Budget Compatibility**: 30 points (Budget ≥ $10,000).
2. **Purchase Timeline**: 25 points (Deploying within 30 days).
3. **Decision-Maker Identified**: 20 points (Executive authority confirmed).
4. **Clear Business Requirement**: 15 points (Explicit need identified).
5. **Suitable Company Size**: 10 points (10 to 500 team members).

**Lead Classification**:
- **Hot**: 70 to 100 points
- **Warm**: 40 to 69 points
- **Cold**: 0 to 39 points

---

## 6. Business Integrations & Idempotency

- **Google Calendar**: Evaluates actual calendar availability slots (10:00 AM, 2:00 PM, 4:00 PM UTC) and enforces idempotency via unique `idempotency_key` indexes to prevent duplicate events.
- **HubSpot CRM**: Deduplicates contacts by email address, patches existing records or creates new contacts, and creates pipeline opportunity deals.
- **Mock Mode**: When external credentials (`GOOGLE_CALENDAR_*` or `HUBSPOT_ACCESS_TOKEN`) are not supplied, the system seamlessly uses deterministic mock adapters returning `is_mock=True` while keeping real API clients completely implemented.

---

## 7. Key API Endpoints

- `GET /health`: Health probe reporting database and pgvector extension status.
- `GET /api/dashboard/overview`: Aggregated analytics (total calls, leads, distribution, average score).
- `GET /api/leads`: Enriched list of leads with customer profiles and booking statuses.
- `POST /api/voice/session`: Initiates live voice session and returns LiveKit room token.
- `POST /api/voice/turn`: Processes voice dialogue turn.
- `POST /api/voice/end`: Completes call and triggers post-call intelligence summary.
- `GET /api/calendar/availability`: Returns upcoming available demo slots.
- `POST /api/calendar/book`: Books calendar demonstration slot.
- `POST /api/crm/sync`: Synchronizes lead record to HubSpot CRM.
