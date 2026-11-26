import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from backend.app.database import Base
from backend.app.config import settings

def generate_uuid() -> str:
    return str(uuid.uuid4())

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True, index=True)
    phone = Column(String(50), nullable=True, index=True)
    company = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    leads = relationship("Lead", back_populates="customer", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="customer", cascade="all, delete-orphan")
    memory = relationship("CustomerMemory", back_populates="customer", uselist=False, cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_customers_tenant_email", "tenant_id", "email"),
    )

class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)

    score = Column(Integer, default=0, nullable=False)
    classification = Column(String(20), default="cold", nullable=False)  # hot, warm, cold
    sentiment = Column(String(20), default="neutral", nullable=False)    # positive, neutral, negative, frustrated
    intent = Column(String(255), nullable=True)

    # Qualification criteria
    requirement = Column(Text, nullable=True)
    budget = Column(Float, nullable=True)
    timeline = Column(String(100), nullable=True)       # e.g., "within 30 days"
    company_size = Column(Integer, nullable=True)
    decision_maker = Column(Boolean, nullable=True)
    objections = Column(JSON, default=list, nullable=False)

    completeness_score = Column(Float, default=0.0, nullable=False)
    raw_extraction = Column(JSON, default=dict, nullable=False)

    hubspot_contact_id = Column(String(100), nullable=True)
    hubspot_deal_id = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="leads")

class Call(Base):
    __tablename__ = "calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id = Column(String(128), unique=True, nullable=False, index=True)
    room_name = Column(String(128), nullable=True)

    status = Column(String(30), default="in_progress", nullable=False)  # in_progress, completed, failed, abandoned
    language = Column(String(20), default="en", nullable=False)
    start_time = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="calls")
    messages = relationship("Message", back_populates="call", cascade="all, delete-orphan", order_by="Message.created_at")
    summary = relationship("CallSummary", back_populates="call", uselist=False, cascade="all, delete-orphan")
    appointments = relationship("Appointment", back_populates="call")

class Message(Base):
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    audio_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    call = relationship("Call", back_populates="messages")

class CustomerMemory(Base):
    __tablename__ = "customer_memory"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    short_term_data = Column(JSON, default=dict, nullable=False)
    long_term_data = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="memory")

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=True)
    metadata_json = Column(JSON, default=dict, nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    token_count = Column(Integer, default=0, nullable=False)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        Index("ix_document_chunks_doc_chunk", "document_id", "chunk_index"),
    )

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="SET NULL"), nullable=True, index=True)

    title = Column(String(255), nullable=False)
    scheduled_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    calendar_event_id = Column(String(255), nullable=True)
    status = Column(String(50), default="confirmed", nullable=False)  # pending, confirmed, cancelled
    idempotency_key = Column(String(128), unique=True, nullable=True, index=True)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    customer = relationship("Customer", back_populates="appointments")
    call = relationship("Call", back_populates="appointments")

class CallSummary(Base):
    __tablename__ = "call_summaries"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(64), nullable=False, default=settings.DEFAULT_TENANT_ID, index=True)
    call_id = Column(String(36), ForeignKey("calls.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)

    summary_text = Column(Text, nullable=False)
    key_insights = Column(JSON, default=list, nullable=False)
    action_items = Column(JSON, default=list, nullable=False)
    lead_score = Column(Integer, nullable=True)
    sentiment = Column(String(50), nullable=True)
    appointment_status = Column(String(50), nullable=True)
    crm_sync_status = Column(String(50), default="pending", nullable=False)

    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    call = relationship("Call", back_populates="summary")
