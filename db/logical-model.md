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
