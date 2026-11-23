# Autonomous ticket creation

## Authority

An operator must approve `.mbu-flow/policy.yaml`, set `autonomy.enabled: true` and allowlist
exact repositories. `--apply` is explicit execution within that grant, not a per-ticket
approval prompt. Never self-enable a policy or widen scope. A GitHub fine-grained token
needs issue read/write access for the allowlisted repository, not repository administration.
Supply it through `MBUFLOW_GITHUB_TOKEN`; never save it to documents, YAML or logs.

The alpha supports GitHub.com list/create only. It does not update, close, assign, label,
link sub-issues, change Projects fields, transition Jira, merge or deploy. Unknown schema
fields/providers are rejected instead of being silently ignored. MCP-enabled agents can
follow the same procedure, but direct connector calls do not inherit the helper's journal
or enforcement automatically. Do not bypass a failed helper using a connector.

## Procedure

Validate the entire plan and policy. `tickets` without flags renders an offline preview.
`--check` reads GitHub without writing; `--apply` scans open and closed issues, ignores PRs,
resolves exact identity markers and creates only missing, unambiguous items. Matches with
changed human content or duplicate markers halt the batch before new writes. Closed matches
are reused without reopening. Same-title unmarked tickets require manual review.

Identity is derived from repository + project + intent + unit + ticket key, not title.
Exact markers and same-title checks are NOT semantic duplicate detection. Review similar
existing issues during planning. Each local intent has a cumulative ticket quota.

## Journal, retries and concurrency

`.mbu-flow/local/tickets.sqlite3` records identity, payload fingerprint, outcome and minimal
audit events; no token or full issue body is stored. `tickets.lock` permits one local writer.
An operation is persisted before POST. Lost responses are reconciled from remote markers.
A pending operation absent remotely is **uncertain**, not safe to repeat automatically.

Use one authoritative writer/root per repository. Different clones, worktrees and machines
do not share the local lock or quota. Distributed exactly-once delivery is not promised.
There are no automatic POST retries; API rate-limit/permission failures stop the run.
Mutating requests are paced. Issue scans cap at 100 pages and fail closed if incomplete.

After a process crash, verify the writer is stopped before removing a stale lock. Preserve
the SQLite file. Inspect remote issues and audit events; resolve ambiguous/pending records
with an operator, not by deleting state and retrying. A fresh clone loses local protection.
