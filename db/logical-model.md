# Logical Model — Vertical Slice 0.1

This implementation intentionally covers only the first vertical slice of the frozen LDM v1.0.

## Implemented schemas

- `core`: legal identity, governed-object identity
- `org`: organisation, business unit, responsible party
- `ai`: use case, system, deployment context, geography, affected population, decision involvement
- `normative`: source, source version, atomic requirement
- `rules`: rule, version, evaluation
- `governance`: case, actor role, classification, obligation, action
- `ux`: guided questions, responses
- `audit`: fact provenance

## Key implementation invariants

1. Regulatory classification is not stored on `ai_system`.
2. `deployment_context` is the primary regulatory assessment anchor for use-specific questions.
3. Rule evaluations preserve their complete fact snapshot and rule version.
4. Unknown rule inputs return an indeterminate result, never silent non-applicability.
5. Governance actions are user-facing groupings; obligations remain normative instances.
6. Source authority is retained separately from user-facing guidance.

## v0.0.2 reference-data and people inventory refinement

The implementation now treats countries and people as controlled references rather than free-text values.

### Country directory

`core.country`

- `code` — ISO 3166-1 alpha-2 primary key
- `name`
- `eu_member`
- `eea_member`
- `status`

All current country selectors reference this directory. `ai.deployment_geography.country_code`, `core.legal_entity.country_code`, and `org.person.country_code` are foreign keys to `core.country.code`.

### People directory

`org.person`

- organisation and business-unit membership
- manager relationship
- employee/external identifier
- name and email
- job title / employment type
- country
- authority level
- active validity and status

Governance responsibility fields should reference `org.person` or an assignable `org.group`; arbitrary person-name text is not a source of truth.

### Groups and qualifications

- `org.group` represents `TEAM`, `FUNCTION`, or `COMMITTEE`.
- `org.person_qualification` stores governance-relevant training/eligibility with validity dates.
- `org.role_assignment` stores temporal roles associated with a person/group and optionally a governed object.

This supports future eligibility rules such as requiring a current human-oversight qualification before assigning an overseer.
