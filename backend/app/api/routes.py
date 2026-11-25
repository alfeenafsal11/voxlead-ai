import os
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models import Customer, Lead, Call, Message, Appointment, CallSummary, Document
from backend.app.schemas import (
    DashboardOverview,
    LeadResponse,
    CallResponse,
    MessageResponse,
    LiveKitTokenRequest,
    LiveKitTokenResponse,
    CalendarAvailabilityRequest,
    CalendarSlot,
    BookAppointmentRequest,
    AppointmentResponse,
    HubSpotSyncRequest,
    HubSpotSyncResponse,
    CallSummaryResponse
)
from backend.app.voice.agent import generate_livekit_token
from backend.app.services.orchestrator import process_voice_turn
from backend.app.services.call_intelligence import generate_call_summary
from backend.app.services.integrations import get_calendar_provider, book_calendar_appointment, sync_lead_to_crm
from backend.app.services.rag import ingest_knowledge_base_directory

router = APIRouter()

# =====================================================================
# DASHBOARD OVERVIEW ANALYTICS
# =====================================================================

@router.get("/dashboard/overview", response_model=DashboardOverview, tags=["Analytics"])
def get_dashboard_overview(
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    """Aggregate live sales metrics directly from database."""
    total_calls = db.query(func.count(Call.id)).filter(Call.tenant_id == tenant_id).scalar() or 0
    total_leads = db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id).scalar() or 0
    qualified_leads = db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id, Lead.score >= 40).scalar() or 0

    hot_leads = db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id, Lead.classification == "hot").scalar() or 0
    warm_leads = db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id, Lead.classification == "warm").scalar() or 0
    cold_leads = db.query(func.count(Lead.id)).filter(Lead.tenant_id == tenant_id, Lead.classification == "cold").scalar() or 0

    avg_score = db.query(func.avg(Lead.score)).filter(Lead.tenant_id == tenant_id).scalar() or 0.0
    appointments_booked = db.query(func.count(Appointment.id)).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.status == "confirmed"
    ).scalar() or 0

    # Sentiment distribution
    sentiment_rows = db.query(Lead.sentiment, func.count(Lead.id)).filter(
        Lead.tenant_id == tenant_id
    ).group_by(Lead.sentiment).all()

    sent_dist = {"positive": 0, "neutral": 0, "negative": 0, "frustrated": 0}
    for s_label, count in sentiment_rows:
        if s_label in sent_dist:
            sent_dist[s_label] = count

    return DashboardOverview(
        total_calls=total_calls,
        total_leads=total_leads,
        qualified_leads=qualified_leads,
        hot_leads=hot_leads,
        warm_leads=warm_leads,
        cold_leads=cold_leads,
        average_lead_score=round(float(avg_score), 1),
        appointments_booked=appointments_booked,
        sentiment_distribution=sent_dist
    )

# =====================================================================
# LEAD MANAGEMENT
# =====================================================================

@router.get("/leads", tags=["Leads"])
def list_leads(
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve all leads with enriched customer profile, appointment and CRM status."""
    leads = (
        db.query(Lead)
        .filter(Lead.tenant_id == tenant_id)
        .order_by(desc(Lead.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for lead in leads:
        customer = lead.customer
        latest_call = db.query(Call).filter(Call.customer_id == lead.customer_id).order_by(desc(Call.created_at)).first()
        summary = latest_call.summary if latest_call else None
        appt = db.query(Appointment).filter(
            Appointment.customer_id == lead.customer_id,
            Appointment.status == "confirmed"
        ).first()

        results.append({
            "id": lead.id,
            "customer_id": lead.customer_id,
            "customer_name": customer.name if customer else "Unknown",
            "company": customer.company if customer else "Unknown",
            "email": customer.email if customer else "",
            "phone": customer.phone if customer else "",
            "score": lead.score,
            "classification": lead.classification,
            "sentiment": lead.sentiment,
            "intent": lead.intent,
            "requirement": lead.requirement,
            "budget": lead.budget,
            "timeline": lead.timeline,
            "company_size": lead.company_size,
            "decision_maker": lead.decision_maker,
            "objections": lead.objections or [],
            "hubspot_contact_id": lead.hubspot_contact_id,
            "hubspot_deal_id": lead.hubspot_deal_id,
            "crm_status": "Synced" if lead.hubspot_contact_id else "Pending",
            "appointment_status": "Booked" if appt else "Not Scheduled",
            "appointment_time": appt.scheduled_time.isoformat() if appt else None,
            "call_summary": summary.summary_text if summary else None,
            "created_at": lead.created_at.isoformat()
        })

    return results

@router.get("/leads/{lead_id}", tags=["Leads"])
def get_lead_details(
    lead_id: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    lead = db.query(Lead).filter(Lead.id == lead_id, Lead.tenant_id == tenant_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

# =====================================================================
# LIVE VOICE SESSIONS & ORCHESTRATION
# =====================================================================

@router.post("/voice/session", tags=["Voice"])
def initialize_voice_session(
    payload: LiveKitTokenRequest,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    """
    Initialize a live voice call session:
    - Creates or identifies customer
    - Generates short-lived LiveKit token
    - Initializes Call record in DB
    """
    # Create or find customer
    cust = None
    if payload.customer_id:
        cust = db.query(Customer).filter(Customer.id == payload.customer_id).first()

    if not cust:
        cust = Customer(
            tenant_id=tenant_id,
            name=payload.participant_name,
        )
        db.add(cust)
        db.commit()
        db.refresh(cust)

    token_res = generate_livekit_token(
        room_name=payload.room_name,
        participant_name=payload.participant_name,
        customer_id=cust.id,
        language=payload.language or "en"
    )

    call = Call(
        tenant_id=tenant_id,
        customer_id=cust.id,
        session_id=token_res.session_id,
        room_name=payload.room_name,
        language=payload.language or "en",
        status="in_progress",
        start_time=datetime.now(timezone.utc)
    )
    db.add(call)
    db.commit()
    db.refresh(call)

    return {
        "call_id": call.id,
        "session_id": token_res.session_id,
        "token": token_res.token,
        "server_url": token_res.server_url,
        "room_name": token_res.room_name,
        "participant_name": token_res.participant_name,
        "customer_id": cust.id,
        "language": call.language
    }

@router.post("/voice/turn", tags=["Voice"])
def submit_voice_turn(
    payload: Dict[str, Any] = Body(...),
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    """
    Process dialogue turn:
    Receives customer speech transcript and returns AI response, sentiment, and updated lead score.
    """
    call_id = payload.get("call_id")
    customer_input = payload.get("message", "")
    override_lang = payload.get("language")

    if not call_id or not customer_input:
        raise HTTPException(status_code=400, detail="call_id and message are required")

    try:
        res = process_voice_turn(
            db=db,
            call_id=call_id,
            customer_input=customer_input,
            override_language=override_lang,
            tenant_id=tenant_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice/end", tags=["Voice"])
def complete_voice_session(
    payload: Dict[str, str] = Body(...),
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    """
    Terminate call session and trigger post-call intelligence:
    - Generates call summary
    - Extracts final requirements & sentiment
    - Updates customer memory
    """
    call_id = payload.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="call_id is required")

    try:
        summary = generate_call_summary(db, call_id=call_id, tenant_id=tenant_id)
        return {
            "success": True,
            "call_id": call_id,
            "summary_text": summary.summary_text,
            "lead_score": summary.lead_score,
            "sentiment": summary.sentiment,
            "appointment_status": summary.appointment_status,
            "crm_sync_status": summary.crm_sync_status,
            "key_insights": summary.key_insights,
            "action_items": summary.action_items
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# CALENDAR & BOOKING
# =====================================================================

@router.get("/calendar/availability", response_model=List[CalendarSlot], tags=["Calendar"])
def check_calendar_availability(
    days_ahead: int = Query(5, ge=1, le=14),
):
    provider = get_calendar_provider()
    now = datetime.now(timezone.utc)
    return provider.check_availability(now, days_ahead=days_ahead)

@router.post("/calendar/book", response_model=AppointmentResponse, tags=["Calendar"])
def book_appointment(
    payload: BookAppointmentRequest,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    try:
        appt = book_calendar_appointment(
            db=db,
            customer_id=payload.customer_id,
            title=payload.title,
            scheduled_time=payload.scheduled_time,
            end_time=payload.end_time,
            idempotency_key=payload.idempotency_key,
            call_id=payload.call_id,
            tenant_id=tenant_id
        )
        return appt
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# HUBSPOT CRM SYNC
# =====================================================================

@router.post("/crm/sync", response_model=HubSpotSyncResponse, tags=["CRM"])
def sync_crm(
    payload: HubSpotSyncRequest,
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    try:
        res = sync_lead_to_crm(
            db=db,
            customer_id=payload.customer_id,
            deal_name=payload.deal_name,
            amount=payload.amount,
            tenant_id=tenant_id
        )
        return HubSpotSyncResponse(
            success=res["success"],
            contact_id=res.get("contact_id"),
            deal_id=res.get("deal_id"),
            message=res.get("message", "Synced"),
            is_mock=res.get("is_mock", True)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =====================================================================
# KNOWLEDGE BASE INGESTION
# =====================================================================

@router.post("/knowledge/ingest", tags=["Knowledge Base"])
def trigger_knowledge_ingestion(
    tenant_id: str = settings.DEFAULT_TENANT_ID,
    db: Session = Depends(get_db)
):
    kb_path = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base")
    docs = ingest_knowledge_base_directory(db, kb_path, tenant_id=tenant_id)
    return {
        "success": True,
        "documents_ingested": len(docs),
        "filenames": [d.filename for d in docs]
    }
