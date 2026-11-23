# Contributing to MBUFlow

Read AGENTS.md, docs/PRD.md and docs/ARCHITECTURE.md. Keep the skill distribution self-contained.
Use Python 3.11+ and install `skills/mbu-flow/scripts/requirements.txt` in a virtual environment.
Run `python -m unittest discover -s tests -v` and `python -m compileall -q skills/mbu-flow/scripts tests`.

Add regression cases for safety boundaries and unknown remote outcomes. Tests must use
fakes/temp directories, never live credentials. Separate mocked, local and live evidence.
Changes to public schemas need reviewed migration notes and capability documentation.
Use Conventional Commits; submit a reviewable PR with scope, actual commands/results,
risks and rollback. Do not claim pending roadmap items are implemented.
