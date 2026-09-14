import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./governance-dev.db")
SCHEMAS = ["core", "org", "ai", "normative", "rules", "governance", "assessment", "risk", "control", "monitoring", "event", "ux", "audit", "learning"]

class Base(DeclarativeBase):
    pass

if DATABASE_URL.startswith("sqlite"):
    schema_map = {name: None for name in SCHEMAS}
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        execution_options={"schema_translate_map": schema_map},
    )
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_database() -> None:
    if not DATABASE_URL.startswith("sqlite"):
        with engine.begin() as conn:
            for schema in SCHEMAS:
                conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    Base.metadata.create_all(engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
