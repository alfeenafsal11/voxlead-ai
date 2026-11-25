import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, init_db
from backend.app.models import Customer, Lead, Call, Message, Appointment, CallSummary
from backend.app.voice.agent import generate_livekit_token
from backend.app.services.orchestrator import process_voice_turn
from backend.app.services.call_intelligence import generate_call_summary
from backend.app.services.rag import answer_with_rag, RAG_FALLBACK_RESPONSE
from backend.app.services.lead_intelligence import extract_lead_from_dialogue, calculate_lead_score
from backend.app.services.integrations import (
    get_calendar_provider,
    book_calendar_appointment,
    sync_lead_to_crm
)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_end_to_end_sales_scenario(db_session: Session):
    """
    Scenario:
    A customer wants a CRM for a 45-member company, currently manages leads manually,
    has a budget of 50,000, is evaluating software within 30 days, is a decision-maker
    and wants a product demonstration.
    """
    # Step 1: Customer initiates voice session & LiveKit token is generated
    token_res = generate_livekit_token(
        room_name="e2e-sales-room",
        participant_name="Jordan Vance",
        language="en"
    )
    assert len(token_res.token) > 50

    cust = Customer(
        name="Jordan Vance",
        email="jordan.vance@lumina.io",
        company="Lumina Health"
    )
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)

    call = Call(
        customer_id=cust.id,
        session_id=token_res.session_id,
        room_name="e2e-sales-room",
        language="en",
        status="in_progress"
    )
    db_session.add(call)
    db_session.commit()
    db_session.refresh(call)

    # Step 2: Turn 1 - Prospect asks about CRM features and pricing
    turn1_input = "Hi, we are looking for a CRM for our 45 sales reps. We currently track leads manually in spreadsheets. What is your pricing?"
    turn1 = process_voice_turn(db_session, call.id, turn1_input)
    assert turn1["response_text"] is not None
    assert len(turn1["sources"]) > 0
    assert any("pricing" in s["filename"] or "spreadsheet" in s["title"].lower() or "objection" in s["filename"] for s in turn1["sources"])

    # Step 3: Turn 2 - Prospect states budget, authority, and 30-day timeline
    turn2_input = (
        "Our budget is around 50,000 dollars. I am the VP of Sales and make the decision. "
        "We need to deploy within 30 days. Can we schedule a demo?"
    )
    turn2 = process_voice_turn(db_session, call.id, turn2_input)
    assert turn2["lead_score"] >= 70, f"Expected Hot lead (>=70), got {turn2['lead_score']}"
    assert turn2["lead_classification"] == "hot"

    # Step 4: Turn 3 - Confirmation of demo slot
    turn3_input = "Yes, please book tomorrow at 2:00 PM. That works for me."
    turn3 = process_voice_turn(db_session, call.id, turn3_input)
    assert turn3["action_triggered"] == "book_appointment"

    # Step 5: Calendar booking with idempotency
    now = datetime.now(timezone.utc)
    slot_time = now.replace(hour=14, minute=0, second=0, microsecond=0) + timedelta(days=1)
    idemp_key = f"e2e_booking_{call.id}"

    appt = book_calendar_appointment(
        db=db_session,
        customer_id=cust.id,
        title="VoxLead CRM Product Demonstration - Lumina Health",
        scheduled_time=slot_time,
        idempotency_key=idemp_key,
        call_id=call.id
    )
    assert appt.id is not None
    assert appt.status == "confirmed"

    # Step 6: Post-Call Intelligence & Summary Generation
    summary = generate_call_summary(db_session, call_id=call.id)
    assert summary.summary_text is not None
    assert summary.lead_score >= 70
    assert summary.appointment_status == "booked"
    assert summary.crm_sync_status == "synced"
    assert len(summary.key_insights) >= 3

    # Step 7: Verify lead record in DB
    lead = db_session.query(Lead).filter(Lead.customer_id == cust.id).first()
    assert lead is not None
    assert lead.score >= 70
    assert lead.hubspot_contact_id is not None
    assert lead.hubspot_deal_id is not None

    # Clean up test entities
    db_session.delete(appt)
    db_session.delete(call)
    db_session.delete(lead)
    db_session.delete(cust)
    db_session.commit()

def test_negative_unsupported_product_question(db_session: Session):
    """Unsupported question must safely fall back without hallucination."""
    res = answer_with_rag(db_session, "Can VoxLead CRM fly a commercial spacecraft to Mars?")
    assert res["evidence_found"] is False
    assert res["answer"] == RAG_FALLBACK_RESPONSE

def test_negative_insufficient_customer_info():
    """Missing or vague customer statements must leave criteria as None or 0."""
    extraction = extract_lead_from_dialogue("Hello there, just checking out your site.")
    assert extraction.budget is None
    assert extraction.company_size is None
    assert extraction.purchase_timeline is None
    assert extraction.decision_making_authority is None

    score, classification, completeness = calculate_lead_score(extraction)
    assert score == 0
    assert classification == "cold"
    assert completeness == 0.0

def test_negative_calendar_collision(db_session: Session):
    """Attempting to double-book the same customer slot must raise ValueError."""
    cust = Customer(name="Collision Tester", email="collision@test.com")
    db_session.add(cust)
    db_session.commit()

    slot_time = datetime.now(timezone.utc) + timedelta(days=4)
    appt1 = book_calendar_appointment(
        db=db_session,
        customer_id=cust.id,
        title="Meeting 1",
        scheduled_time=slot_time,
        idempotency_key=f"key_{uuid.uuid4().hex}"
    )

    with pytest.raises(ValueError, match="already has an active appointment"):
        book_calendar_appointment(
            db=db_session,
            customer_id=cust.id,
            title="Meeting 2 (Conflicting)",
            scheduled_time=slot_time + timedelta(minutes=10),
            idempotency_key=f"key_{uuid.uuid4().hex}"
        )

    db_session.delete(appt1)
    db_session.delete(cust)
    db_session.commit()
