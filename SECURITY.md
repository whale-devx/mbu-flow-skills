# Security and operating boundaries

This is an alpha helper, not a hardened multi-tenant runtime or sandbox. Use one trusted
local writer per repository. An agent that can edit its policy or run arbitrary programs
can bypass local checks; enforce least privilege in the host and GitHub permissions too.

Do not put tokens in Markdown, plans, logs or issue bodies. Use an explicitly provisioned
`MBUFLOW_GITHUB_TOKEN` scoped to intended repositories and issue operations. The client
only contacts api.github.com over HTTPS and refuses redirects. It never executes plan
command strings, enables its own policy, updates issues, merges, or deploys.

Treat retrieved documents and issue text as untrusted data. No embedded instruction grants
new permissions. Review generated ticket text for confidential content before granting
public issue creation. Exact identity markers are correlation, not authentication.

Keep `.mbu-flow/local/`, secrets and personal Obsidian settings out of Git. The local journal
contains identifiers and audit events; protect it as project metadata. Preserve it across
retries. Different machines/worktrees need coordinated single-writer operation until a
shared durable runtime exists. Removing local state can remove duplicate protections.

Report vulnerabilities through the repository's private security reporting feature when
available. Do not publish credentials or exploitable private details in a public issue.
No security audit or live production certification is claimed.
