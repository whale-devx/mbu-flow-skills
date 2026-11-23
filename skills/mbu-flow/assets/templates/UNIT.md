---
status: draft
---

# Unit specification

## Objective and requirements
Link stable requirement IDs and state the independent user/technical outcome.

## Scope and exclusions
List literal owned paths; shared interfaces and files owned by other units are read-only.

## Contract and independence
Reference the frozen contract digest and executable test double. Explain why this unit does not
need another unit's unfinished implementation. If it does, replan or merge the scope.

## Acceptance and verification
Define observable acceptance criteria, independent test commands and integration expectations.
The machine-readable plan carries readiness and ticket identity; do not duplicate mutable tracker state.

## Evidence and handoff
Record PR, commit, actual test results, remaining risks and reusable knowledge.
