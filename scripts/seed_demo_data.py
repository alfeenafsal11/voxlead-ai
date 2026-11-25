import os
import sys
import uuid
from datetime import datetime, timedelta, timezone

# Ensure backend package is accessible
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database import SessionLocal, init_db
from backend.app.models import Customer, Lead, Call, Message, Appointment, CallSummary, CustomerMemory
from backend.app.services.rag import ingest_knowledge_base_directory
from backend.app.services.integrations import book_calendar_appointment, sync_lead_to_crm
from backend.app.config import settings

def seed_demo_data():
    print("🌱 Initializing VoxLead AI Database and Ingesting Knowledge Base...")
    init_db()
    db = SessionLocal()

    tenant_id = settings.DEFAULT_TENANT_ID

    # 1. Ingest Knowledge Base
    kb_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "app", "data", "knowledge_base"))
    docs = ingest_knowledge_base_directory(db, kb_path, tenant_id=tenant_id)
    print(f"✅ Ingested {len(docs)} knowledge base documents into pgvector.")

    # 2. Seed Customer 1: Alex Vance (Lumina Health) - Hot Lead
    now = datetime.now(timezone.utc)
    c1 = Customer(
        tenant_id=tenant_id,
        name="Alex Vance",
        email="alex.vance@luminahealth.io",
        phone="+1 (415) 890-1234",
        company="Lumina Health"
    )
    db.add(c1)
    db.flush()

    lead1 = Lead(
        tenant_id=tenant_id,
        customer_id=c1.id,
        score=95,
        classification="hot",
        sentiment="positive",
        intent="Schedule product demonstration",
        requirement="Autonomous Sales Voice CRM for inbound & outbound SDRs",
        budget=50000.0,
        timeline="within 30 days",
        company_size=45,
        decision_maker=True,
        objections=["Currently managing leads manually on spreadsheets"],
        completeness_score=1.0,
        raw_extraction={"source": "seed"}
    )
    db.add(lead1)

    call1 = Call(
        tenant_id=tenant_id,
        customer_id=c1.id,
        session_id=f"sess_{uuid.uuid4().hex[:10]}",
        room_name="sales-lumina-demo",
        status="completed",
        language="en",
        start_time=now - timedelta(minutes=40),
        end_time=now - timedelta(minutes=25),
        duration_seconds=900
    )
    db.add(call1)
    db.flush()

    # Conversation messages
    m1 = Message(tenant_id=tenant_id, call_id=call1.id, role="assistant", content="Hello! I am Ava from VoxLead AI. How can I assist your sales team today?")
    m2 = Message(tenant_id=tenant_id, call_id=call1.id, role="user", content="Hi Ava, I am Alex from Lumina Health. We have 45 sales reps and track leads manually in spreadsheets. What is your pricing?")
    m3 = Message(tenant_id=tenant_id, call_id=call1.id, role="assistant", content="Our Professional tier is $79 per user monthly with autonomous AI voice agents and automated CRM integration. Would you like to schedule a live demo?")
    m4 = Message(tenant_id=tenant_id, call_id=call1.id, role="user", content="Our budget is 50,000 dollars and we want to deploy within 30 days. Yes, please book tomorrow at 2 PM.")
    db.add_all([m1, m2, m3, m4])

    # Call summary
    summary1 = CallSummary(
        tenant_id=tenant_id,
        call_id=call1.id,
        summary_text="Conducted consultative sales call with Alex Vance, Head of Sales at Lumina Health. Prospect currently struggles with manual spreadsheets across 45 reps. Qualified as a HOT opportunity ($50k budget, 30-day decision timeline). Successfully scheduled product demonstration.",
        key_insights=[
            "Lumina Health has 45 sales representatives currently using spreadsheets.",
            "Budget confirmed at $50,000 with a 30-day deployment goal.",
            "Alex is the primary decision-maker."
        ],
        action_items=[
            "Send calendar invite and demonstration access details.",
            "Prepare tailored presentation focusing on automatic spreadsheet replacement."
        ],
        lead_score=95,
        sentiment="positive",
        appointment_status="booked",
        crm_sync_status="synced"
    )
    db.add(summary1)

    # Book Appointment
    slot_time = now.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    appt1 = Appointment(
        tenant_id=tenant_id,
        customer_id=c1.id,
        call_id=call1.id,
        title="VoxLead CRM Product Demonstration - Lumina Health",
        scheduled_time=slot_time,
        end_time=slot_time + timedelta(minutes=45),
        calendar_event_id=f"gcal_evt_{uuid.uuid4().hex[:8]}",
        status="confirmed",
        idempotency_key=f"seed_appt_{c1.id}"
    )
    db.add(appt1)

    # Sync to CRM
    sync_res = sync_lead_to_crm(db, customer_id=c1.id, amount=50000.0, tenant_id=tenant_id)
    lead1.hubspot_contact_id = sync_res["contact_id"]
    lead1.hubspot_deal_id = sync_res["deal_id"]

    # 3. Seed Customer 2: Priya Sharma (Zenith Corp) - Multilingual Hindi Lead
    c2 = Customer(
        tenant_id=tenant_id,
        name="Priya Sharma",
        email="priya.sharma@zenith.in",
        phone="+91 98765 43210",
        company="Zenith Retail India"
    )
    db.add(c2)
    db.flush()

    lead2 = Lead(
        tenant_id=tenant_id,
        customer_id=c2.id,
        score=75,
        classification="hot",
        sentiment="positive",
        intent="Evaluate enterprise multilingual voice capabilities",
        requirement="Enterprise multilingual AI voice agent for inbound support & qualification",
        budget=35000.0,
        timeline="within 30 days",
        company_size=30,
        decision_maker=True,
        objections=[],
        completeness_score=0.8,
        raw_extraction={"source": "seed"}
    )
    db.add(lead2)

    call2 = Call(
        tenant_id=tenant_id,
        customer_id=c2.id,
        session_id=f"sess_{uuid.uuid4().hex[:10]}",
        room_name="sales-zenith-hindi",
        status="completed",
        language="hi",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1, minutes=45),
        duration_seconds=900
    )
    db.add(call2)

    # 4. Seed Customer 3: Marcus Wright (CyberShield) - Warm Lead
    c3 = Customer(
        tenant_id=tenant_id,
        name="Marcus Wright",
        email="marcus@cybershield.net",
        company="CyberShield Systems"
    )
    db.add(c3)
    db.flush()

    lead3 = Lead(
        tenant_id=tenant_id,
        customer_id=c3.id,
        score=55,
        classification="warm",
        sentiment="neutral",
        intent="Evaluate pricing models",
        requirement="Sales automation tools",
        budget=15000.0,
        timeline="within 90 days",
        company_size=15,
        decision_maker=False,
        objections=["Budget approval required from executive committee"],
        completeness_score=0.8
    )
    db.add(lead3)

    # 5. Seed Customer 4: Elena Rostova - Cold Lead
    c4 = Customer(
        tenant_id=tenant_id,
        name="Elena Rostova",
        email="elena@novatech.co",
        company="NovaTech"
    )
    db.add(c4)
    db.flush()

    lead4 = Lead(
        tenant_id=tenant_id,
        customer_id=c4.id,
        score=25,
        classification="cold",
        sentiment="neutral",
        intent="Browsing product overview",
        requirement=None,
        budget=None,
        timeline="undecided",
        company_size=3,
        decision_maker=False,
        objections=[],
        completeness_score=0.2
    )
    db.add(lead4)

    db.commit()
    print("✅ Seeded 4 customers, 4 leads (Hot, Warm, Cold), 2 calls, and appointments.")
    db.close()

if __name__ == "__main__":
    seed_demo_data()
