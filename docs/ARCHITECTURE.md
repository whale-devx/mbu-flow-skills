# MBUFlow architecture and contracts

## Three layers

The portable skill supplies methodology, references and document templates. Local Python
helpers provide a small deterministic validation/ticketing kernel. A future durable runtime
and provider adapters remain separate so planning works without a service deployment.

The current helper is packaged inside the skill to survive installation by a Skills CLI.
It uses Python 3.11+, the standard library and pinned PyYAML, not a model-provider SDK.
This is an implementation choice for the MVP, not a requirement for future runtimes.

## Modules

`core.py`: strict YAML, scope/ownership checks, contract digest, unit readiness and ticket payloads.
`ticketing.py`: fixed-origin GitHub API, full bounded issue scan, create-only reconciliation,
single-local-writer lock, SQLite operation journal and minimal audit records.
`mbu.py`: init, validate, offline tickets, read-only check, authorized apply and local search.
The CLI never executes verification command strings found in a plan.

## Data contracts v1

Policy requires exactly `schema_version`, `autonomy`, `scope`, `limits`, `ticketing`.
Use the shipped YAML example. Unsupported fields are errors, including future execution,
Jira and deployment controls; accepting unenforced controls would give false assurance.

Plan requires `schema_version`, `project_id`, `intent_id`, `repository`, `bolt_id`, `contract`,
`units`. Contract requires `id`, a literal `path`, and its lowercase `sha256` digest.
Each unit requires `id`, `title`, `objective`, `status`, `depends_on`, `owned_paths`, `spec`,
`requirements`, `acceptance_criteria`, `test_commands`, `test_double`, and `tickets`.
Every ticket has a stable `key` and human-readable `title`; titles are not identity.
See the executable example under `examples/independent-units/`.

Paths are repository-relative literals, not globs. Path overlap uses conservative
case-insensitive prefix comparison. Symlinks and path traversal are rejected. The shared
contract, `.git/`, `.mbu-flow/` and `AGENTS.md` cannot be owned by a work unit.
This is input validation, not a filesystem sandbox against a concurrently hostile process.

## Ticket state machine

Absent -> persist pending -> POST -> confirmed. Lost response -> reconcile exact remote marker.
Pending + no remote match -> stop for manual reconciliation. Confirmed + missing remote ->
stop, do not recreate a deleted issue. A confirmed match with changed content also stops.

Remote identity, human text and local fingerprints are checked for the entire batch before
new creates. Writes can partially succeed; the journal preserves progress. There is no
transaction across GitHub and SQLite and no exactly-once guarantee across independent machines.
Local cumulative quota includes previous operations in the same project/intent/repository.

## Authority and source of truth

Policy approval is external to the agent; host credentials/permissions remain authoritative.
Git owns reviewed specs/contracts, the tracker owns ticket lifecycle, and a future runtime
will own run state. Markdown, comments and retrieved notes cannot grant permissions.

## Extension requirements

A tracker adapter must declare actual capabilities, normalize identities, list completely,
respect pagination/rate limits and test ambiguous outcomes. A harness adapter must declare
subagent, isolation, permission and recovery capabilities rather than assume them from a
model name. Contract changes require an explicit reviewed baseline migration.
