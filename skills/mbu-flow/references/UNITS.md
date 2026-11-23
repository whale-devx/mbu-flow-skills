# Independent Units of Work

The non-negotiable goal is **no cross-unit implementation prerequisites** within the
parallel plan. Runtime component calls, shared read-only contracts and final integration
can still exist. Do not claim that architectural coupling has disappeared.

Each unit needs an objective, requirements, scope/exclusions, owned paths, baseline contract,
acceptance criteria, independently available test doubles and verification commands.
A unit can have multiple tickets. Task ordering inside that unit is allowed.

Use literal paths (`src/auth/`, `tests/auth/`, `docs/auth.md`), not glob expressions.
Ownership is conservatively case-insensitive: a directory conflicts with all descendants.
Avoid concurrent edits to manifests, lockfiles, shared route registries, generated APIs,
DB migrations, design tokens and global configuration. Freeze these, pre-establish extension
points, or combine inseparable work; separate worktrees do not eliminate semantic conflicts.

The validator checks declared dependencies, file existence, path overlap/scope and contract
hashes. It does NOT prove import independence, compilation, runtime safety or test validity.
Actually run each unit's independent build/tests and then integrated contract/e2e checks.

If a dependency cannot be removed honestly, replan or merge the units. Do not silently turn
it into a later-Bolt prerequisite and still advertise a dependency-free plan. Record any
requested sequential exception for owner review outside this alpha's executable schema.
