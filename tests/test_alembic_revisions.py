from pathlib import Path
import re


def test_alembic_revision_ids_fit_default_version_column():
    """Alembic's default version_num column is VARCHAR(32)."""
    versions_dir = Path(__file__).parents[1] / "backend" / "alembic" / "versions"
    revision_pattern = re.compile(r'^revision\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)

    for migration in versions_dir.glob("*.py"):
        match = revision_pattern.search(migration.read_text(encoding="utf-8"))
        assert match, f"No Alembic revision id found in {migration.name}"
        revision_id = match.group(1)
        assert len(revision_id) <= 32, (
            f"Alembic revision id {revision_id!r} in {migration.name} is "
            "longer than the default VARCHAR(32) alembic_version.version_num column"
        )
