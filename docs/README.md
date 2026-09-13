# AI Governance Center — Vertical Slice 0.1

A Docker-ready prototype implementing the first end-to-end slice of the AI Governance Center:

1. Guided non-expert onboarding for an AI use.
2. Canonical storage of use case, system, deployment context, populations, geography and decision involvement.
3. Explainable rules check with versioned rules and source references.
4. AI Card summary and generated governance actions.

## Architecture

- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL in Docker; SQLite fallback for local smoke tests
- **Frontend:** dependency-free HTML/CSS/JS prototype served by nginx in Docker
- **Rules:** structured JSON expressions evaluated by the backend

## Run with Docker

```bash
docker compose up --build
```

Open http://localhost:8080

Backend API: http://localhost:8000/docs

## Run locally without Docker

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Then serve `frontend/` with any static server, e.g. `python -m http.server 8080 -d frontend`.

The backend automatically falls back to SQLite when `DATABASE_URL` is not set.

## Current seeded regulatory example

The prototype intentionally contains a small, legally-grounded **illustrative** EU AI Act rule set for validating the architecture, not a complete codification of the Regulation. It covers:

- EU scope indicator for EU deployment/use.
- likely deployer role for third-party use.
- employment-ranking high-risk screening candidate.
- transparency screening indicator.

Every result carries a source reference, rule version, facts used and plain-language explanation.
