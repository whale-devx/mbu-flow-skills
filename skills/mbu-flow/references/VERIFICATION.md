# Verification and delivery gates

Before ticket creation: review requirement coverage, exact repository allowlist, contract
baseline, independence rationale, ownership and required test doubles. Readiness is not proof.

Before accepting a unit: run its actual independent build, unit and contract tests. Capture
command, environment, commit, exit code and useful output. Inspect changed paths against
ownership. The alpha helper records test commands but deliberately does not execute them.

Before accepting a Bolt: integrate real implementations and run contract, integration/e2e,
CI and risk-appropriate security/performance checks. Mocks passing independently is insufficient.
Keep PRs reviewable and do not merge protected branches or deploy without separate authorization.

When a test fails, report the failure, bounded remediation and affected unit. Do not invent a
pass, modify acceptance criteria merely to pass, or change a frozen contract behind other agents.
A stopped unit must not erase already verified work from other units.

Provider support has separate dimensions: skill discovery, context loading, file access,
tool permissions, subagents, worktree isolation and execution recovery. Record what was tested
per harness. Plain Markdown portability is not proof of full autonomous provider compatibility.
