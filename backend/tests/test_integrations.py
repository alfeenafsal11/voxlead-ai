import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from backend.app.database import SessionLocal, init_db
from backend.app.models import Customer, Lead, Appointment
from backend.app.services.integrations import (
    get_calendar_provider,
    get_crm_provider,
    book_calendar_appointment,
    sync_lead_to_crm,
    GoogleCalendarProvider,
    HubSpotCRMProvider,
    MockCalendarProvider,
    MockHubSpotCRMProvider
)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_calendar_availability_interface():
    provider = get_calendar_provider()
    now = datetime.now(timezone.utc)
    slots = provider.check_availability(now, days_ahead=3)

    assert len(slots) > 0, "No available slots returned"
    first_slot = slots[0]
    assert first_slot.start_time > now
    assert first_slot.end_time > first_slot.start_time
    assert len(first_slot.formatted) > 5

def test_appointment_booking_and_idempotency(db_session: Session):
    cust = Customer(name="Clara Oswald", email="clara@tardis.co", company="Tardis Travel")
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)

    slot_time = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=2, hours=3)
    idemp_key = f"key_{uuid.uuid4().hex}"

    # Initial booking
    appt1 = book_calendar_appointment(
        db=db_session,
        customer_id=cust.id,
        title="VoxLead CRM Product Demo",
        scheduled_time=slot_time,
        idempotency_key=idemp_key
    )
    assert appt1.id is not None
    assert appt1.status == "confirmed"
    assert appt1.calendar_event_id is not None

    # Idempotent re-request must return identical appointment without duplicate
    appt2 = book_calendar_appointment(
        db=db_session,
        customer_id=cust.id,
        title="VoxLead CRM Product Demo",
        scheduled_time=slot_time,
        idempotency_key=idemp_key
    )
    assert appt2.id == appt1.id

    # Collision test: Booking overlapping slot with different idempotency key must fail
    with pytest.raises(ValueError, match="already has an active appointment"):
        book_calendar_appointment(
            db=db_session,
            customer_id=cust.id,
            title="Conflicting Meeting",
            scheduled_time=slot_time + timedelta(minutes=10),
            idempotency_key=f"key_{uuid.uuid4().hex}"
        )

    # Clean up
    db_session.delete(appt1)
    db_session.delete(cust)
    db_session.commit()

def test_crm_contact_and_deal_sync(db_session: Session):
    cust = Customer(name="David Miller", email="david@fintech.io", company="Fintech Peak")
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)

    lead = Lead(
        customer_id=cust.id,
        score=85,
        classification="hot",
        budget=45000.0,
        requirement="Enterprise Sales AI CRM"
    )
    db_session.add(lead)
    db_session.commit()

    sync_res = sync_lead_to_crm(db_session, customer_id=cust.id)
    assert sync_res["success"] is True
    assert sync_res["contact_id"] is not None
    assert sync_res["deal_id"] is not None

    db_session.refresh(lead)
    assert lead.hubspot_contact_id == sync_res["contact_id"]
    assert lead.hubspot_deal_id == sync_res["deal_id"]

    # Clean up
    db_session.delete(lead)
    db_session.delete(cust)
    db_session.commit()

def test_provider_classes_completeness():
    # Verify real Google Calendar provider structure
    gcal = GoogleCalendarProvider("dummy_id", "dummy_secret", "dummy_refresh")
    assert gcal.is_mock() is False
    assert hasattr(gcal, "check_availability")
    assert hasattr(gcal, "create_event")

    # Verify real HubSpot CRM provider structure
    hs = HubSpotCRMProvider("dummy_token")
    assert hs.is_mock() is False
    assert hasattr(hs, "search_contact")
    assert hasattr(hs, "create_or_update_contact")
    assert hasattr(hs, "create_deal")
