"""governance guide, roles, RACI and learning

Revision ID: 0005_gov_people_learning
Revises: 0004_v004_baseline
"""
from alembic import op
from sqlalchemy import text
from app.database import Base
from app import models  # noqa: F401

revision = "0005_gov_people_learning"
down_revision = "0004_v004_baseline"
branch_labels = None
depends_on = None

TABLES = [
    "governance.responsibility", "governance.role", "governance.role_responsibility",
    "org.governance_role_assignment", "learning.competency", "learning.course",
    "learning.training_program", "learning.training_program_course",
    "learning.role_training_requirement", "learning.learning_assignment",
    "learning.course_completion", "ux.guide_content",
]

def upgrade():
    bind = op.get_bind()
    bind.execute(text('CREATE SCHEMA IF NOT EXISTS "learning"'))
    for key in TABLES:
        Base.metadata.tables[key].create(bind=bind, checkfirst=True)

def downgrade():
    bind = op.get_bind()
    for key in reversed(TABLES):
        Base.metadata.tables[key].drop(bind=bind, checkfirst=True)
