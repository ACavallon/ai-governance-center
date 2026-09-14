"""Database migration bridge introduced in v0.0.5.

Existing v0.0.4 databases are stamped at the transitional baseline and upgraded.
Fresh databases are created from current metadata and stamped at head. From v0.0.5
forward, schema evolution is managed through Alembic revisions.
"""
import subprocess
from sqlalchemy import inspect, text
from .database import engine, Base, SCHEMAS
from . import models  # noqa: F401


def run(*args: str) -> None:
    subprocess.run(["alembic", *args], check=True)


def main() -> None:
    with engine.begin() as conn:
        for schema in SCHEMAS:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    inspector = inspect(engine)
    has_version = inspector.has_table("alembic_version", schema=None)
    has_existing = inspector.has_table("country", schema="core")
    if not has_version:
        if has_existing:
            print("Existing pre-v0.0.5 database detected; stamping v0.0.4 baseline.")
            run("stamp", "0004_v004_baseline")
            run("upgrade", "head")
        else:
            print("Fresh database detected; creating current schema and stamping Alembic head.")
            Base.metadata.create_all(engine)
            run("stamp", "head")
    else:
        run("upgrade", "head")

if __name__ == "__main__":
    main()
