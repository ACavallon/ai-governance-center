"""v0.0.4 baseline

Revision ID: 0004_v004_baseline
Revises:
"""
revision = "0004_v004_baseline"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Transitional baseline: v0.0.1-v0.0.4 were created with SQLAlchemy create_all.
    pass

def downgrade():
    pass
