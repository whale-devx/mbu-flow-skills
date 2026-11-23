---
status: draft
---

# Integration plan

## Inputs
List unit PRs and the exact shared contract revision used by all participants.

## Gates
Require real contract and integration tests, CI, review, and risk-appropriate security checks.
Unit tests with mocks do not establish end-to-end compatibility.

## Conflicts and recovery
Route contract changes back to the Mob. Stop affected work, preserve other completed units,
and record replan/rollback decisions. Do not mark a Bolt delivered merely because PRs exist.
