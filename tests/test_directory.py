import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.database import init_database, SessionLocal
from app.seed import seed_reference_data
from app import models


def test_country_directory_and_people_seeded():
    init_database()
    db = SessionLocal()
    try:
        seed_reference_data(db)
        assert db.query(models.Country).count() == 249
        assert db.get(models.Country, "FR").eu_member is True
        assert db.get(models.Country, "US").eu_member is False
        assert db.query(models.Person).filter(models.Person.status == "ACTIVE").count() >= 3
        assert db.query(models.Group).filter_by(group_type="COMMITTEE").count() >= 1
    finally:
        db.close()
