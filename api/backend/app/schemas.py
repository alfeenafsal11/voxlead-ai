from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Health & Status ---
class HealthResponse(BaseModel):
    status: str
    version: str
    database: str
    pgvector: str
    mock_mode: bool

# --- Authentication & Tenant ---
class Token(BaseModel):
    access_token: str
    token_type: str
    tenant_id: str

class TokenData(BaseModel):
    username: Optional[str] = None
    tenant_id: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str
    tenant_id: Optional[str] = None

# --- Customer ---
class CustomerBase(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None

class CustomerCreate(CustomerBase):
    tenant_id: Optional[str] = None

class CustomerUpdate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: str
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

# --- Lead Intelligence & Scoring ---
class LeadExtractionResult(BaseModel):
    customer_name: Optional[str] = Field(None, description="Extracted customer full or first name")
    email: Optional[str] = Field(None, description="Extracted email address")
    phone: Optional[str] = Field(None, description="Customer contact phone number")
    company_name: Optional[str] = Field(None, description="Company or organization name")
    industry: Optional[str] = Field(None, description="Industry or business domain")
    company_size: Optional[int] = Field(None, description="Number of employees or team members")
    budget: Optional[float] = Field(None, description="Stated budget in numerical format")
    product_requirement: Optional[str] = Field(None, description="Specific business requirement or needed product")
    purchase_timeline: Optional[str] = Field(None, description="Timeline for making a purchase or decision")
    decision_making_authority: Optional[bool] = Field(None, description="True if customer is a key decision maker")
    objections: List[str] = Field(default_factory=list, description="List of concerns or objections raised")
    customer_intent: Optional[str] = Field(None, description="Customer intent e.g. schedule demo, evaluate pricing, explore features")

class SentimentResult(BaseModel):
    sentiment: str = Field(description="Must be one of: positive, neutral, negative, frustrated")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence score")
    reasoning: Optional[str] = Field(None, description="Brief justification for sentiment score")

class LeadResponse(BaseModel):
    id: str
    tenant_id: str
    customer_id: str
    score: int
    classification: str  # hot, warm, cold
    sentiment: str
    intent: Optional[str] = None
    requirement: Optional[str] = None
    budget: Optional[float] = None
    timeline: Optional[str] = None
    company_size: Optional[int] = None
    decision_maker: Optional[bool] = None
    objections: List[str] = []
    completeness_score: float = 0.0
    hubspot_contact_id: Optional[str] = None
    hubspot_deal_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

# --- Messages & Calls ---
class MessageCreate(BaseModel):
    role: str
    content: str
    audio_url: Optional[str] = None

class MessageResponse(BaseModel):
    id: str
    call_id: str
    role: str
    content: str
    audio_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class CallCreate(BaseModel):
    customer_id: Optional[str] = None
    language: Optional[str] = "en"

class CallResponse(BaseModel):
    id: str
    tenant_id: str
    customer_id: Optional[str] = None
    session_id: str
    room_name: Optional[str] = None
    status: str
    language: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}

# --- LiveKit Voice Session ---
class LiveKitTokenRequest(BaseModel):
    room_name: str
    participant_name: str
    customer_id: Optional[str] = None
    language: Optional[str] = "en"

class LiveKitTokenResponse(BaseModel):
    token: str
    server_url: str
    room_name: str
    participant_name: str
    session_id: str

# --- Customer Memory ---
class MemoryUpdate(BaseModel):
    short_term_data: Optional[Dict[str, Any]] = None
    long_term_data: Optional[Dict[str, Any]] = None

class CustomerMemoryResponse(BaseModel):
    id: str
    customer_id: str
    short_term_data: Dict[str, Any]
    long_term_data: Dict[str, Any]
    updated_at: datetime

    model_config = {"from_attributes": True}

# --- Documents & RAG ---
class DocumentChunkResponse(BaseModel):
    id: str
    chunk_index: int
    content: str
    token_count: int
    created_at: datetime

    model_config = {"from_attributes": True}

class DocumentResponse(BaseModel):
    id: str
    tenant_id: str
    filename: str
    file_type: str
    title: Optional[str] = None
    metadata_json: Dict[str, Any] = {}
    created_at: datetime
    chunks: List[DocumentChunkResponse] = []

    model_config = {"from_attributes": True}

class RAGQueryResult(BaseModel):
    chunk_id: str
    document_title: str
    filename: str
    content: str
    similarity: float

# --- Appointments & Integrations ---
class CalendarSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    formatted: str

class CalendarAvailabilityRequest(BaseModel):
    start_date: Optional[datetime] = None
    days_ahead: int = 5

class BookAppointmentRequest(BaseModel):
    customer_id: str
    call_id: Optional[str] = None
    title: str = "VoxLead Product Demonstration"
    scheduled_time: datetime
    end_time: Optional[datetime] = None
    idempotency_key: Optional[str] = None

class AppointmentResponse(BaseModel):
    id: str
    tenant_id: str
    customer_id: str
    call_id: Optional[str] = None
    title: str
    scheduled_time: datetime
    end_time: datetime
    calendar_event_id: Optional[str] = None
    status: str
    idempotency_key: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class HubSpotSyncRequest(BaseModel):
    customer_id: str
    deal_name: Optional[str] = None
    amount: Optional[float] = None
    pipeline_stage: Optional[str] = "appointmentscheduled"

class HubSpotSyncResponse(BaseModel):
    success: bool
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    message: str
    is_mock: bool

# --- Call Summaries ---
class CallSummaryResponse(BaseModel):
    id: str
    call_id: str
    summary_text: str
    key_insights: List[str]
    action_items: List[str]
    lead_score: Optional[int] = None
    sentiment: Optional[str] = None
    appointment_status: Optional[str] = None
    crm_sync_status: str
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Dashboard Overview Analytics ---
class DashboardOverview(BaseModel):
    total_calls: int
    total_leads: int
    qualified_leads: int
    hot_leads: int
    warm_leads: int
    cold_leads: int
    average_lead_score: float
    appointments_booked: int
    sentiment_distribution: Dict[str, int]
