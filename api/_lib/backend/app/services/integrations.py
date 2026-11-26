import os
import uuid
import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import httpx

from backend.app.config import settings
from backend.app.models import Customer, Lead, Appointment
from backend.app.schemas import CalendarSlot

logger = logging.getLogger("voxlead.integrations")

# =====================================================================
# CALENDAR INTEGRATION INTERFACE & PROVIDERS
# =====================================================================

class CalendarProvider(ABC):
    @abstractmethod
    def is_mock(self) -> bool:
        pass

    @abstractmethod
    def check_availability(self, start_date: datetime, days_ahead: int = 5) -> List[CalendarSlot]:
        pass

    @abstractmethod
    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendee_email: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        pass

class MockCalendarProvider(CalendarProvider):
    """
    Deterministic Mock Calendar Provider.
    Provides realistic working hours (10:00 AM, 2:00 PM, 4:00 PM UTC)
    and tracks booked slots to prevent double-booking.
    """
    _booked_slots: set = set()

    def is_mock(self) -> bool:
        return True

    def check_availability(self, start_date: datetime, days_ahead: int = 5) -> List[CalendarSlot]:
        slots: List[CalendarSlot] = []
        base = start_date.replace(hour=0, minute=0, second=0, microsecond=0)

        # Generate candidate slots over the next N business days
        for day in range(1, days_ahead + 1):
            slot_date = base + timedelta(days=day)
            # Skip Saturday and Sunday
            if slot_date.weekday() >= 5:
                continue

            for hour in (10, 14, 16):  # 10:00 AM, 2:00 PM, 4:00 PM
                st = slot_date.replace(hour=hour, minute=0, tzinfo=timezone.utc)
                et = st + timedelta(minutes=45)
                slot_iso = st.isoformat()

                if slot_iso not in self._booked_slots:
                    slots.append(
                        CalendarSlot(
                            start_time=st,
                            end_time=et,
                            formatted=st.strftime("%A, %b %d at %I:%M %p UTC")
                        )
                    )
        return slots

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendee_email: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        slot_iso = start_time.isoformat()
        if slot_iso in self._booked_slots:
            raise ValueError(f"Calendar slot at {slot_iso} is already booked.")

        self._booked_slots.add(slot_iso)
        event_id = f"mock_evt_{uuid.uuid4().hex[:12]}"
        return {
            "success": True,
            "event_id": event_id,
            "html_link": f"https://calendar.google.com/calendar/event?eid={event_id}",
            "summary": summary,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "attendee": attendee_email,
            "is_mock": True
        }

class GoogleCalendarProvider(CalendarProvider):
    """Real Google Calendar API v3 provider."""
    def __init__(self, client_id: str, client_secret: str, refresh_token: str, calendar_id: str = "primary"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.calendar_id = calendar_id

    def is_mock(self) -> bool:
        return False

    def _get_access_token(self) -> str:
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "grant_type": "refresh_token",
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(token_url, data=data)
            resp.raise_for_status()
            return resp.json()["access_token"]

    def check_availability(self, start_date: datetime, days_ahead: int = 5) -> List[CalendarSlot]:
        access_token = self._get_access_token()
        time_min = start_date.isoformat()
        time_max = (start_date + timedelta(days=days_ahead)).isoformat()
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events"
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"timeMin": time_min, "timeMax": time_max, "singleEvents": "true", "orderBy": "startTime"}

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, headers=headers, params=params)
            resp.raise_for_status()
            events = resp.json().get("items", [])

        busy_times = []
        for e in events:
            start_dt = e.get("start", {}).get("dateTime")
            end_dt = e.get("end", {}).get("dateTime")
            if start_dt and end_dt:
                busy_times.append((datetime.fromisoformat(start_dt), datetime.fromisoformat(end_dt)))

        slots: List[CalendarSlot] = []
        base = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        for day in range(1, days_ahead + 1):
            slot_date = base + timedelta(days=day)
            if slot_date.weekday() >= 5:
                continue
            for hour in (10, 14, 16):
                st = slot_date.replace(hour=hour, minute=0, tzinfo=timezone.utc)
                et = st + timedelta(minutes=45)
                # Check collision
                has_collision = any(not (et <= b_start or st >= b_end) for b_start, b_end in busy_times)
                if not has_collision:
                    slots.append(CalendarSlot(start_time=st, end_time=et, formatted=st.strftime("%A, %b %d at %I:%M %p UTC")))
        return slots

    def create_event(
        self,
        summary: str,
        start_time: datetime,
        end_time: datetime,
        attendee_email: Optional[str] = None,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        access_token = self._get_access_token()
        url = f"https://www.googleapis.com/calendar/v3/calendars/{self.calendar_id}/events"
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        payload = {
            "summary": summary,
            "start": {"dateTime": start_time.isoformat()},
            "end": {"dateTime": end_time.isoformat()},
            "description": f"Scheduled by VoxLead AI Autonomous Voice Assistant. Key: {idempotency_key or ''}"
        }
        if attendee_email:
            payload["attendees"] = [{"email": attendee_email}]

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return {
                "success": True,
                "event_id": data.get("id"),
                "html_link": data.get("htmlLink"),
                "summary": summary,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "attendee": attendee_email,
                "is_mock": False
            }

def get_calendar_provider() -> CalendarProvider:
    if (
        settings.GOOGLE_CALENDAR_CLIENT_ID
        and settings.GOOGLE_CALENDAR_CLIENT_SECRET
        and settings.GOOGLE_CALENDAR_REFRESH_TOKEN
        and not settings.MOCK_MODE
    ):
        return GoogleCalendarProvider(
            client_id=settings.GOOGLE_CALENDAR_CLIENT_ID,
            client_secret=settings.GOOGLE_CALENDAR_CLIENT_SECRET,
            refresh_token=settings.GOOGLE_CALENDAR_REFRESH_TOKEN,
            calendar_id=settings.GOOGLE_CALENDAR_CALENDAR_ID
        )
    return MockCalendarProvider()

# =====================================================================
# HUBSPOT CRM INTEGRATION INTERFACE & PROVIDERS
# =====================================================================

class CRMProvider(ABC):
    @abstractmethod
    def is_mock(self) -> bool:
        pass

    @abstractmethod
    def search_contact(self, email: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def create_or_update_contact(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    def create_deal(
        self,
        contact_id: str,
        deal_name: str,
        amount: float,
        pipeline_stage: str = "appointmentscheduled"
    ) -> Dict[str, Any]:
        pass

class MockHubSpotCRMProvider(CRMProvider):
    """In-memory mock HubSpot CRM adapter."""
    _contacts_by_email: Dict[str, Dict[str, Any]] = {}
    _deals: Dict[str, Dict[str, Any]] = {}

    def is_mock(self) -> bool:
        return True

    def search_contact(self, email: str) -> Optional[Dict[str, Any]]:
        return self._contacts_by_email.get(email.lower())

    def create_or_update_contact(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        email = customer_data.get("email", "").lower()
        if not email:
            email = f"lead_{uuid.uuid4().hex[:6]}@demo.voxlead.ai"

        existing = self._contacts_by_email.get(email)
        if existing:
            contact_id = existing["id"]
            existing.update(customer_data)
            return {"contact_id": contact_id, "email": email, "updated": True, "is_mock": True}

        contact_id = f"hs_cont_{uuid.uuid4().hex[:10]}"
        record = {
            "id": contact_id,
            "email": email,
            "firstname": customer_data.get("name", "Unknown"),
            "company": customer_data.get("company", "Unknown"),
            "phone": customer_data.get("phone", ""),
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._contacts_by_email[email] = record
        return {"contact_id": contact_id, "email": email, "created": True, "is_mock": True}

    def create_deal(
        self,
        contact_id: str,
        deal_name: str,
        amount: float,
        pipeline_stage: str = "appointmentscheduled"
    ) -> Dict[str, Any]:
        deal_id = f"hs_deal_{uuid.uuid4().hex[:10]}"
        deal_record = {
            "id": deal_id,
            "contact_id": contact_id,
            "deal_name": deal_name,
            "amount": amount,
            "stage": pipeline_stage,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        self._deals[deal_id] = deal_record
        return {
            "deal_id": deal_id,
            "deal_name": deal_name,
            "amount": amount,
            "stage": pipeline_stage,
            "is_mock": True
        }

class HubSpotCRMProvider(CRMProvider):
    """Real HubSpot CRM API v3 client."""
    BASE_URL = "https://api.hubapi.com"

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    def is_mock(self) -> bool:
        return False

    def search_contact(self, email: str) -> Optional[Dict[str, Any]]:
        url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
        payload = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }]
            }]
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=self.headers, json=payload)
            if resp.status_code == 200:
                results = resp.json().get("results", [])
                if results:
                    return results[0]
            return None

    def create_or_update_contact(self, customer_data: Dict[str, Any]) -> Dict[str, Any]:
        email = customer_data.get("email")
        existing = self.search_contact(email) if email else None

        properties = {
            "firstname": customer_data.get("name", ""),
            "company": customer_data.get("company", ""),
            "phone": customer_data.get("phone", "")
        }
        if email:
            properties["email"] = email

        with httpx.Client(timeout=10.0) as client:
            if existing:
                contact_id = existing["id"]
                url = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
                resp = client.patch(url, headers=self.headers, json={"properties": properties})
                resp.raise_for_status()
                return {"contact_id": contact_id, "email": email, "updated": True, "is_mock": False}
            else:
                url = f"{self.BASE_URL}/crm/v3/objects/contacts"
                resp = client.post(url, headers=self.headers, json={"properties": properties})
                resp.raise_for_status()
                data = resp.json()
                return {"contact_id": data.get("id"), "email": email, "created": True, "is_mock": False}

    def create_deal(
        self,
        contact_id: str,
        deal_name: str,
        amount: float,
        pipeline_stage: str = "appointmentscheduled"
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/crm/v3/objects/deals"
        payload = {
            "properties": {
                "dealname": deal_name,
                "amount": str(amount),
                "dealstage": pipeline_stage,
                "pipeline": "default"
            }
        }
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, headers=self.headers, json=payload)
            resp.raise_for_status()
            deal_data = resp.json()
            deal_id = deal_data.get("id")

            # Associate deal with contact
            assoc_url = f"{self.BASE_URL}/crm/v3/objects/deals/{deal_id}/associations/contacts/{contact_id}/deal_to_contact"
            client.put(assoc_url, headers=self.headers)

            return {
                "deal_id": deal_id,
                "deal_name": deal_name,
                "amount": amount,
                "stage": pipeline_stage,
                "is_mock": False
            }

def get_crm_provider() -> CRMProvider:
    if settings.HUBSPOT_ACCESS_TOKEN and not settings.MOCK_MODE:
        return HubSpotCRMProvider(settings.HUBSPOT_ACCESS_TOKEN)
    return MockHubSpotCRMProvider()

# =====================================================================
# BUSINESS WORKFLOW FUNCTIONS (IDEMPOTENCY & STATE INTEGRATION)
# =====================================================================

def book_calendar_appointment(
    db: Session,
    customer_id: str,
    title: str,
    scheduled_time: datetime,
    end_time: Optional[datetime] = None,
    idempotency_key: Optional[str] = None,
    call_id: Optional[str] = None,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> Appointment:
    """
    Check availability, enforce idempotency, book calendar event via provider,
    and persist local database record.
    """
    if not end_time:
        end_time = scheduled_time + timedelta(minutes=45)

    # 1. Idempotency Check: Prevent duplicate bookings
    if idempotency_key:
        existing_appt = db.query(Appointment).filter(
            Appointment.idempotency_key == idempotency_key,
            Appointment.tenant_id == tenant_id
        ).first()
        if existing_appt:
            logger.info(f"Idempotent booking returned existing appointment {existing_appt.id}")
            return existing_appt

    # 2. Check collision on customer's existing appointments
    collision = db.query(Appointment).filter(
        Appointment.customer_id == customer_id,
        Appointment.status == "confirmed",
        Appointment.scheduled_time < end_time,
        Appointment.end_time > scheduled_time
    ).first()
    if collision:
        raise ValueError(f"Customer already has an active appointment at {collision.scheduled_time}")

    # 3. Retrieve customer email
    cust = db.query(Customer).filter(Customer.id == customer_id).first()
    attendee_email = cust.email if cust else None

    # 4. Invoke Calendar Provider
    provider = get_calendar_provider()
    event_res = provider.create_event(
        summary=title,
        start_time=scheduled_time,
        end_time=end_time,
        attendee_email=attendee_email,
        idempotency_key=idempotency_key
    )

    # 5. Persist to local database
    appt = Appointment(
        tenant_id=tenant_id,
        customer_id=customer_id,
        call_id=call_id,
        title=title,
        scheduled_time=scheduled_time,
        end_time=end_time,
        calendar_event_id=event_res.get("event_id"),
        status="confirmed",
        idempotency_key=idempotency_key
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt

def sync_lead_to_crm(
    db: Session,
    customer_id: str,
    deal_name: Optional[str] = None,
    amount: Optional[float] = None,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> Dict[str, Any]:
    """Synchronize customer and deal information to HubSpot CRM."""
    cust = db.query(Customer).filter(Customer.id == customer_id, Customer.tenant_id == tenant_id).first()
    if not cust:
        raise ValueError(f"Customer {customer_id} not found")

    lead = db.query(Lead).filter(Lead.customer_id == customer_id, Lead.tenant_id == tenant_id).first()

    provider = get_crm_provider()

    # Create / update contact in CRM
    customer_payload = {
        "name": cust.name or "Prospective Customer",
        "email": cust.email or f"lead_{cust.id[:8]}@example.com",
        "company": cust.company or "Unknown Company",
        "phone": cust.phone or ""
    }
    contact_res = provider.create_or_update_contact(customer_payload)
    contact_id = contact_res.get("contact_id")

    # Create deal if lead has requirement or budget
    deal_res = {}
    if lead and (lead.budget or lead.requirement or amount):
        deal_title = deal_name or f"{cust.company or 'Lead'} - VoxLead CRM Opportunity"
        deal_amount = amount or (lead.budget or 35000.0)
        deal_res = provider.create_deal(
            contact_id=contact_id,
            deal_name=deal_title,
            amount=deal_amount,
            pipeline_stage="appointmentscheduled"
        )
        lead.hubspot_contact_id = contact_id
        lead.hubspot_deal_id = deal_res.get("deal_id")
        db.commit()
        db.refresh(lead)

    return {
        "success": True,
        "contact_id": contact_id,
        "deal_id": deal_res.get("deal_id"),
        "is_mock": provider.is_mock(),
        "message": f"Successfully synchronized with {'Mock ' if provider.is_mock() else ''}HubSpot CRM."
    }
