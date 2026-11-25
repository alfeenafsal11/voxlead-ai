# VoxLead AI: Architecture & System Design

## 1. High-Level Architecture Overview

VoxLead AI is engineered as a modular monolith optimized for low-latency conversational voice reasoning, semantic knowledge retrieval, deterministic lead scoring, and automated business system synchronization.

The architecture decouples heavy external AI services behind provider interfaces, allowing seamless swapping between production AI engines (OpenAI, Deepgram, ElevenLabs, Google Calendar, HubSpot) and deterministic local mock adapters without modifying core domain logic.

```mermaid
flowchart TD
    subgraph ClientLayer ["Client Layer"]
        UserMic["Microphone Audio"] --> WebRTC["WebRTC Audio Stream"]
        BrowserUI["React / Vite Dashboard"] --> REST["FastAPI HTTP/JSON Client"]
    end

    subgraph VoiceGateway ["Voice Gateway & Streaming Pipeline"]
        WebRTC --> LiveKit["LiveKit Server"]
        LiveKit --> STT["Deepgram Streaming STT"]
        STT --> VoiceAgent["Voice Agent Orchestrator"]
        VoiceAgent --> TTS["ElevenLabs Streaming TTS"]
        TTS --> LiveKit
    end

    subgraph CoreEngine ["Backend Modular Monolith (FastAPI)"]
        REST --> APIRoutes["API Router (/api)"]
        APIRoutes --> VoiceAgent
        VoiceAgent --> RAGEngine["RAG Knowledge Engine"]
        VoiceAgent --> MemoryService["Customer Memory (Short & Long Term)"]
        VoiceAgent --> LeadIntel["Lead Intelligence & BANT Scoring"]
        VoiceAgent --> IntService["Integration Service"]
        VoiceAgent --> CallIntel["Post-Call Intelligence"]
    end

    subgraph DataStorage ["Persistence Layer"]
        RAGEngine --> PGVector["PostgreSQL 16 + pgvector"]
        MemoryService --> PGVector
        LeadIntel --> PGVector
        CallIntel --> PGVector
    end

    subgraph ExternalServices ["External Business Integrations"]
        IntService --> GCal["Google Calendar API v3"]
        IntService --> HubSpot["HubSpot CRM API v3"]
    end
```

---

## 2. Component Responsibilities

| Component | Responsibility | Technology |
| :--- | :--- | :--- |
| **Frontend UI** | Real-time sales overview, interactive voice agent with animated waveform, lead management & appointment booking. | React 18, Vite, Lucide Icons, Vanilla CSS |
| **FastAPI Core** | API routes, authentication, lifespan management, health check probes. | FastAPI, Uvicorn, Pydantic v2 |
| **LiveKit Gateway** | Real-time WebRTC audio connection, session room tokens, turn activity detection. | LiveKit Agents & LiveKit API |
| **RAG Knowledge Pipeline** | Ingestion of markdown, PDF, and txt documents; chunking (~500 tokens with 75 overlap); cosine vector retrieval; anti-hallucination guardrails. | pgvector, OpenAI `text-embedding-3-small` / Deterministic Semantic pseudo-embeddings |
| **Customer Memory** | Short-term conversation state, language preference, pending confirmations, long-term profile, objections, and past interaction summaries. | PostgreSQL JSON / SQLAlchemy |
| **Lead Intelligence** | Deterministic BANT scoring (0-100), categorization (Hot/Warm/Cold), sentiment classification (Positive/Neutral/Negative/Frustrated). | Pydantic structured models |
| **Business Integrations** | Calendar slot checking, conflict avoidance, idempotent appointment booking, HubSpot contact deduplication & deal pipeline creation. | Google Calendar API v3, HubSpot CRM API v3, Mock Adapters |
| **Post-Call Intelligence** | Automated post-call summary generation, key insight extraction, action items logging, CRM auto-sync. | OpenAI LLM / Deterministic Summarizer |

---

## 3. End-to-End Conversational Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Prospect as Prospective Customer
    participant UI as React Dashboard
    participant API as FastAPI Router
    participant Voice as Voice Orchestrator
    participant RAG as pgvector RAG Engine
    participant LLM as OpenAI GPT-4o
    participant GCal as Google Calendar
    participant CRM as HubSpot CRM
    participant DB as PostgreSQL

    Prospect->>UI: Clicks "Start Sales Call"
    UI->>API: POST /api/voice/session
    API->>Voice: generate_livekit_token(room, participant)
    Voice-->>UI: Return JWT Token & Room Details
    UI->>Prospect: Establish Audio Channel

    Prospect->>UI: Speaks: "What is the price of the Professional tier?"
    UI->>Voice: Streaming Audio Turn
    Voice->>RAG: retrieve_relevant_chunks("What is the price of the Professional tier?")
    RAG->>DB: Cosine Distance Lookup (<=>)
    DB-->>RAG: Top Chunks (pricing.md, similarity: 0.76)
    RAG-->>Voice: Grounded Evidence Context
    Voice->>LLM: Generate Consultative Turn (System Prompt + RAG + Transcript)
    LLM-->>Voice: "Our Professional tier is $79/user/month..."
    Voice-->>UI: Streaming TTS Audio & Chat Bubble

    Prospect->>UI: "We have 45 reps and $50k budget. Can we book a demo tomorrow at 2 PM?"
    UI->>Voice: Streaming Audio Turn
    Voice->>Voice: Lead Extraction & Scoring (Score: 95, Hot)
    Voice->>Voice: Detect Confirmation Intent ("book_appointment")
    Voice->>GCal: Recheck Availability & Book Slot (Idempotent)
    GCal-->>Voice: Event Confirmed (ID: evt_123)
    Voice->>CRM: Create Contact & Opportunity Deal
    CRM-->>Voice: Synced (Contact: hs_cont_456, Deal: hs_deal_789)
    Voice-->>UI: "Confirmed! I have scheduled your demo for tomorrow at 2:00 PM."

    Prospect->>UI: Ends Call
    UI->>API: POST /api/voice/end
    API->>Voice: generate_call_summary(call_id)
    Voice->>DB: Persist CallSummary & Update Customer Memory
    DB-->>UI: Display Post-Call Summary Modal
```
