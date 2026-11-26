import re
import json
from typing import Dict, Any, Tuple, Optional, List
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.models import Lead, Customer
from backend.app.schemas import LeadExtractionResult, SentimentResult

def calculate_lead_score(extraction: LeadExtractionResult) -> Tuple[int, str, float]:
    """
    Deterministic lead scoring:
    - Budget compatibility: 30 points (budget >= 10,000 or stated affordable)
    - Purchase timeline within 30 days: 25 points
    - Decision-maker identified: 20 points
    - Clear requirement: 15 points
    - Suitable company size: 10 points (10-500 employees)

    Returns:
    - score (0 to 100)
    - classification ('hot', 'warm', 'cold')
    - completeness_score (0.0 to 1.0)
    """
    score = 0
    evaluated_criteria = 0
    total_criteria = 5

    # 1. Budget compatibility (30 points)
    if extraction.budget is not None:
        evaluated_criteria += 1
        # If budget is at least $10,000 or positive value
        if extraction.budget >= 10000:
            score += 30
        elif extraction.budget > 0:
            score += 15

    # 2. Purchase timeline within 30 days (25 points)
    if extraction.purchase_timeline is not None:
        evaluated_criteria += 1
        tl = extraction.purchase_timeline.lower()
        if any(term in tl for term in ["30 days", "immediately", "asap", "this month", "2 weeks", "urgent", "now", "within a month"]):
            score += 25
        elif any(term in tl for term in ["quarter", "60 days", "90 days", "3 months"]):
            score += 12

    # 3. Decision-maker identified (20 points)
    if extraction.decision_making_authority is not None:
        evaluated_criteria += 1
        if extraction.decision_making_authority is True:
            score += 20
        elif extraction.decision_making_authority is False:
            score += 5

    # 4. Clear requirement (15 points)
    if extraction.product_requirement:
        evaluated_criteria += 1
        req_clean = extraction.product_requirement.strip()
        if len(req_clean) >= 5 and req_clean.lower() not in ("none", "unknown", "n/a"):
            score += 15

    # 5. Suitable company size (10 points: 10-500 employees)
    if extraction.company_size is not None:
        evaluated_criteria += 1
        if 10 <= extraction.company_size <= 500:
            score += 10
        elif extraction.company_size > 0:
            score += 5

    completeness_score = round(evaluated_criteria / total_criteria, 2)

    # Classification: 70-100 Hot, 40-69 Warm, 0-39 Cold
    if score >= 70:
        classification = "hot"
    elif score >= 40:
        classification = "warm"
    else:
        classification = "cold"

    return score, classification, completeness_score

def analyze_sentiment(text_content: str) -> SentimentResult:
    """Classify sentiment into positive, neutral, negative, or frustrated."""
    if not text_content or not text_content.strip():
        return SentimentResult(sentiment="neutral", confidence=1.0, reasoning="No text provided")

    # If OpenAI API is available, use structured prompt
    if settings.OPENAI_API_KEY and not settings.MOCK_MODE:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            prompt = (
                f"Analyze the sentiment of the following customer speech. "
                f"Respond with JSON: {{\"sentiment\": \"positive|neutral|negative|frustrated\", \"confidence\": float, \"reasoning\": string}}.\n\n"
                f"Text: \"{text_content}\""
            )
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = json.loads(resp.choices[0].message.content)
            sentiment_val = data.get("sentiment", "neutral").lower()
            if sentiment_val not in ("positive", "neutral", "negative", "frustrated"):
                sentiment_val = "neutral"
            return SentimentResult(
                sentiment=sentiment_val,
                confidence=float(data.get("confidence", 0.9)),
                reasoning=data.get("reasoning", "")
            )
        except Exception:
            pass

    # Deterministic sentiment classifier for mock/offline execution
    text_lower = text_content.lower()

    frustrated_indicators = ["ridiculous", "terrible", "waste of time", "furious", "unacceptable", "annoying", "angry"]
    negative_indicators = ["don't like", "disappointed", "too expensive", "bad", "slow", "won't work", "poor"]
    positive_indicators = ["great", "excellent", "love", "perfect", "sounds good", "interested", "excited", "awesome", "impressive", "demo"]

    if any(k in text_lower for k in frustrated_indicators):
        return SentimentResult(sentiment="frustrated", confidence=0.95, reasoning="Caller expressed frustration keywords")
    elif any(k in text_lower for k in negative_indicators):
        return SentimentResult(sentiment="negative", confidence=0.85, reasoning="Caller expressed negative remarks")
    elif any(k in text_lower for k in positive_indicators):
        return SentimentResult(sentiment="positive", confidence=0.90, reasoning="Caller expressed positive interest")
    else:
        return SentimentResult(sentiment="neutral", confidence=0.80, reasoning="Standard consultative dialogue")

def extract_lead_from_dialogue(transcript: str) -> LeadExtractionResult:
    """Extract structured lead attributes from conversation transcript."""
    if settings.OPENAI_API_KEY and not settings.MOCK_MODE:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            system_prompt = (
                "You are an expert sales intelligence extractor. Extract structured lead data from the sales conversation. "
                "Any missing or unmentioned attributes MUST strictly be null. "
                "Output strictly a JSON object matching these keys: "
                "customer_name, email, phone, company_name, industry, company_size (int), budget (float), "
                "product_requirement, purchase_timeline, decision_making_authority (bool), objections (list of strings), customer_intent."
            )
            resp = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Transcript:\n{transcript}"}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            data = json.loads(resp.choices[0].message.content)
            return LeadExtractionResult(**data)
        except Exception:
            pass

    # Deterministic rule-based extraction for mock / offline fallback
    name = None
    email = None
    phone = None
    company = None
    industry = None
    company_size = None
    budget = None
    product_requirement = None
    purchase_timeline = None
    decision_making_authority = None
    objections = []
    customer_intent = None

    # Name extraction
    name_match = re.search(r"(?:my name is|i am|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", transcript, re.I)
    if name_match:
        name = name_match.group(1).strip()

    # Email extraction
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', transcript)
    if email_match:
        email = email_match.group(0).strip()

    # Phone extraction
    phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', transcript)
    if phone_match:
        phone = phone_match.group(0).strip()

    # Company name
    company_match = re.search(r"(?:at|with|from|company is)\s+([A-Z][A-Za-z0-9\s]+?)(?:,|\.|\s+and|\s+we|\s+with|\n|$)", transcript)
    if company_match:
        comp_candidate = company_match.group(1).strip()
        if comp_candidate.lower() not in ("my", "our", "the", "a", "an"):
            company = comp_candidate

    # Company size
    size_match = re.search(r'(\d+)\s*(?:people|employees|members|reps|users|team members|sales reps)', transcript, re.I)
    if size_match:
        company_size = int(size_match.group(1))

    # Budget
    budget_match = re.search(r'(?:budget\s*(?:is|of|around|\s)*[\$]?|[\$])\s*(\d{1,3}(?:,\d{3})*|\d+)(?:\s*(?:k|thousand|dollars))?', transcript, re.I)
    if budget_match:
        raw_val = budget_match.group(1).replace(",", "")
        b_val = float(raw_val)
        if "k" in budget_match.group(0).lower() or "thousand" in budget_match.group(0).lower():
            b_val *= 1000
        budget = b_val

    # Timeline
    if re.search(r'(?:within|in|next)\s*(?:30\s*days|month|few weeks|immediately)', transcript, re.I):
        purchase_timeline = "within 30 days"
    elif re.search(r'(?:quarter|q[1-4]|60\s*days|90\s*days|3\s*months)', transcript, re.I):
        purchase_timeline = "within 90 days"

    # Decision maker
    if re.search(r'(?:i make the decision|decision maker|i am the decision maker|i decide|head of|vp|director|ceo|cro)', transcript, re.I):
        decision_making_authority = True
    elif re.search(r'(?:not the decision maker|need to ask my boss|committee decides)', transcript, re.I):
        decision_making_authority = False

    # Product requirement
    req_match = re.search(r'(?:need|looking for|want|evaluating)\s+([^.,\n]+?)(?:\s+to|\.|\,|$)', transcript, re.I)
    if req_match:
        product_requirement = req_match.group(1).strip()

    # Intent
    if re.search(r'(?:demo|demonstration|walkthrough)', transcript, re.I):
        customer_intent = "schedule product demonstration"
    elif re.search(r'(?:pricing|quote|cost)', transcript, re.I):
        customer_intent = "evaluate pricing"

    # Objections
    if re.search(r'(?:spreadsheets|google sheets)', transcript, re.I):
        objections.append("Currently managing leads manually on spreadsheets")
    if re.search(r'(?:expensive|cost too high)', transcript, re.I):
        objections.append("Concerns regarding overall cost")

    return LeadExtractionResult(
        customer_name=name,
        email=email,
        phone=phone,
        company_name=company,
        industry=industry,
        company_size=company_size,
        budget=budget,
        product_requirement=product_requirement,
        purchase_timeline=purchase_timeline,
        decision_making_authority=decision_making_authority,
        objections=objections,
        customer_intent=customer_intent
    )

def update_lead_information(
    db: Session,
    customer_id: str,
    extraction: LeadExtractionResult,
    sentiment: str = "neutral",
    tenant_id: str = settings.DEFAULT_TENANT_ID
) -> Lead:
    """Calculate lead score and persist or update lead record in database."""
    score, classification, completeness = calculate_lead_score(extraction)

    lead = db.query(Lead).filter(
        Lead.customer_id == customer_id,
        Lead.tenant_id == tenant_id
    ).first()

    if not lead:
        lead = Lead(
            customer_id=customer_id,
            tenant_id=tenant_id,
        )
        db.add(lead)

    lead.score = score
    lead.classification = classification
    lead.sentiment = sentiment
    lead.intent = extraction.customer_intent
    lead.requirement = extraction.product_requirement
    lead.budget = extraction.budget
    lead.timeline = extraction.purchase_timeline
    lead.company_size = extraction.company_size
    lead.decision_maker = extraction.decision_making_authority
    lead.objections = extraction.objections
    lead.completeness_score = completeness
    lead.raw_extraction = extraction.model_dump()

    # Also update customer record if name, company, or email were extracted
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer:
        if extraction.customer_name and not customer.name:
            customer.name = extraction.customer_name
        if extraction.company_name and not customer.company:
            customer.company = extraction.company_name
        if extraction.email and not customer.email:
            customer.email = extraction.email
        if extraction.phone and not customer.phone:
            customer.phone = extraction.phone

    db.commit()
    db.refresh(lead)
    return lead
