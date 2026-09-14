import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.database import Base, engine, SessionLocal
from app.seed import seed_reference_data
from app.models import (
    GuideContent, GovernanceRole, GovernanceResponsibility, RoleResponsibility,
    RoleTrainingRequirement, GovernanceRoleAssignment, CourseCompletion, Person,
)


def test_v005_governance_guide_raci_and_learning_seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        seed_reference_data(db)
        assert db.query(GuideContent).count() >= 8
        assert db.query(GovernanceResponsibility).count() >= 8
        assert db.query(GovernanceRole).count() >= 6
        assert db.query(RoleResponsibility).count() >= 1
        assert db.query(RoleTrainingRequirement).count() >= 1
        sophie = db.query(Person).filter_by(email="sophie.martin@example.com").one()
        assert db.query(GovernanceRoleAssignment).filter_by(person_id=sophie.id).count() >= 2
        assert db.query(CourseCompletion).filter_by(person_id=sophie.id).count() >= 4
    finally:
        db.close()
