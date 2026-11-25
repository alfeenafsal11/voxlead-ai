# VoxLead CRM: Features & Capabilities

## 1. Autonomous AI Voice Agent
- Cascaded streaming architecture: Deepgram streaming Speech-to-Text, OpenAI LLM reasoning, and ElevenLabs human-grade Text-to-Speech.
- Full duplex conversational capability with sub-second interruption handling and acoustic echo cancellation.
- Natural multi-turn dialogue with proactive objection management and contextual question progression.
- Real-time language switching between English and Hindi, with persistent user language preference tracking.

## 2. Dynamic RAG Knowledge Retrieval
- Embeds product collateral, technical whitepapers, pricing tables, and company policies into PostgreSQL using pgvector.
- Strict anti-hallucination guardrails: the agent strictly grounds its answers on verified retrieved chunks and explicitly declares when facts are unknown.
- Sub-50ms vector similarity lookup utilizing cosine distance indexes.

## 3. Real-Time Lead Qualification & Scoring
- Automates BANT (Budget, Authority, Need, Timeline) qualification criteria collection.
- Deterministic lead scoring algorithm calculating 0-100 score:
  - Budget compatibility (30 points)
  - Purchase timeline within 30 days (25 points)
  - Identified decision maker (20 points)
  - Explicit business need/requirement (15 points)
  - Suitable company size (10 points)
- Automatic categorical classification into Hot (70-100), Warm (40-69), or Cold (0-39).

## 4. Calendar & Scheduling Engine
- Live two-way synchronization with Google Calendar and Outlook Calendar.
- Real-time conflict avoidance checking actual slot availability before proposing meeting times.
- Idempotent booking transactions ensuring no duplicate calendar invites or orphaned events.

## 5. Bidirectional CRM Synchronization
- Out-of-the-box native synchronization with HubSpot CRM and Salesforce.
- Automatic contact discovery, deduplication, enrichment, and pipeline deal creation.
- Structured call summary logging including customer sentiment, stated objections, and next steps.
