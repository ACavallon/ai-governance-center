# AI Governance Center — Prototype v0.0.4

Docker-ready prototype for an integrated AI Governance Center grounded in the EU AI Act and designed to support broader AI management practices. v0.0.4 completes the first end-to-end lifecycle slice: **Risk & Impact → Safeguards → Proof → Approval → Monitoring → Reassessment**.

> **Prototype notice:** the regulatory knowledge base is intentionally incomplete. Seeded EU AI Act rules are illustrative, legally-grounded screening logic used to validate the architecture; they are not a complete codification of Regulation (EU) 2024/1689.

## What works

1. Guided non-expert onboarding for an AI use.
2. Canonical storage of use case, system, deployment context, affected population, geography and decision involvement.
3. Closed ISO 3166-1 country directory (249 entries).
4. People inventory with organisation, business unit, manager, job title, country, authority level and qualifications.
5. Business-owner selection from the People inventory rather than free text.
6. Explainable EU AI Act Rules Check with versioned rules and source references.
7. Generated governance actions from regulatory screening.
8. **Risk & Impact workspace** with contextual suggested risk scenarios.
9. Cause → event → impact presentation for non-expert risk review.
10. Historical risk evaluations with explicit uncertainty.
11. Reusable **Safeguard / Control library** mapped to risk and selected EU AI Act requirements.
12. Per-deployment safeguard implementations with implementation status.
13. **Proof / Evidence** records linked to safeguard implementations.
14. AI Card journey now covers Describe → Rules → Risks → Safeguards → Approve → Monitor.
15. **Approval gate** with accountable approver and blocking-readiness checks.
16. **Frozen approval baseline** capturing the system, classifications, risks, safeguards and proof at decision time.
17. Automatic operational **Monitoring Plan** after approval.
18. Manual monitoring observations with breach-triggered reassessment.
19. User-reported **change events** with materiality and dependency-aware reassessment start point.
20. User-reported **incidents**, explicitly separating operational severity from legal serious-incident classification.
21. Operational event/reassessment history in the UI.

## Architecture

- **Backend:** FastAPI + SQLAlchemy
- **Database:** PostgreSQL in Docker; SQLite fallback for local smoke tests
- **Frontend:** dependency-free HTML/CSS/JS prototype served by nginx
- **Rules:** structured JSON expressions evaluated by the backend
- **Model:** domain schemas for `core`, `org`, `ai`, `normative`, `rules`, `governance`, `assessment`, `risk`, `control`, `monitoring`, `event`, `ux`, and `audit`

## Run with Docker

First build (or after dependency/Dockerfile changes):

```bash
docker compose up --build
```

Open:

- Frontend: http://localhost:8080
- Backend API / Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Development workflow / hot reload

v0.0.4 keeps the development mounts introduced in v0.0.3, so backend/frontend edits are reflected without rebuilding the image.

After the first build, normal code edits **do not require rebuilding the containers**:

```bash
docker compose up
```

- Python backend changes trigger Uvicorn auto-reload.
- HTML/CSS/JavaScript files are served directly from the mounted `frontend/` folder; refresh the browser to see changes.
- Re-run `docker compose up --build` when Python dependencies, Dockerfiles, or other image-level dependencies change.

Stop the stack with `Ctrl+C`, or:

```bash
docker compose down
```

## Upgrading from v0.0.3

v0.0.4 is additive: it adds approval, monitoring and event/reassessment tables without removing or renaming v0.0.3 columns. `Base.metadata.create_all()` will create the new structures at startup, so a database reset should normally **not** be necessary.

If you are carrying an older incompatible prototype database and receive `UndefinedColumn` / schema errors, reset the prototype volume once:

```bash
docker compose down -v
docker compose up --build
```

**Important:** proper Alembic migrations are still required before the prototype stores data that must be preserved across schema upgrades.

## Phase C user flow

For an AI use that has completed a Rules Check:

1. Open the AI Card.
2. Click **Start risk review**.
3. Review contextual risk scenarios (suggestions, not automatic conclusions).
4. Review or adjust the risk rating and uncertainty.
5. Review suggested safeguards.
6. Mark safeguards as implemented when the actual process/control exists.
7. Attach proof such as procedures, training records, test reports or system configuration references.

The backend preserves the distinction between:

- risk scenario vs. risk category;
- risk vs. impact;
- reusable control vs. deployment-specific implementation;
- safeguard implementation vs. evidence;
- legal obligation vs. risk-based safeguard.

## Phase D user flow

After risks, safeguards and proof are ready:

1. Open **Approval** from the AI Card.
2. The prototype evaluates the G07 approval gate and lists blockers.
3. An eligible governance approver records the accountable decision.
4. Approval creates a hashed baseline snapshot and moves the deployment to `ACTIVE`.
5. A monitoring plan is created automatically.
6. Record monitoring observations from the Monitor workspace.
7. A qualitative `FAIL`, `BREACH` or `UNACCEPTABLE` result creates a monitoring-breach event and reassessment.
8. Report material changes or incidents; the governance state moves to `REASSESSMENT` when review is required.

> Phase D is intentionally a thin operational prototype. Monitoring thresholds, substantial-modification logic, serious-incident classification and reporting deadlines still require full normative rule implementation.

## Main API endpoints

### Directory / inventory

- `GET /api/reference/countries`
- `GET /api/people`
- `POST /api/people`
- `POST /api/people/{id}/qualifications`
- `GET /api/groups`
- `GET /api/business-units`
- `GET /api/ai-uses`
- `POST /api/ai-uses`
- `GET /api/ai-uses/{id}/card`

### Regulatory screening

- `POST /api/governance-cases/{id}/rules-check`

### Risk, safeguards and evidence

- `GET /api/governance-cases/{id}/phase-c`
- `POST /api/governance-cases/{id}/risk-review/initialize`
- `POST /api/risks/{id}/evaluation`
- `PATCH /api/control-implementations/{id}`
- `POST /api/control-implementations/{id}/evidence`

### Approval and continuous governance

- `GET /api/governance-cases/{id}/approval`
- `POST /api/governance-cases/{id}/approval`
- `GET /api/governance-cases/{id}/monitoring`
- `POST /api/monitoring-definitions/{id}/observations`
- `POST /api/governance-cases/{id}/changes`
- `POST /api/governance-cases/{id}/incidents`

## Tests

From the repository root:

```bash
pytest -q
```

The test suite covers the rule engine, reference directories, Phase C risk/safeguard creation, and the Phase D approval → monitoring → reassessment lifecycle.

## Current limitations / next engineering steps

- The complete EU AI Act is **not yet encoded**.
- Safeguard recommendations are seeded prototype mappings and need a governed control-library authoring/review process.
- Evidence is currently metadata/reference only; binary file storage comes later.
- Risk scoring is currently a configurable qualitative prototype rather than a finalized organisational methodology.
- Alembic migrations should be introduced before further non-additive schema changes.
- Phase D is implemented as a prototype, but monitoring logic is still deliberately simple and requires configurable real-world thresholds and data integrations.
- Serious-incident classification/reportability and substantial-modification classification are not yet complete legal rule sets.
- Approval currently uses prototype internal readiness rules; these need configurable organisational gate policies.
