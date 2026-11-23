---
status: draft
---

# Shared contract baseline

## Interfaces
Define inputs, outputs, data types, error semantics, events and versioning.
Prefer links to executable schemas such as OpenAPI/JSON Schema rather than duplicate definitions.

## Fixtures and compatibility
Define deterministic provider/consumer fixtures, negative cases and compatibility rules.

## Freeze record
Record a reviewed baseline and SHA-256 in .mbu-flow/plan.yaml before parallel construction.
A hash identifies bytes, not review approval or semantic correctness. Changes require impact review.

## Ownership
Shared contract changes are outside individual unit ownership. Integrate against the same baseline.
