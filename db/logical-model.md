# Logical model — v0.0.3 implementation slice

The implementation remains a partial realization of the canonical AI Governance metamodel. The current vertical slice covers:

`Organisation → AI Use → AI System → Deployment Context → Rules Check → Obligation/Action → Assessment → Risk/Impact → Safeguard → Evidence`.

## Implemented schemas

- `core`: country, legal entity, governed object
- `org`: organisation, business unit, person, group, role assignment, qualification
- `ai`: use case, system, deployment, geography, affected population, decision involvement
- `normative`: source, source version, atomic requirement
- `rules`: rule, rule version, evaluation
- `governance`: governance case, classification, obligation, action, actor-role assignment
- `assessment`: assessment template, assessment
- `risk`: risk, impact, risk evaluation
- `control`: objective, control, requirement/risk mappings, control implementation, evidence
- `ux`: guided question/response
- `audit`: fact provenance

`monitoring` and `event` schemas are reserved in the runtime for the next lifecycle slice.

## Key implementation invariants

1. AI Act classification is not stored as a scalar `risk_level` on the AI system.
2. Deployment Context is the default use-level governance anchor.
3. People and countries are controlled references rather than free text.
4. Risk is represented as cause → event → consequence and historical evaluations are appended rather than overwritten.
5. Control is a reusable safeguard; ControlImplementation is how the safeguard is implemented for a governed object.
6. Evidence existence does not itself imply control effectiveness.
7. Seeded risk patterns are suggestions and are not automatic factual/legal conclusions.
8. Normative requirements and management/risk safeguards remain traceable but semantically distinct.

## v0.0.4 — Phase D implementation slice

Phase D adds the first operational lifecycle objects:

- `governance.gate_result`
- `governance.decision`
- `governance.approval_baseline`
- `monitoring.monitoring_plan`
- `monitoring.monitoring_definition`
- `monitoring.threshold_rule`
- `monitoring.observation`
- `event.governance_event`
- `event.change_event`
- `event.incident`
- `event.reassessment`

The prototype lifecycle is now:

`REGISTERED → CLASSIFIED → ASSESSED → APPROVED/ACTIVE → MONITORING → REASSESSMENT`

Approval snapshots the governed configuration and current governance conclusions instead of treating approval as a mutable boolean. Monitoring observations and operational events are immutable history. Changes/incidents may create a reassessment without deleting or rewriting the approved baseline.

Operational severity, change materiality and regulatory classifications remain distinct concepts. Full AI Act substantial-modification and serious-incident logic will be introduced through the versioned rules layer rather than hard-coded into event records.
