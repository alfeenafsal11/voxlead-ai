import re
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from backend.app.config import settings
from backend.app.models import Call, Customer, Message
from backend.app.voice.agent import get_voice_system_prompt
from backend.app.services.rag import retrieve_relevant_chunks, RAG_FALLBACK_RESPONSE
from backend.app.services.memory import (
    get_or_create_customer_memory,
    update_customer_memory,
    save_message,
    get_recent_messages
)
from backend.app.services.lead_intelligence import (
    extract_lead_from_dialogue,
    update_lead_information,
    analyze_sentiment
)

logger = logging.getLogger("voxlead.orchestrator")

# Common Hindi detection keywords
HINDI_KEYWORDS = ["namaste", "kya", "hai", "mujhe", "aap", "kaise", "chahiye", "kitna", "dhanyawad", "batao", "bataiye", "hoga"]

def detect_language(text: str, current_lang: str = "en") -> str:
    """Detect if customer is speaking English or Hindi."""
    words = re.findall(r'\b\w+\b', text.lower())
    hindi_hits = sum(1 for w in words if w in HINDI_KEYWORDS)
    # Check for Devanagari Unicode block
    has_devanagari = any('\u0900' <= char <= '\u097F' for char in text)

    if has_devanagari or hindi_hits >= 2:
        return "hi"
    return current_lang

def generate_voice_llm_response(
    messages_history: List[Dict[str, str]],
    system_prompt: str,
    rag_context: Optional[str] = None,
    language: str = "en"
) -> str:
    """Generate LLM response using OpenAI or consultative mock agent."""
    if settings.OPENAI_API_KEY and not settings.MOCK_MODE:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            full_system = system_prompt
            if rag_context:
                full_system += f"\n\nVerified Knowledge Base Evidence:\n{rag_context}\n\nGround your answer strictly on the above facts."

            msgs = [{"role": "system", "content": full_system}]
            msgs.extend(messages_history)

            res = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=msgs,
                temperature=0.3,
                max_tokens=250
            )
            return res.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI error in voice generation: {e}")

    # Fallback / Mock consultative responses
    latest_user_msg = messages_history[-1]["content"].lower() if messages_history else ""

    # Multilingual response in Hindi
    if language == "hi":
        if any(w in latest_user_msg for w in ["demo", "meeting", "ha", "theek", "shikhar", "batao", "dikha"]):
            return "नमस्ते! मैं आपके लिए हमारे सॉल्यूशंस इंजीनियर के साथ एक लाइव डेमो बुक कर सकती हूँ। क्या कल दोपहर 2 बजे का समय आपके लिए ठीक रहेगा?"
        if any(w in latest_user_msg for w in ["price", "kitna", "cost", "rupaye", "paisa"]):
            return "हमारे VoxLead CRM के प्लान $29 प्रति यूजर से शुरू होते हैं। क्या आप अपनी टीम के साइज के बारे में बता सकते हैं?"
        return "नमस्ते! मैं VoxLead से Ava हूँ। मैं आपके सेल्स प्रोसेस को ऑटोमेट करने में कैसे मदद कर सकती हूँ?"

    # Consultative sales workflow in English
    if "yes" in latest_user_msg or "confirm" in latest_user_msg or "book it" in latest_user_msg or "sounds good" in latest_user_msg:
        return (
            "Fantastic! I have confirmed your appointment for tomorrow at 2:00 PM UTC. "
            "A calendar invite and demonstration link have been sent to your email. "
            "Is there anything specific your team would like us to highlight during the walkthrough?"
        )

    if any(k in latest_user_msg for k in ["price", "cost", "pricing", "tier", "how much"]):
        if rag_context:
            return (
                f"Our plans start at $29 per user per month for the Starter tier, and $79 for our most popular Professional tier "
                f"which includes the full AI voice agent and automated HubSpot integration. How many sales reps are on your team?"
            )
        return "Our Professional tier is $79 per user monthly with unlimited pipelines and AI voice minutes. How large is your team?"

    if any(k in latest_user_msg for k in ["spreadsheets", "sheets", "excel", "manual"]):
        return (
            "Spreadsheets are very common for early stage tracking, but as teams scale, manual updates typically cost each rep 8-10 hours weekly. "
            "VoxLead automatically qualifies leads and updates records in real time. Would you like to see a quick 20-minute demo this week?"
        )

    if any(k in latest_user_msg for k in ["demo", "demonstration", "schedule", "meet", "booking", "time"]):
        return (
            "I would be delighted to set that up! We have an opening with our Senior Solutions Engineer tomorrow at 2:00 PM UTC. "
            "Would that time work for your schedule?"
        )

    return (
        "Hello! I am Ava from VoxLead AI. We help sales teams eliminate manual admin work and qualify leads 24/7 with autonomous voice agents. "
        "What are you currently looking to achieve with your sales pipeline?"
    )

def process_voice_turn(
    db: Session,
    call_id: str,
    customer_input: str,
    override_language: Optional[str] = None,
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> Dict[str, Any]:
    """
    Execute full voice processing pipeline for a single dialogue turn:
    1. STT Transcript intake & customer message persistence
    2. Language detection and memory sync
    3. RAG retrieval for grounding
    4. Lead qualification & sentiment analysis
    5. Action determination (confirmation check for booking/CRM)
    6. Conversational response generation
    7. Assistant message persistence
    """
    call = db.query(Call).filter(Call.id == call_id).first()
    if not call:
        raise ValueError(f"Call session {call_id} not found")

    customer_id = call.customer_id
    if not customer_id:
        # Create an anonymous customer record if not attached
        cust = Customer(tenant_id=tenant_id, name="Prospective Buyer")
        db.add(cust)
        db.commit()
        db.refresh(cust)
        customer_id = cust.id
        call.customer_id = customer_id
        db.commit()

    # 1. Persist customer input message
    save_message(db, call_id=call_id, role="user", content=customer_input, tenant_id=tenant_id)

    # 2. Language tracking
    current_lang = override_language or call.language or "en"
    detected_lang = detect_language(customer_input, current_lang)
    if detected_lang != call.language:
        call.language = detected_lang
        db.commit()

    # 3. Load & sync customer memory
    memory = get_or_create_customer_memory(db, customer_id, tenant_id)
    update_customer_memory(
        db,
        customer_id,
        short_term_updates={"current_language": detected_lang},
        tenant_id=tenant_id
    )

    # 4. RAG retrieval
    rag_context = ""
    sources = []
    # If the user asks an informational question, search knowledge base
    if any(q in customer_input.lower() for q in ["what", "how", "price", "cost", "feature", "policy", "faq", "tier", "support", "security", "hubspot", "sheet"]):
        chunks = retrieve_relevant_chunks(db, customer_input, tenant_id=tenant_id, top_k=3)
        if chunks:
            rag_context = "\n\n".join([f"[{c.document_title}]: {c.content}" for c in chunks])
            sources = [{"title": c.document_title, "filename": c.filename, "similarity": c.similarity} for c in chunks]

    # 5. Extract lead details and analyze sentiment from recent conversation
    recent_msgs = get_recent_messages(db, call_id, limit=6)
    transcript_so_far = "\n".join([f"{m.role}: {m.content}" for m in recent_msgs])

    extraction = extract_lead_from_dialogue(transcript_so_far)
    sentiment_res = analyze_sentiment(customer_input)

    # Update Lead record with extracted qualifications
    lead = update_lead_information(
        db,
        customer_id=customer_id,
        extraction=extraction,
        sentiment=sentiment_res.sentiment,
        tenant_id=tenant_id
    )

    # 6. Action determination
    action_triggered = None
    input_lower = customer_input.lower()
    if any(conf in input_lower for conf in ["yes", "confirm", "book it", "please do", "sounds good", "2 pm"]):
        # Check if an appointment was previously offered
        st_data = memory.short_term_data or {}
        if st_data.get("conversation_state") in ("booking_proposed", "qualifying", "greeting"):
            action_triggered = "book_appointment"
            update_customer_memory(
                db,
                customer_id,
                short_term_updates={"conversation_state": "appointment_confirmed", "pending_business_actions": None},
                tenant_id=tenant_id
            )

    # If proposing demo
    if any(d in input_lower for d in ["demo", "demonstration", "schedule", "meet", "calendar"]):
        update_customer_memory(
            db,
            customer_id,
            short_term_updates={"conversation_state": "booking_proposed"},
            tenant_id=tenant_id
        )

    # 7. Generate LLM response
    system_prompt = get_voice_system_prompt(detected_lang)
    formatted_history = [{"role": m.role, "content": m.content} for m in recent_msgs]

    response_text = generate_voice_llm_response(
        formatted_history, system_prompt, rag_context, language=detected_lang
    )

    # 8. Persist assistant message
    save_message(db, call_id=call_id, role="assistant", content=response_text, tenant_id=tenant_id)

    # Mock audio URL for TTS
    audio_url = f"/api/voice/audio_stream?call_id={call_id}&t={datetime.now(timezone.utc).timestamp()}"

    return {
        "call_id": call_id,
        "customer_id": customer_id,
        "language": detected_lang,
        "response_text": response_text,
        "lead_score": lead.score,
        "lead_classification": lead.classification,
        "sentiment": sentiment_res.sentiment,
        "action_triggered": action_triggered,
        "sources": sources,
        "audio_url": audio_url
    }
