# AI Governance Center — Prototype v0.0.2

Docker-ready prototype for the AI Governance Center. This version implements the first governance vertical slice plus controlled reference data for countries and people.

## What works

1. Guided non-expert onboarding for an AI use.
2. Canonical storage of use case, system, deployment context, affected population, geography and decision involvement.
3. Closed **ISO 3166-1 country directory** (249 entries) used by geography/person selectors.
4. **People inventory** with organisation, business unit, manager, job title, country, authority level and qualification records.
5. Business-owner selection from the People inventory instead of free text.
6. Assignable groups (team/function/committee) and temporal role-assignment data model.
7. Explainable EU AI Act Rules Check with versioned rules and source references.
8. AI Card summary and generated governance actions.

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

### Upgrading from v0.0.1

v0.0.2 changes the database schema and the prototype does not yet include Alembic migrations. Reset the local Docker database once before starting v0.0.2:

```bash
docker compose down -v
docker compose up --build
```

This deletes **prototype local data**. Do not use this reset approach once the application starts containing data that must be retained; schema migrations are planned before that point.

## Run locally without Docker

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Then serve `frontend/` with any static server, for example:

```bash
python -m http.server 8080 -d frontend
```

The backend falls back to SQLite when `DATABASE_URL` is not set.

## Directory/reference API

- `GET /api/reference/countries`
- `GET /api/people`
- `POST /api/people`
- `POST /api/people/{id}/qualifications`
- `GET /api/groups`
- `POST /api/groups`
- `GET /api/business-units`

## Current seeded regulatory example

The prototype intentionally contains a small, legally-grounded **illustrative** EU AI Act rule set for validating the architecture, not a complete codification of the Regulation. It covers:

- EU scope indicator for EU deployment/use.
- likely deployer role for third-party use.
- employment-ranking high-risk screening candidate.
- transparency screening indicator.

Every result carries a source reference, rule version, facts used and plain-language explanation.
