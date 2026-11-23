#!/usr/bin/env python3
"""MBUFlow's optional local helper; not a background multi-agent runtime."""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Install helper dependencies: python -m pip install -r <skill>/scripts/requirements.txt")

from core import FlowError, load_yaml, repo_name, safe_path, ticket_payloads, validate_plan
from ticketing import GitHubClient, apply_tickets, reconcile

ASSETS = Path(__file__).resolve().parent.parent / "assets"
PROFILES = {
    "minimal": ["INDEX", "PRD", "WORK_PLAN"],
    "backend": ["INDEX", "PRD", "TECHNICAL_DESIGN", "API_CONTRACTS", "WORK_PLAN", "TEST_STRATEGY", "INTEGRATION_PLAN"],
    "frontend": ["INDEX", "PRD", "UX_DESIGN", "UI_DESIGN", "DESIGN_SYSTEM", "API_CONTRACTS", "WORK_PLAN", "TEST_STRATEGY", "INTEGRATION_PLAN"],
    "full": ["INDEX", "VISION", "PRD", "USER_STORIES", "UX_DESIGN", "UI_DESIGN", "DESIGN_SYSTEM", "ARCHITECTURE", "TECHNICAL_DESIGN", "API_CONTRACTS", "DATA_MODEL", "SECURITY_DESIGN", "WORK_PLAN", "TEST_STRATEGY", "INTEGRATION_PLAN", "DEPLOYMENT", "RUNBOOK", "LEARNINGS"],
}


def scaffold(root: Path, profile: str, repository: str | None) -> dict:
    root.mkdir(parents=True, exist_ok=True)
    policy = load_yaml(ASSETS / "policy.example.yaml")
    if repository:
        policy["scope"]["repositories"] = [repo_name(repository)]
    templates = json.loads((ASSETS / "templates.json").read_text(encoding="utf-8"))
    files = {".mbu-flow/policy.yaml": yaml.safe_dump(policy, sort_keys=False),
             ".mbu-flow/.gitignore": "local/\n",
             ".mbu-flow/plan.yaml": yaml.safe_dump({"schema_version": 1, "project_id": "replace-project", "intent_id": "replace-intent",
                 "repository": repository or "owner/repository", "bolt_id": "B001",
                 "contract": {"id": "replace-contract-v1", "path": "docs/design/API_CONTRACTS.md", "sha256": "REPLACE_WITH_REAL_SHA256"},
                 "units": []}, sort_keys=False)}
    for key in PROFILES[profile]:
        item = templates[key]
        files[item["path"]] = (ASSETS / "templates" / f"{key}.md").read_text(encoding="utf-8")
    # Preflight all paths before writing. Reuse existing docs, never overwrite them.
    paths = {name: safe_path(root, name) for name in files}
    result = {"created": [], "preserved": [], "status": "draft; fill documents and freeze contracts before validation"}
    for name, destination in paths.items():
        if destination.exists():
            result["preserved"].append(name)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8") as handle:
            handle.write(files[name])
        result["created"].append(name)
    return result


def search_notes(root: Path, query: str, limit: int) -> list[dict]:
    words = query.casefold().split()
    results = []
    if not words:
        raise FlowError("Search query must not be empty")
    docs = safe_path(root, "docs")
    for file in docs.rglob("*.md"):
        rel = file.relative_to(root).as_posix()
        try:
            safe_path(root, rel, file=True)
        except FlowError:
            continue
        if file.stat().st_size > 128_000 or any(p.startswith(".") for p in file.relative_to(docs).parts):
            continue
        body = file.read_text(encoding="utf-8")
        score = sum((body.casefold().count(word) + 3 * rel.casefold().count(word)) for word in words)
        if score:
            lines = [line for line in body.splitlines() if any(w in line.casefold() for w in words)]
            results.append({"path": rel, "score": score, "excerpt": "\n".join(lines)[:600]})
    return sorted(results, key=lambda item: (-item["score"], item["path"]))[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="MBUFlow: Mob, Bolt & Unit workflow helpers (alpha)")
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Scaffold draft docs without overwriting existing files")
    init.add_argument("--root", type=Path, default=Path.cwd())
    init.add_argument("--profile", choices=PROFILES, default="backend")
    init.add_argument("--repository")
    search = commands.add_parser("search", help="Local lexical Markdown retrieval; no embeddings or network")
    search.add_argument("--root", type=Path, default=Path.cwd())
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, choices=range(1, 21), default=5)
    for command in ("validate", "tickets"):
        sub = commands.add_parser(command)
        sub.add_argument("--root", type=Path, default=Path.cwd())
        sub.add_argument("--plan", default=".mbu-flow/plan.yaml")
        sub.add_argument("--policy", default=".mbu-flow/policy.yaml")
        if command == "tickets":
            mode = sub.add_mutually_exclusive_group()
            mode.add_argument("--check", action="store_true", help="Read GitHub and reconcile; no remote writes")
            mode.add_argument("--apply", action="store_true", help="Create missing tickets under approved policy")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        if args.command == "init":
            output = scaffold(root, args.profile, args.repository)
        elif args.command == "search":
            output = search_notes(root, args.query, args.limit)
        else:
            plan = load_yaml(safe_path(root, args.plan, file=True))
            policy = load_yaml(safe_path(root, args.policy, file=True))
            report = validate_plan(plan, policy, root)
            if args.command == "validate":
                output = report
            elif not args.apply and not args.check:
                output = {"mode": "offline-preview", "network_used": False, "tickets": ticket_payloads(plan)}
            else:
                token = os.environ.get("MBUFLOW_GITHUB_TOKEN", "")
                if args.apply and not token:
                    raise FlowError("Set MBUFLOW_GITHUB_TOKEN through your trusted secret manager; do not put it in files")
                client = GitHubClient(token)
                output = (apply_tickets(plan, policy, root, client) if args.apply
                          else reconcile(ticket_payloads(plan), client.list_issues(plan["repository"])))
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 0
    except (FlowError, OSError, UnicodeError, sqlite3.Error) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
