# MBUFlow roadmap and truthful capability status

The phases below preserve the user-supplied Blueprint. Completing one phase does not imply
all later capabilities exist. Work is grouped into independent units only after interfaces
are baselined; roadmap rows are not falsely advertised as immediately parallel tasks.

| Phase | Target | Current state |
| --- | --- | --- |
| MVP | Portable skill, adaptive PRD/design, independent unit planning, autonomous GitHub ticket creation | Alpha implementation; helper tests are offline; live acceptance remains separate |
| V1 | Executable contract validation, ownership enforcement against diffs, Projects V2, semantic duplicate review, richer retrieval | Static checks/exact dedup/lexical search only; remainder planned |
| V2 | Durable runtime, parallel agent dispatch, worktrees, PR/CI synchronization, distributed recovery | Planned |
| V3 | Jira, conflict-aware bidirectional sync, Obsidian Bases/Canvas, change impact analysis | Planned |
| V4 | More tracker/harness adapters, governance, observability, production hardening | Planned |

## Next acceptance work

Validate actual Skills CLI installation and a harness compatibility matrix; run a controlled
live GitHub create/repeat/timeout scenario in a disposable repository with explicit authority.
Then define executable provider/consumer contracts and a structured evaluation corpus for
independence, decomposition quality and unintended side effects before expanding automation.

## Future independent boundaries

After freezing adapter interfaces, Projects and Jira adapters can own separate modules and
fake contract fixtures. Documentation/knowledge retrieval can own separate paths. Runtime
work must not be claimed independent of an unfinished shared contract or state store.
Consolidate inseparable changes rather than inventing empty dependency lists.

## Product guardrails

Do not add empty runtime packages, claim every provider is supported, or advertise an
end-to-end autonomous production workflow before corresponding live tests exist. Preserve
planning-only and offline modes throughout. Keep code execution, ticket creation, protected
branch merging and production deployment as separate capabilities and grants.
