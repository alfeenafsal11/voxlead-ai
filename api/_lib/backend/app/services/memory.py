from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from backend.app.config import settings
from backend.app.models import CustomerMemory, Message, Customer, Call

def get_or_create_customer_memory(
    db: Session,
    customer_id: str,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> CustomerMemory:
    """Load or initialize customer memory records."""
    memory = db.query(CustomerMemory).filter(
        CustomerMemory.customer_id == customer_id,
        CustomerMemory.tenant_id == tenant_id
    ).first()

    if not memory:
        memory = CustomerMemory(
            customer_id=customer_id,
            tenant_id=tenant_id,
            short_term_data={
                "conversation_state": "greeting",
                "known_qualification_fields": {},
                "current_language": "en",
                "pending_business_actions": None,
                "recent_topics": []
            },
            long_term_data={
                "customer_profile": {},
                "requirements": [],
                "budget": None,
                "purchase_timeline": None,
                "previous_objections": [],
                "previous_appointments": [],
                "previous_interaction_summaries": []
            }
        )
        db.add(memory)
        db.commit()
        db.refresh(memory)

    return memory

def update_customer_memory(
    db: Session,
    customer_id: str,
    short_term_updates: Optional[Dict[str, Any]] = None,
    long_term_updates: Optional[Dict[str, Any]] = None,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> CustomerMemory:
    """Safely merge updates into short-term and long-term customer memory."""
    memory = get_or_create_customer_memory(db, customer_id, tenant_id)

    st_data = dict(memory.short_term_data or {})
    lt_data = dict(memory.long_term_data or {})

    if short_term_updates:
        for k, v in short_term_updates.items():
            if isinstance(v, dict) and isinstance(st_data.get(k), dict):
                st_data[k].update(v)
            else:
                st_data[k] = v

    if long_term_updates:
        for k, v in long_term_updates.items():
            if isinstance(v, list) and isinstance(lt_data.get(k), list):
                # Append unique items to history lists
                current_list = lt_data[k]
                for item in v:
                    if item not in current_list:
                        current_list.append(item)
                lt_data[k] = current_list
            elif isinstance(v, dict) and isinstance(lt_data.get(k), dict):
                lt_data[k].update(v)
            else:
                lt_data[k] = v

    memory.short_term_data = st_data
    memory.long_term_data = lt_data
    db.commit()
    db.refresh(memory)
    return memory

def save_message(
    db: Session,
    call_id: str,
    role: str,
    content: str,
    audio_url: Optional[str] = None,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> Message:
    """Persist an individual message to database."""
    msg = Message(
        tenant_id=tenant_id,
        call_id=call_id,
        role=role,
        content=content,
        audio_url=audio_url
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_recent_messages(
    db: Session,
    call_id: str,
    limit: int = 10
) -> List[Message]:
    """Retrieve only the most recent N messages to avoid bloated LLM contexts."""
    msgs = (
        db.query(Message)
        .filter(Message.call_id == call_id)
        .order_by(desc(Message.created_at))
        .limit(limit)
        .all()
    )
    # Return in chronological order
    return list(reversed(msgs))
