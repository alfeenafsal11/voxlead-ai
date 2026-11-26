import json
import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.models import Call, Customer, Lead, CallSummary, Appointment
from backend.app.services.lead_intelligence import extract_lead_from_dialogue, calculate_lead_score, analyze_sentiment
from backend.app.services.memory import get_recent_messages, update_customer_memory
from backend.app.services.integrations import sync_lead_to_crm

logger = logging.getLogger("voxlead.call_intelligence")

def generate_call_summary(
    db: Session,
    call_id: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> CallSummary:
    """
    Process completed call:
    - Aggregate full transcript
    - Extract requirements, objections, intent, and sentiment
    - Calculate final lead score
    - Update customer memory
    - Check appointment booking & sync with CRM
    - Save CallSummary record
    """
    call = db.query(Call).filter(Call.id == call_id, Call.tenant_id == tenant_id).first()
    if not call:
        raise ValueError(f"Call {call_id} not found")

    # Mark call as completed if in progress
    if call.status == "in_progress":
        call.status = "completed"
        call.end_time = datetime.now(timezone.utc)
        if call.start_time:
            # Ensure timezone awareness
            st = call.start_time if call.start_time.tzinfo else call.start_time.replace(tzinfo=timezone.utc)
            et = call.end_time if call.end_time.tzinfo else call.end_time.replace(tzinfo=timezone.utc)
            call.duration_seconds = max(10, int((et - st).total_seconds()))

    customer_id = call.customer_id
    messages = get_recent_messages(db, call_id, limit=50)
    transcript = "\n".join([f"{m.role.capitalize()}: {m.content}" for m in messages])

    # Extract lead intelligence
    extraction = extract_lead_from_dialogue(transcript)
    lead_score, classification, completeness = calculate_lead_score(extraction)
    sentiment_res = analyze_sentiment(transcript)

    # Check appointment status for this call
    appt = db.query(Appointment).filter(
        Appointment.call_id == call_id,
        Appointment.status == "confirmed"
    ).first()
    appointment_status = "booked" if appt else "not_scheduled"

    # CRM synchronization status
    crm_status = "pending"
    lead = db.query(Lead).filter(Lead.customer_id == customer_id).first()
    if lead and lead.hubspot_contact_id:
        crm_status = "synced"
    elif customer_id:
        try:
            # Auto-sync qualified leads with score >= 40
            if lead_score >= 40:
                sync_res = sync_lead_to_crm(db, customer_id, tenant_id=tenant_id)
                crm_status = "synced" if sync_res.get("success") else "failed"
        except Exception as e:
            logger.warning(f"Auto-sync CRM failed: {e}")
            crm_status = "failed"

    # Formulate structured summary
    customer = db.query(Customer).filter(Customer.id == customer_id).first() if customer_id else None
    cust_name = customer.name if customer and customer.name else "Prospective Buyer"
    company_name = customer.company if customer and customer.company else "Unknown Company"

    key_insights = [
        f"Caller represents {company_name} with ~{extraction.company_size or 'unspecified'} team members.",
        f"Requirement: {extraction.product_requirement or 'General Sales Automation evaluation'}.",
        f"Budget: ${extraction.budget:,.2f}" if extraction.budget else "Budget not disclosed.",
        f"Decision Authority: {'Yes, primary decision maker' if extraction.decision_making_authority else 'Evaluator/Not confirmed'}.",
        f"Timeline: {extraction.purchase_timeline or 'Standard evaluation timeline'}.",
    ]
    if extraction.objections:
        key_insights.append(f"Identified Objections: {', '.join(extraction.objections)}")

    action_items = [
        "Send product collateral and pricing overview via email.",
        f"{'Confirm calendar invite and prepare customized demo sandbox' if appt else 'Follow up in 2 business days to schedule demonstration'}.",
        "Verify CRM contact data enrichment."
    ]

    summary_text = (
        f"Completed consultative sales dialogue with {cust_name} from {company_name}. "
        f"The lead was qualified as a {classification.upper()} opportunity with a score of {lead_score}/100. "
        f"Customer expressed {sentiment_res.sentiment} sentiment. "
        f"{'A product demonstration has been booked successfully.' if appt else 'Prospect is evaluating options.'}"
    )

    # Persist or update CallSummary
    call_summary = db.query(CallSummary).filter(CallSummary.call_id == call_id).first()
    if not call_summary:
        call_summary = CallSummary(
            tenant_id=tenant_id,
            call_id=call_id
        )
        db.add(call_summary)

    call_summary.summary_text = summary_text
    call_summary.key_insights = key_insights
    call_summary.action_items = action_items
    call_summary.lead_score = lead_score
    call_summary.sentiment = sentiment_res.sentiment
    call_summary.appointment_status = appointment_status
    call_summary.crm_sync_status = crm_status

    # Update customer memory with summary
    if customer_id:
        update_customer_memory(
            db,
            customer_id=customer_id,
            short_term_updates={"conversation_state": "call_completed"},
            long_term_updates={
                "previous_interaction_summaries": [summary_text],
                "previous_objections": extraction.objections
            },
            tenant_id=tenant_id
        )

    db.commit()
    db.refresh(call_summary)
    return call_summary
