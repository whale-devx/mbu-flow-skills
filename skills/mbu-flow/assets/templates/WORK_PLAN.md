---
status: draft
---

# Independent work plan

## Mob decisions
Link the PRD, design decisions and frozen shared contract baseline.

## Units and Bolt
Create a spec per unit and machine-readable plan entries. Show owned paths, test doubles,
acceptance criteria and verification commands. One unit may have multiple tickets.

## Readiness gate
No cross-unit implementation dependencies or overlapping write paths. Replan or merge inseparable work.
Readiness is not live ticket status. max_parallel_units limits suggested batches, not a runtime here.

## Delivery
Specify integration and release gates separately from unit completion.
