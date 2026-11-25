# VoxLead AI: Live Demonstration Script & Presentation Workflow

This document outlines the step-by-step demonstration procedure to present VoxLead AI to technical evaluators and enterprise stakeholders.

---

## Part 1: Architecture & System Health Check (1 Minute)

1. Open the VoxLead AI dashboard at `http://localhost:5173`.
2. Point out the top header status badges:
   - **MOCK ADAPTERS**: Proves integration safety when external production API keys are omitted.
   - **PGVECTOR ONLINE**: Confirms active PostgreSQL 16 connection with 1,536-dimensional vector similarity indexing.
3. Review the **Sales Overview** page:
   - Live KPI cards: Total Calls, Identified Leads, Average Lead Score, and Booked Demos.
   - Lead Classification Distribution (Hot / Warm / Cold).
   - Sentiment Breakdown (Positive, Neutral, Negative, Frustrated).

---

## Part 2: The Core Sales Dialogue & Voice Agent (3 Minutes)

Navigate to the **Live Voice Agent** tab (`http://localhost:5173`).

### Step 1: Initiating Session
1. Enter Customer Name: `Alex Vance`
2. Enter Company: `Lumina Health`
3. Click **Start Sales Call**.
4. Observe the WebRTC streaming indicator turn green and audio waveform activate.

### Step 2: Product & Pricing Inquiry (RAG Knowledge Grounding)
- **Customer**: *"What is the price of your Professional tier and what features does it include?"*
- **Ava (Voice Agent)**: *"Our Professional tier is $79 per user per month billed annually. It includes our autonomous AI voice agent, 2,500 monthly voice minutes, real-time RAG knowledge base integration, and native two-way synchronization with HubSpot and Google Calendar. How many sales reps are on your team?"*
- **Inspect**:
  - Notice the `pricing.md` source metadata attached to the message bubble.
  - Notice that Ava immediately answered with verified numbers and followed up with **one** relevant qualification question.

### Step 3: Handling Objection & BANT Qualification
- **Customer**: *"We have 45 sales reps, but we currently manage all our leads manually in spreadsheets."*
- **Ava**: *"Spreadsheets are very common for early stage tracking, but as teams scale past 10 reps, manual updates typically cost each representative 8-10 hours weekly. VoxLead automatically qualifies leads and updates records in real time. Would you like to see a quick 20-minute demo this week?"*
- **Inspect**:
  - Live Lead Score updates in the right sidebar to **95/100**.
  - Classification updates to **HOT 🔥**.
  - Sentiment displays **Positive**.

### Step 4: Multilingual Switch Demonstration (Hindi)
- **Customer**: *"Namaste! Kya kal afternoon 2 baje ka demo book ho sakta hai?"*
- **Ava**: *"नमस्ते! मैं आपके लिए हमारे सॉल्यूशंस इंजीनियर के साथ एक लाइव डेमो बुक कर सकती हूँ। कल दोपहर 2 बजे का समय आपके लिए कन्फर्म कर दिया गया है।"*
- **Inspect**:
  - Notice the automatic language switch to Hindi without breaking conversation state.

### Step 5: Appointment Booking Confirmation & CRM Sync
- **Customer**: *"Yes, please confirm tomorrow at 2:00 PM."*
- **Ava**: *"Confirmed! I have scheduled your product demonstration for tomorrow at 2:00 PM UTC. A calendar invite has been sent to your email."*
- **Inspect**:
  - Notice the green badge: `Appointment Booking Executed & Confirmed`.

### Step 6: Post-Call Summary Generation
1. Click **End Call & Summarize**.
2. The **Post-Call Summary Modal** appears:
   - Executive summary of the dialogue.
   - Lead Score: 95/100.
   - HubSpot CRM status: `Synced`.
   - Extracted key insights and action items.

---

## Part 3: Lead Management & CRM Inspection (1 Minute)

Navigate to the **Lead Management** tab.

1. Locate **Alex Vance (Lumina Health)** in the table:
   - Score: **95** (Hot badge).
   - Appointment: **Booked**.
   - HubSpot CRM: **Synced**.
2. Click **Summary** to inspect the complete conversation context.
3. Demonstrate searching by keyword: Type `spreadsheets` or `Lumina` in the search bar.
4. Filter by Hot / Warm / Cold to show instantaneous tabular filtering.

---

## Part 4: Failure & Guardrail Demonstrations (Negative Cases)

### 1. Unsupported Question Guardrail
- **Input**: *"Can VoxLead CRM fly a commercial spacecraft to Mars?"*
- **Expected Result**: Ava safely responds with the verified fallback:
  > *"I don't have verified information regarding this in our knowledge base. Would you like me to note this requirement for our solutions team, or discuss it during a scheduled demonstration?"*
  *(Anti-hallucination guardrail prevents fabricating fictional specifications).*

### 2. Double-Booking & Conflict Avoidance
- In the Lead Management table, attempt to book a conflicting demo for the same customer at an already booked time slot.
- **Expected Result**: The system prevents double-booking and reports: `Customer already has an active appointment at that time.`

### 3. Missing Information Handling
- A prospect saying *"Just browsing your website today"* has missing criteria preserved as `null`, receiving a score of `0` and classified safely as `Cold`.
