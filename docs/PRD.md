# MBUFlow product requirements

Status: implementation baseline for 0.1.0-alpha.1.
Source: the user-supplied Complete Skill Blueprint, with the agreed MBUFlow naming.
This is a scoped implementation of that blueprint, not a replacement methodology.

## Goal

Connect product intent, software design, independent work units, tickets, agents and
verified delivery without forcing a new model provider, project tracker or document layout.
Preserve Mob collaboration, Unit boundaries and Bolt delivery cycles throughout.

## Requirements and implementation mapping

| ID | Blueprint requirement | Alpha implementation / remaining scope |
| --- | --- | --- |
| REQ-001 | Autonomous by operator-approved policy | Explicit enablement, repository allowlist, quotas; no self-granted authority |
| REQ-002 | Mob, Unit, Bolt remain central | Portable workflow; human review at policy-defined boundaries |
| REQ-003 | No cross-unit implementation prerequisites | Declared dependency rejection, disjoint paths, frozen contract digest, test-double presence; semantic proof requires real tests |
| REQ-004 | Parallel-first | Suggested bounded batches; actual agent dispatch is V2 |
| REQ-005 | PRD, UX/UI, technical/design documents | Adaptive templates and non-overwriting scaffolding |
| REQ-006 | Autonomous multi-ticket orchestration | GitHub create-only, one-to-many unit/ticket identity, exact-marker reconciliation; semantic dedup/update are future work |
| REQ-007 | GitHub Projects and Jira | Interfaces/guidance in design only; no live adapter yet |
| REQ-008 | Persistent knowledge, optional Obsidian | Markdown conventions, ADR/learnings templates, lexical retrieval; enhanced dashboards/impact analysis later |
| REQ-009 | Recovery and audit | Local ticket journal/unknown-outcome protection; not a durable multi-agent runtime |
| REQ-010 | Traceability and quality gates | IDs, contract digest, unit spec, criteria and test commands in ticket bodies; actual PR/CI sync later |
| REQ-011 | Provider independence | Self-contained Markdown skill with optional Python helper; no provider SDK; host compatibility must be tested separately |
| REQ-012 | Reuse existing workflows and documents | Preserve existing files; no forced application restructure or duplicate document source of truth |

## Non-goals for this alpha

No claim of production readiness, universal harness certification, AWS compatibility
certification, semantic independence proof, distributed locking, Jira sync, automatic PR merge,
secret discovery or production deployment. Do not ship empty packages masquerading as a runtime.

## Acceptance gates

The skill is discoverable by standard name/description metadata. All local references resolve.
Offline preview performs no network access. Invalid ownership, dependencies, scope, contract
drift or unsupported policy fields block execution. Repeating a confirmed ticket operation
reuses it; an uncertain unconfirmed operation is not automatically retried. Human edits cause
review, not overwrite. Tests never contact GitHub. Report live verification separately.

## Preserved end-to-end target

Intent -> Mob elaboration -> PRD/design -> frozen contracts -> independent units -> autonomous
tickets -> parallel Bolt construction -> verified integration -> knowledge and tracker sync.
A change triggers impact analysis and replanning; it must not silently widen the approved scope.
