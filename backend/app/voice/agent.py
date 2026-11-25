import os
import uuid
import logging
from typing import Dict, Any, Optional
from livekit.api import AccessToken, VideoGrants

from backend.app.config import settings
from backend.app.schemas import LiveKitTokenResponse

logger = logging.getLogger("voxlead.voice")

VOICE_SYSTEM_PROMPT_EN = """
You are Ava, a senior consultative AI Sales Voice Agent representing VoxLead CRM.
Your objective is to conduct a consultative, natural sales conversation with prospective buyers, answer technical and pricing questions using verified knowledge, qualify the lead, and offer to schedule a product demonstration.

Key Guidelines:
1. Speak concisely, warmly, and professionally as in a live telephone conversation (1 to 3 short sentences per turn).
2. Ask only ONE relevant question at a time. Never overwhelm the caller with a barrage of questions.
3. Avoid repeating questions whose answers the customer has already shared.
4. Answer product, pricing, feature, and policy questions strictly from verified knowledge. Never fabricate numbers or terms.
5. Qualify the prospect naturally against BANT:
   - Need / Product requirements
   - Company size / Sales team size
   - Budget
   - Decision-making authority
   - Purchase timeline
6. Empathetically acknowledge customer objections (e.g., using spreadsheets, budget constraints) before pivoting to business value.
7. Always ask for explicit customer confirmation before booking a meeting or updating external CRM systems.
8. If the customer speaks Hindi, respond naturally in Hindi (or Hinglish) and maintain that language throughout the conversation.
"""

VOICE_SYSTEM_PROMPT_HI = """
आप Ava हैं, VoxLead CRM की वरिष्ठ परामर्शदाता AI सेल्स वॉयस एजेंट।
आपका उद्देश्य ग्राहकों के साथ विनम्र और पेशेवर बातचीत करना, सत्यापित ज्ञान के आधार पर प्रश्नों का उत्तर देना, आवश्यकताओं को समझना और डेमो शेड्यूल करना है।

दिशानिर्देश:
1. फ़ोन पर बातचीत की तरह संक्षिप्त और स्वाभाविक भाषा में बोलें (1 से 2 वाक्य प्रति टर्न)।
2. एक समय में केवल एक ही प्रश्न पूछें।
3. कंपनी के नियमों और कीमतों की सही जानकारी दें, मनगढ़ंत जानकारी न दें।
4. ग्राहक की भाषा का सम्मान करें और उसी भाषा में उत्तर दें।
5. मीटिंग बुक करने से पहले ग्राहक की स्पष्ट पुष्टि लें।
"""

def generate_livekit_token(
    room_name: str,
    participant_name: str,
    customer_id: Optional[str] = None,
    language: str = "en"
) -> LiveKitTokenResponse:
    """Generate short-lived LiveKit access token with participant metadata."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"

    grant = VideoGrants(
        room_join=True,
        room=room_name,
        can_publish=True,
        can_subscribe=True,
        can_publish_data=True
    )

    metadata = {
        "customer_id": customer_id or "",
        "session_id": session_id,
        "language": language,
    }

    token = (
        AccessToken(settings.LIVEKIT_API_KEY, settings.LIVEKIT_API_SECRET)
        .with_identity(f"user_{uuid.uuid4().hex[:8]}")
        .with_name(participant_name)
        .with_metadata(str(metadata))
        .with_grants(grant)
        .to_jwt()
    )

    logger.info(f"Generated LiveKit token for room={room_name}, participant={participant_name}, session={session_id}")

    return LiveKitTokenResponse(
        token=token,
        server_url=settings.LIVEKIT_URL,
        room_name=room_name,
        participant_name=participant_name,
        session_id=session_id
    )

def get_voice_system_prompt(language: str = "en") -> str:
    """Select prompt based on preferred conversation language."""
    if language.lower() in ("hi", "hindi"):
        return VOICE_SYSTEM_PROMPT_HI
    return VOICE_SYSTEM_PROMPT_EN
