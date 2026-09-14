import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import init_database, SessionLocal
from app.seed import seed_reference_data
from app.schemas import AIUseCreate
from app.service import create_ai_use, run_rules_check, initialize_risk_review, get_phase_c_summary
from app import models


def test_phase_c_risks_and_safeguards_are_created():
    init_database()
    db = SessionLocal()
    try:
        seed_reference_data(db)
        owner = db.query(models.Person).filter_by(email="anna.rossi@example.com").first()
        created = create_ai_use(db, AIUseCreate(
            name="Phase C test recruitment",
            business_purpose="Rank applicants for recruiter review",
            business_process="Recruitment",
            owner_person_id=owner.id,
            system_name="Test Talent AI",
            system_purpose="Rank job applicants",
            supply_model="third_party",
            supplier_name="Phase C Test Vendor",
            function="ranking",
            decision_domain="employment",
            human_final_decision=True,
            affected_population="job_applicants",
            countries=["FR", "DE"],
        ))
        run_rules_check(db, created["case_id"])
        result = initialize_risk_review(db, created["case_id"], owner.id)
        assert result["summary"]["risk_count"] >= 3
        assert result["summary"]["safeguard_count"] >= 4
        assert any(x["control_code"] == "CTRL-HO-001" for x in result["safeguards"])
        assert any("applicant" in x["title"].lower() or "group" in x["title"].lower() for x in result["risks"])
    finally:
        db.close()
