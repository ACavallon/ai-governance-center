import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import init_database, SessionLocal
from app.seed import seed_reference_data
from app.schemas import AIUseCreate, RiskUpdate, ControlImplementationUpdate, EvidenceCreate, ApprovalDecisionCreate, ObservationCreate, ChangeEventCreate
from app.service import (
    create_ai_use, run_rules_check, initialize_risk_review, get_phase_c_summary,
    update_risk_evaluation, update_control_implementation, add_control_evidence,
    create_approval_decision, get_monitoring_summary, add_monitoring_observation,
    create_change_event,
)
from app import models


def test_phase_d_approval_monitoring_and_reassessment():
    init_database()
    db = SessionLocal()
    try:
        seed_reference_data(db)
        owner = db.query(models.Person).filter_by(email="anna.rossi@example.com").first()
        approver = db.query(models.Person).filter_by(email="sophie.martin@example.com").first()
        created = create_ai_use(db, AIUseCreate(
            name="Phase D recruitment",
            business_purpose="Rank applicants for recruiter review",
            business_process="Recruitment",
            owner_person_id=owner.id,
            system_name="Phase D Talent AI",
            system_purpose="Rank job applicants",
            supply_model="third_party",
            supplier_name="Phase D Vendor",
            function="ranking",
            decision_domain="employment",
            human_final_decision=True,
            affected_population="job_applicants",
            countries=["FR", "DE"],
        ))
        run_rules_check(db, created["case_id"])
        phase_c = initialize_risk_review(db, created["case_id"], owner.id)
        for risk in phase_c["risks"]:
            update_risk_evaluation(db, risk["id"], "MEDIUM", "MEDIUM", "Reviewed for approval test")
        phase_c = get_phase_c_summary(db, created["case_id"])
        for safeguard in phase_c["safeguards"]:
            update_control_implementation(db, safeguard["id"], "IMPLEMENTED", owner.id, "Implemented for test")
            add_control_evidence(db, safeguard["id"], EvidenceCreate(
                title=f"Evidence for {safeguard['control_code']}", evidence_type="PROCEDURE", artifact_reference="test://evidence"
            ))
        approval = create_approval_decision(db, created["case_id"], ApprovalDecisionCreate(
            decision_authority_id=approver.id, outcome="APPROVED", rationale="Ready for controlled production"
        ))
        assert approval["decision"]["outcome"] == "APPROVED"
        assert approval["baseline"]["content_hash"]
        monitoring = get_monitoring_summary(db, created["case_id"])
        assert monitoring["active"] is True
        assert len(monitoring["definitions"]) >= 4
        obs = add_monitoring_observation(db, monitoring["definitions"][0]["id"], ObservationCreate(value=1.0))
        assert obs["threshold_status"] == "OK"
        change = create_change_event(db, created["case_id"], ChangeEventCreate(
            change_type="MODEL_VERSION", description="Supplier model version changed", materiality="MATERIAL",
            old_state={"version": "1"}, new_state={"version": "2"}
        ))
        assert change["reassessment_id"]
        assert change["state"] == "REASSESSMENT"
    finally:
        db.close()
