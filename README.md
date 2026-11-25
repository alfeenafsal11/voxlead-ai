# VoxLead AI — Autonomous AI Sales Voice Agent

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-blue.svg)](https://github.com/pgvector/pgvector)
[![React 18](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

VoxLead AI is an autonomous, production-ready AI sales voice assistant designed to conduct natural, consultative multilingual sales calls, retrieve product specifications using RAG on PostgreSQL/pgvector, qualify leads against BANT criteria, detect sentiment, check calendar availability, book appointments, and synchronize CRM records.

---

## Key Features

1. **Cascaded Voice Architecture**:
   - Streaming STT (Deepgram).
   - Conversational reasoning and qualification (OpenAI GPT-4o).
   - Human-grade streaming speech synthesis (ElevenLabs).
   - Real-time WebRTC audio channel via LiveKit.

2. **RAG Knowledge Base with pgvector**:
   - Ingests Markdown, PDF, and TXT product collateral into PostgreSQL 16.
   - Vector embeddings (1,536 dimensions) with cosine distance search.
   - Anti-hallucination guardrails: returns safe fallback responses when verified evidence is absent.

3. **Deterministic BANT Lead Scoring & Sentiment**:
   - Automatically scores prospects (0–100) based on budget compatibility, 30-day timeline, decision authority, clear need, and team size.
   - Categorizes leads into **Hot (70–100)**, **Warm (40–69)**, and **Cold (0–39)**.
   - Classifies customer sentiment into Positive, Neutral, Negative, or Frustrated.

4. **Business Integrations & Idempotency**:
   - **Google Calendar**: Evaluates availability slots, avoids collisions, and books appointments with unique idempotency keys.
   - **HubSpot CRM**: Deduplicates contacts by email address, enriches customer profiles, and creates opportunity deals.
   - **Dual Mock/Production Adapters**: Cleanly operates offline or without API keys via deterministic mock adapters while keeping real API clients completely implemented.

5. **Multilingual Support**:
   - Real-time natural dialogue in English and Hindi.
   - Preserves customer language preference throughout the interaction.

6. **Interactive SaaS Dashboard**:
   - **Sales Overview**: Real-time KPI cards, lead distribution, and sentiment breakdown.
   - **Live Voice Agent**: Live microphone toggle, animated waveform, interactive transcript bubbles with RAG source chips, and live score updates.
   - **Lead Management**: Filterable, searchable table with post-call summaries, CRM sync status, and manual booking actions.

---

## Project Structure

```
voxlead-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entry point & health check
│   │   ├── config.py                # Environment configuration & Pydantic settings
│   │   ├── database.py              # PostgreSQL engine & pgvector initialization
│   │   ├── models.py                # SQLAlchemy entities (Customers, Leads, Calls, Chunks, etc.)
│   │   ├── schemas.py               # Pydantic data validation & structured extraction schemas
│   │   ├── voice/
│   │   │   └── agent.py             # LiveKit room token generator & system prompts
│   │   ├── services/
│   │   │   ├── orchestrator.py      # Voice dialogue turn processor & language tracker
│   │   │   ├── memory.py            # Customer short-term & long-term memory management
│   │   │   ├── rag.py               # Document ingestion, vector search & guardrails
│   │   │   ├── lead_intelligence.py # BANT scoring & sentiment classification
│   │   │   ├── integrations.py      # Google Calendar & HubSpot CRM providers + mock adapters
│   │   │   └── call_intelligence.py # Post-call summarization & CRM sync
│   │   ├── api/
│   │   │   └── routes.py            # REST endpoints for dashboard, voice, calendar & CRM
│   │   └── data/
│   │       └── knowledge_base/      # Synthetic CRM knowledge base documents (7 files)
│   ├── tests/
│   │   ├── test_rag.py              # Vector retrieval & document chunking tests
│   │   ├── test_leads.py            # Extraction, deterministic scoring & sentiment tests
│   │   ├── test_integrations.py     # Calendar & HubSpot integration tests
│   │   └── test_workflow.py         # End-to-end sales scenario & negative test cases
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── SalesOverview.jsx    # Real-time analytics dashboard
│   │   │   ├── LiveVoiceAgent.jsx   # Interactive voice agent with transcript & waveform
│   │   │   └── LeadManagement.jsx   # Filterable leads table & summary modal
│   │   ├── services/
│   │   │   └── api.js               # Frontend HTTP client service
│   │   ├── App.jsx                  # Main navigation & system health badge
│   │   ├── index.css                # Dark SaaS styling & responsive design
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── Dockerfile
├── docs/
│   ├── architecture.md              # System design, component responsibilities & sequence diagrams
│   ├── implementation.md            # Engineering guide, agent persona & RAG mechanics
│   ├── scalability.md               # 100,000-user strategy & 500 concurrent call capacity planning
│   └── demo_script.md               # Step-by-step evaluator presentation guide
├── scripts/
│   └── seed_demo_data.py            # Ingests KB documents & seeds 4 realistic lead personas
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md
```

---

## Prerequisites

- **Python**: 3.11 or higher
- **Node.js**: 18+ and npm
- **PostgreSQL 16**: With the `pgvector` extension installed
- *(Optional)*: Docker and Docker Compose

---

## Quick Start (Running Locally)

### 1. Database Setup
Ensure PostgreSQL is running locally on port `5432` with a database named `voxlead` and the `vector` extension available:
```sql
CREATE DATABASE voxlead;
\c voxlead
CREATE EXTENSION IF NOT EXISTS vector;
```

### 2. Environment Configuration
Copy the example environment file:
```bash
cp .env.example .env
```
*(Leave API keys blank to run in robust Mock Mode, or supply your actual keys to activate live AI providers).*

### 3. Backend Setup & Ingestion
Install dependencies and seed the demo data:
```bash
pip install -r backend/requirements.txt
python scripts/seed_demo_data.py
```

Start the FastAPI backend server:
```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
Verify the health check:
- `http://localhost:8000/health` → `{"status": "healthy", "database": "connected", "pgvector": "active"}`
- Swagger documentation: `http://localhost:8000/docs`

### 4. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open your browser at **`http://localhost:5173`**.

---

## Running with Docker Compose

To run the entire stack (PostgreSQL with pgvector, FastAPI backend, and React frontend) using Docker Compose:
```bash
docker-compose up --build
```
- Access the frontend dashboard at `http://localhost:5173`.
- Access the backend API at `http://localhost:8000`.

---

## Executing Automated Tests

VoxLead AI includes a comprehensive automated test suite covering all 7 phases:
```bash
python -m pytest backend/tests/ -v
```
Test breakdown:
- `test_rag.py`: Verifies document chunking, pgvector embedding persistence, cosine retrieval, and safe fallbacks.
- `test_leads.py`: Verifies deterministic BANT scoring, Hot/Warm/Cold categorization, and sentiment classification.
- `test_integrations.py`: Verifies Google Calendar availability, collision prevention, idempotency, and HubSpot CRM sync.
- `test_workflow.py`: Executes the complete end-to-end sales scenario and negative guardrail cases.

---

## Production Integrations vs. Mock Mode

The system uses an environment-driven provider pattern:
- **Mock Mode (`MOCK_MODE=true` or blank API keys)**: Uses deterministic local adapters with realistic calendar slots, anti-collision tracking, in-memory HubSpot contact/deal sync, and mathematically grounded vector embeddings. All mock responses are clearly labeled `is_mock: True`.
- **Production Mode**: Fill in the corresponding keys in `.env`:
  - `OPENAI_API_KEY`: Activates live GPT-4o reasoning and `text-embedding-3-small`.
  - `DEEPGRAM_API_KEY`: Activates streaming speech-to-text.
  - `ELEVENLABS_API_KEY`: Activates streaming human-like speech synthesis.
  - `GOOGLE_CALENDAR_*`: Connects to Google Calendar API v3.
  - `HUBSPOT_ACCESS_TOKEN`: Connects to HubSpot CRM API v3.

---

## License
MIT License. Created by the VoxLead Engineering Team.
