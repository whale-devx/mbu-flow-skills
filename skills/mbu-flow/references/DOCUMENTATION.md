# Adaptive documents

Reuse existing paths and content. Never overwrite a PRD, ADR or agent-instruction file just
to fit a template. `init` is opt-in, adds draft files only, and preserves existing content.
It does not produce reviewed requirements or automatically link every generated document.

| Work | Minimum useful context |
| --- | --- |
| Small bug | Existing issue, reproduction, expected behavior, test evidence |
| Backend feature | PRD/spec, technical design, contracts, units, verification |
| UI feature | PRD, UX/UI states, applicable design system, contracts, units |
| New production system | Product, design, data/security, delivery and operations as needed |

`assets/templates/` includes Vision, PRD, stories, UX/UI, design system, architecture,
technical design, API contracts, data/security, work plan, test strategy, integration,
deployment, runbook, learnings, Unit, Bolt and ADR. Select relevant templates; do not generate
empty documentation for appearance. The helper's minimal/backend/frontend/full profiles
are starting sets, not a substitute for inspecting the repository.

Markdown is the human-readable specification. `.mbu-flow/plan.yaml` owns executable planning
metadata and stable ticket identities. `status: ready` means plan readiness, not tracker
completion. Keep acceptance criteria aligned; the current helper does not semantically
compare PRD text with unit specs. Use explicit human/agent review for that gap.

Trace requirement ID -> design -> contract -> unit -> ticket -> PR -> actual test evidence.
Use draft/reviewed/approved/superseded only when the corresponding event really occurred.
