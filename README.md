# AI Governance Center — v0.0.5

A Docker-ready prototype for operating AI governance from organisation-level governance through the lifecycle of individual AI uses.

## What v0.0.5 adds

### 1. Alembic database migrations
v0.0.5 introduces Alembic as the schema migration layer.

This release contains a **transitional v0.0.4 baseline** because v0.0.1–v0.0.4 used SQLAlchemy `create_all()` rather than migrations.

On Docker startup the backend now:

1. detects whether the database is fresh or pre-v0.0.5;
2. preserves an existing v0.0.4 PostgreSQL database;
3. stamps the v0.0.4 baseline when needed;
4. applies pending migrations with Alembic;
5. starts FastAPI.

From v0.0.5 onward, new schema changes should be delivered as Alembic revisions rather than requiring database-volume deletion.

### 2. AI Governance Guide
A new **Guide** area explains both:

- AI governance as an organisation-wide management system;
- the guided governance journey for one AI use.

The guide currently covers:

- what AI governance is;
- organisation governance vs individual AI-use governance;
- roles, RACI and competence;
- Describe;
- Rules;
- Risks & impacts;
- Safeguards & proof;
- Approval;
- Operate, monitor & reassess.

Guide content is stored as versionable data (`ux.guide_content`) rather than hard-coded only in the frontend. This is intended to become the source for contextual “Why are we asking this?” help.

### 3. People, roles, RACI and competence
The People area now separates:

- **Person** — the physical individual in the organisation directory;
- **Governance role** — a reusable organisational role;
- **Responsibility** — a governance activity;
- **RACI mapping** — how a role participates in a responsibility;
- **Role assignment** — who holds a role and at what scope;
- **Training requirement** — learning required or recommended for a role;
- **Completion** — evidence that an assigned person completed a course.

The seeded RACI matrix is an example governance configuration, not a claim that every organisation must use the same allocation.

### 4. Role-based learning
The prototype now contains an initial learning/competence model:

- courses;
- training programs;
- role training requirements;
- learning assignments;
- course completion and validity;
- training-readiness calculation per person.

The Governance Center is **not intended to become an LMS**. It owns the governance question: *who needs what learning, why, by when, and does a gap affect eligibility?* Course delivery can later be integrated with an LMS such as Workday Learning, Cornerstone, SuccessFactors or Moodle.

### 5. Clear organisation vs AI-use visualisation
The home page now says **“A guided journey for every AI use”**. The per-AI lifecycle is:

`Describe → Rules → Risks → Safeguards → Approve → Operate`

The new **Governance** area is organisation-level and sits above the portfolio. It contains the initial RACI and role-based learning views.

## Reference basis
The design deliberately distinguishes binding law from voluntary standards/frameworks.

- **EU AI Act — Regulation (EU) 2024/1689**, consolidated text used by the prototype. Article 4 is particularly relevant to role/context-sensitive AI literacy; other lifecycle provisions are mapped only where applicable to the actor and AI context.
- **ISO/IEC 42001:2023** — organisation-wide AI management system structure, policies, objectives, processes and continual improvement.
- **NIST AI RMF 1.0 / Playbook** — especially GOVERN 2.1 (clear roles/responsibilities) and GOVERN 2.2 (training enabling people to perform their duties).

Prototype mappings and seeded content require legal/governance validation before production use.

## Run locally

Prerequisites: Docker Desktop / Docker Engine with Compose.

```bash
docker compose up --build
```

Open:

- Frontend: `http://localhost:8080`
- FastAPI / Swagger: `http://localhost:8000/docs`
- Health endpoint: `http://localhost:8000/health`

`http://localhost:8000/` has no root page by design; use `/docs` or `/health` for the backend.

After the first build, normal backend/frontend source edits use mounted development volumes and typically only require:

```bash
docker compose up
```

Rebuild when dependencies, Dockerfiles or Alembic tooling change.

## Upgrade from v0.0.4

Do **not** run `docker compose down -v` just to upgrade to v0.0.5. The migration bridge is specifically intended to preserve the existing PostgreSQL volume.

Replace/update the project files and run:

```bash
docker compose up --build
```

The backend startup logs should show either:

```text
Existing pre-v0.0.5 database detected; stamping v0.0.4 baseline.
```

followed by migration to head, or a normal `alembic upgrade head` on an already-migrated database.

If you intentionally want a completely clean prototype database:

```bash
docker compose down -v
docker compose up --build
```

## Development migration workflow

Create a new revision after changing the SQLAlchemy data model:

```bash
cd backend
alembic revision -m "describe schema change"
```

Implement `upgrade()` and `downgrade()`, then test:

```bash
alembic upgrade head
```

Do not use `Base.metadata.create_all()` as a substitute for future production migrations.

## Validation

v0.0.5 passes the prototype integration suite covering:

- controlled country/person directory;
- rules evaluation;
- risk and safeguard workflow;
- approval/monitoring/reassessment;
- guide content;
- dynamic governance roles/RACI;
- role-based training requirements and seeded completion records.

Current local test result: **6 passed**.

## Current limitations

- Authentication and authorisation are not yet implemented.
- Role eligibility currently considers mandatory training status but does not yet enforce all segregation-of-duty rules in workflow decisions.
- RACI editing is seeded/read-only in the UI; persistence is already modelled for future editing.
- Learning integrations are not implemented yet.
- The regulatory knowledge base is intentionally incomplete and must not be treated as legal advice or a complete EU AI Act conformity assessment.
- Alembic’s v0.0.4 baseline is transitional; v0.0.5 is the point from which migrations become authoritative.

## License

This project is licensed under the **Apache License 2.0**.

You may use, modify, and distribute the software, including for commercial purposes, subject to the terms of the license. See [LICENSE](LICENSE) for the full license text.
