import pytest
from sqlalchemy.orm import Session
from backend.app.database import SessionLocal, init_db
from backend.app.models import Customer, Lead
from backend.app.schemas import LeadExtractionResult
from backend.app.services.lead_intelligence import (
    calculate_lead_score,
    analyze_sentiment,
    extract_lead_from_dialogue,
    update_lead_information
)

@pytest.fixture(scope="module")
def db_session():
    init_db()
    db = SessionLocal()
    yield db
    db.close()

def test_deterministic_scoring_hot_lead():
    # Ideal lead meeting all 5 BANT criteria:
    # 30 (budget) + 25 (timeline) + 20 (decision maker) + 15 (requirement) + 10 (company size) = 100
    extraction = LeadExtractionResult(
        customer_name="Samantha Ray",
        company_name="Apex Global",
        company_size=45,
        budget=50000.0,
        product_requirement="Autonomous Sales CRM with Voice AI",
        purchase_timeline="within 30 days",
        decision_making_authority=True,
        customer_intent="schedule product demonstration"
    )

    score, classification, completeness = calculate_lead_score(extraction)
    assert score == 100, f"Expected 100 points, got {score}"
    assert classification == "hot"
    assert completeness == 1.0

def test_deterministic_scoring_warm_and_cold_lead():
    # Warm lead: Budget ($25k = 30) + requirement (15) = 45 -> warm
    warm_extraction = LeadExtractionResult(
        budget=25000.0,
        product_requirement="CRM software",
        purchase_timeline="next year",
        decision_making_authority=False,
        company_size=5  # outside 10-500
    )
    w_score, w_class, _ = calculate_lead_score(warm_extraction)
    assert 40 <= w_score <= 69, f"Expected warm score, got {w_score}"
    assert w_class == "warm"

    # Cold lead: No budget, no timeline, no decision maker, only small size
    cold_extraction = LeadExtractionResult(
        company_size=3
    )
    c_score, c_class, completeness = calculate_lead_score(cold_extraction)
    assert 0 <= c_score <= 39, f"Expected cold score, got {c_score}"
    assert c_class == "cold"
    assert completeness < 0.5

def test_safe_missing_information_extraction():
    transcript = "Hello, I am just browsing your website today."
    extraction = extract_lead_from_dialogue(transcript)

    assert extraction.budget is None
    assert extraction.company_size is None
    assert extraction.purchase_timeline is None
    assert extraction.decision_making_authority is None
    assert isinstance(extraction.objections, list)

def test_structured_extraction_from_scenario():
    # Test the required sales scenario:
    # 45-member company, manually manages leads, budget 50,000, evaluating within 30 days, decision maker
    scenario_transcript = (
        "Hi, my name is Alex Vance from Lumina Health. We have 45 sales reps and we currently manage all our "
        "leads manually on spreadsheets. We need an autonomous AI CRM to automate our outreach. "
        "Our budget is around 50,000 dollars. I am the head of sales and I make the final decision. "
        "We are evaluating software to deploy within 30 days and would love to schedule a demo."
    )

    extraction = extract_lead_from_dialogue(scenario_transcript)
    assert extraction.customer_name == "Alex Vance"
    assert extraction.company_size == 45
    assert extraction.budget == 50000.0
    assert extraction.purchase_timeline == "within 30 days"
    assert extraction.decision_making_authority is True
    assert "spreadsheets" in str(extraction.objections).lower()

    score, classification, completeness = calculate_lead_score(extraction)
    assert score >= 70
    assert classification == "hot"

def test_sentiment_analysis_categories():
    pos_res = analyze_sentiment("This sounds wonderful! I am very excited to see the demo.")
    assert pos_res.sentiment == "positive"
    assert pos_res.confidence >= 0.7

    frust_res = analyze_sentiment("This is ridiculous and a complete waste of time!")
    assert frust_res.sentiment == "frustrated"

    neg_res = analyze_sentiment("Your pricing is bad and too expensive.")
    assert neg_res.sentiment == "negative"

    neu_res = analyze_sentiment("Could you please provide the technical documentation?")
    assert neu_res.sentiment == "neutral"

def test_update_lead_information_db(db_session: Session):
    cust = Customer(name="Jordan Bell", email="jordan@acme.org")
    db_session.add(cust)
    db_session.commit()
    db_session.refresh(cust)

    extraction = LeadExtractionResult(
        customer_name="Jordan Bell",
        company_name="Acme Corporation",
        company_size=60,
        budget=60000.0,
        product_requirement="Lead qualification voice bot",
        purchase_timeline="within 30 days",
        decision_making_authority=True
    )

    lead = update_lead_information(db_session, cust.id, extraction, sentiment="positive")
    assert lead.customer_id == cust.id
    assert lead.score == 100
    assert lead.classification == "hot"
    assert lead.sentiment == "positive"

    # Verify customer company updated
    db_session.refresh(cust)
    assert cust.company == "Acme Corporation"

    # Clean up
    db_session.delete(cust)
    db_session.commit()
