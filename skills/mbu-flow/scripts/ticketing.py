"""Create-only GitHub adapter with conservative reconciliation and local journaling."""
from __future__ import annotations

import json
import os
import sqlite3
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core import FlowError, fingerprint, repo_name, safe_path, ticket_payloads, validate_plan


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise FlowError("API redirects are refused; verify the repository's canonical name")


class GitHubClient:
    def __init__(self, token: str = "", *, opener: Any = None):
        self.token = token
        self.opener = opener or urllib.request.build_opener(NoRedirect())
        self.last_write = 0.0

    def request(self, method: str, repository: str, suffix: str, payload: dict | None = None) -> Any:
        repo = repo_name(repository)
        if method not in {"GET", "POST"}:
            raise FlowError("Only list and create operations are supported")
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10",
                   "User-Agent": "MBUFlow/0.1.0-alpha.1"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = None if payload is None else json.dumps(payload).encode()
        if data is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues{suffix}",
                                         data=data, headers=headers, method=method)
        if method == "POST":
            time.sleep(max(0, 1.0 - (time.monotonic() - self.last_write)))
            self.last_write = time.monotonic()
        try:
            with self.opener.open(request, timeout=30) as response:
                raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    raise FlowError("API response exceeds the size limit")
                return json.loads(raw)
        except urllib.error.HTTPError as exc:
            raise FlowError(f"GitHub HTTP {exc.code}; inspect permissions/rate limits. No automatic write retry.") from exc
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise FlowError("GitHub response unavailable/invalid. Reconcile before retrying; no write was retried.") from exc

    def list_issues(self, repository: str) -> list[dict]:
        found = []
        for page in range(1, 101):
            batch = self.request("GET", repository, f"?state=all&per_page=100&page={page}&sort=created&direction=asc")
            if not isinstance(batch, list):
                raise FlowError("Unexpected GitHub issue listing")
            for item in batch:
                if not isinstance(item, dict):
                    raise FlowError("Invalid item in GitHub listing")
                if "pull_request" not in item:
                    if (type(item.get("number")) is not int or item["number"] < 1
                            or not isinstance(item.get("title"), str)
                            or not isinstance(item.get("body") or "", str)
                            or item.get("state") not in {"open", "closed"}):
                        raise FlowError("Invalid issue fields in GitHub listing")
                    found.append(item)
            if len(batch) < 100:
                return found
        raise FlowError("Issue scan limit reached; refusing an incomplete duplicate check")

    def create_issue(self, repository: str, payload: dict) -> dict:
        if not self.token:
            raise FlowError("MBUFLOW_GITHUB_TOKEN is required for live creation")
        return self.request("POST", repository, "", payload)


def reconcile(desired: list[dict], existing: list[dict]) -> list[dict]:
    actions = []
    for item in desired:
        matches = [issue for issue in existing if item["marker"] in (issue.get("body") or "").splitlines()]
        if len(matches) > 1:
            raise FlowError("Duplicate identity markers found; resolve manually before writing")
        if matches:
            issue = matches[0]
            if issue.get("title") != item["payload"]["title"] or (issue.get("body") or "") != item["payload"]["body"]:
                raise FlowError("Existing ticket differs from the plan; review instead of overwriting human edits")
            if type(issue.get("number")) is not int or issue["number"] < 1:
                raise FlowError("Existing issue is missing a valid number")
            actions.append({**item, "action": "reuse", "number": issue["number"], "state": issue.get("state")})
        else:
            title = " ".join(item["payload"]["title"].split()).casefold()
            if any(" ".join(str(i.get("title", "")).split()).casefold() == title for i in existing):
                raise FlowError("Same-title ticket without the expected marker; ambiguous match requires review")
            actions.append({**item, "action": "create"})
    return actions


@contextmanager
def journal(root: Path):
    directory = safe_path(root, ".mbu-flow/local")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock = safe_path(root, ".mbu-flow/local/tickets.lock")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise FlowError("Ticket writer is locked. After a crash, verify no writer is running before removing tickets.lock.") from exc
    connection = None
    try:
        with os.fdopen(descriptor, "w") as handle:
            handle.write(str(os.getpid()))
        db = safe_path(root, ".mbu-flow/local/tickets.sqlite3")
        for suffix in ("-journal", "-wal", "-shm"):
            safe_path(root, f".mbu-flow/local/tickets.sqlite3{suffix}")
        connection = sqlite3.connect(db, isolation_level=None)
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("CREATE TABLE IF NOT EXISTS operations (key TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status TEXT NOT NULL, number INTEGER, intent TEXT NOT NULL)")
        connection.execute("CREATE TABLE IF NOT EXISTS audit (at TEXT NOT NULL, key TEXT NOT NULL, event TEXT NOT NULL)")
        yield connection
    finally:
        if connection is not None:
            connection.close()
        lock.unlink(missing_ok=True)


def audit(connection: sqlite3.Connection, key: str, event: str) -> None:
    connection.execute("INSERT INTO audit VALUES (?, ?, ?)", (datetime.now(timezone.utc).isoformat(), key, event))


def apply_tickets(plan: dict, policy: dict, root: Path, client: Any) -> list[dict]:
    validate_plan(plan, policy, root)
    if not policy["autonomy"]["enabled"]:
        raise FlowError("Autonomous writes are disabled; obtain an operator-approved policy")
    repository = repo_name(plan["repository"])
    if repository not in {repo_name(r) for r in policy["scope"]["repositories"]}:
        raise FlowError("Repository is not in the approved allowlist")
    desired = ticket_payloads(plan)
    intent = fingerprint([repository, plan["project_id"], plan["intent_id"]])
    results = []
    with journal(root) as connection:
        actions = reconcile(desired, client.list_issues(repository))
        known = {row[0] for row in connection.execute("SELECT key FROM operations WHERE intent = ?", (intent,))}
        if len(known | {item["key"] for item in desired}) > policy["limits"]["max_tickets_per_intent"]:
            raise FlowError("Cumulative local intent ticket quota exceeded")
        # Validate ALL local/remote identities before the first remote write.
        for action in actions:
            row = connection.execute("SELECT fingerprint, status FROM operations WHERE key = ?", (action["key"],)).fetchone()
            if row and row[0] != action["fingerprint"]:
                raise FlowError("Intent identity changed content; review or use a new intent revision")
            if row and action["action"] == "create":
                raise FlowError("A previous operation is missing remotely or has uncertain outcome; manual reconciliation required")
        for action in actions:
            key = action["key"]
            if action["action"] == "reuse":
                number = action["number"]
                connection.execute("INSERT OR REPLACE INTO operations VALUES (?, ?, 'confirmed', ?, ?)", (key, action["fingerprint"], number, intent))
                audit(connection, key, "reused")
            else:
                # Persist BEFORE sending POST. An unknown outcome must never be blindly retried.
                connection.execute("INSERT INTO operations VALUES (?, ?, 'pending', NULL, ?)", (key, action["fingerprint"], intent))
                audit(connection, key, "create_requested")
                try:
                    created = client.create_issue(repository, action["payload"])
                    number = created.get("number") if isinstance(created, dict) else None
                    if type(number) is not int or number < 1:
                        raise FlowError("Create response has no valid issue number; outcome is uncertain")
                except Exception:
                    audit(connection, key, "outcome_uncertain")
                    raise
                connection.execute("UPDATE operations SET status = 'confirmed', number = ? WHERE key = ?", (number, key))
                audit(connection, key, "created")
            results.append({"key": key, "action": action["action"], "number": number,
                            "url": f"https://github.com/{repository}/issues/{number}"})
    return results
