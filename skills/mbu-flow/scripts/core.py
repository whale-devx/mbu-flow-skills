"""MBUFlow plan validation. This checks declarations, not program independence."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import yaml


class FlowError(ValueError):
    """A fail-closed validation or workflow error safe to show to the operator."""


class StrictLoader(yaml.SafeLoader):
    """Safe YAML with duplicate keys rejected instead of silently overwritten."""


def _mapping(loader: StrictLoader, node: Any, deep: bool = False) -> dict:
    result = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str) or key in result:
            raise FlowError("YAML keys must be unique strings")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


StrictLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _mapping)


def load_yaml(path: Path) -> dict:
    if path.stat().st_size > 1_000_000:
        raise FlowError("YAML exceeds the 1 MB limit")
    text = path.read_text(encoding="utf-8")
    try:
        if any(isinstance(t, (yaml.tokens.AliasToken, yaml.tokens.AnchorToken))
               for t in yaml.scan(text)):
            raise FlowError("YAML anchors and aliases are not supported")
        data = yaml.load(text, Loader=StrictLoader)
    except yaml.YAMLError as exc:
        raise FlowError("Invalid YAML; use plain mappings and lists") from exc
    if not isinstance(data, dict):
        raise FlowError("YAML root must be a mapping")
    return data


def fields(value: Any, names: str, where: str) -> None:
    expected = set(names.split())
    if not isinstance(value, dict) or set(value) != expected:
        raise FlowError(f"{where}: expected exactly these fields: {', '.join(sorted(expected))}")


def text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 10_000:
        raise FlowError(f"{where}: expected non-empty text of at most 10000 characters")
    return value


def strings(value: Any, where: str, allow_empty: bool = False) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise FlowError(f"{where}: expected a {'possibly empty ' if allow_empty else 'non-empty '}list")
    for item in value:
        text(item, where)
    if len(set(value)) != len(value):
        raise FlowError(f"{where}: duplicate entries")
    return value


def repo_name(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9_.-]+", value):
        raise FlowError("Repository must have the form owner/repository")
    if value.split("/")[1] in {".", ".."}:
        raise FlowError("Invalid repository name")
    return value.lower()


def relative(value: Any) -> str:
    text(value, "path")
    clean = value.rstrip("/")
    if (not clean or value != value.strip() or any(c in value for c in "\\:*?\x00\n\r")
            or any(part in {"", ".", ".."} for part in clean.split("/"))):
        raise FlowError(f"Use literal repository-relative paths, not globs or traversal: {value!r}")
    return clean


def safe_path(root: Path, value: str, *, file: bool = False) -> Path:
    clean = relative(value)
    root = root.resolve()
    current = root
    for part in clean.split("/"):
        current = current / part
        if current.is_symlink():
            raise FlowError(f"Symlink paths are not allowed: {value}")
    if not current.resolve().is_relative_to(root):
        raise FlowError("Path escapes the project root")
    if file and not current.is_file():
        raise FlowError(f"Required file is missing: {value}")
    return current


def contains(parent: str, child: str) -> bool:
    parent, child = relative(parent).casefold(), relative(child).casefold()
    return child == parent or child.startswith(parent + "/")


def overlaps(a: str, b: str) -> bool:
    return contains(a, b) or contains(b, a)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fingerprint(data: Any) -> str:
    return digest(json.dumps(data, sort_keys=True, ensure_ascii=False).encode())


def validate_policy(policy: dict) -> None:
    fields(policy, "schema_version autonomy scope limits ticketing", "policy")
    if type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise FlowError("Unsupported policy schema_version")
    fields(policy["autonomy"], "enabled ticket_creation", "autonomy")
    if (type(policy["autonomy"]["enabled"]) is not bool
            or policy["autonomy"]["ticket_creation"] != "autonomous"):
        raise FlowError("Use an explicit boolean enabled and ticket_creation: autonomous")
    fields(policy["scope"], "repositories allowed_paths protected_paths", "scope")
    repos = strings(policy["scope"]["repositories"], "repositories", allow_empty=True)
    if len({repo_name(r) for r in repos}) != len(repos):
        raise FlowError("Duplicate repository grants")
    for key in ("allowed_paths", "protected_paths"):
        for path in strings(policy["scope"][key], key, allow_empty=key == "protected_paths"):
            relative(path)
    fields(policy["limits"], "max_units max_tickets_per_intent max_parallel_units", "limits")
    for key, value in policy["limits"].items():
        if type(value) is not int or not 1 <= value <= 100:
            raise FlowError(f"{key} must be an integer between 1 and 100")
    fields(policy["ticketing"], "provider", "ticketing")
    if policy["ticketing"]["provider"] != "github":
        raise FlowError("This alpha only implements GitHub Issues; other adapters are planned")


def validate_plan(plan: dict, policy: dict, root: Path) -> dict:
    validate_policy(policy)
    fields(plan, "schema_version project_id intent_id repository bolt_id contract units", "plan")
    if type(plan["schema_version"]) is not int or plan["schema_version"] != 1:
        raise FlowError("Unsupported plan schema_version")
    for key in ("project_id", "intent_id", "bolt_id"):
        if not isinstance(plan[key], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", plan[key]):
            raise FlowError(f"Invalid stable identifier: {key}")
    repo_name(plan["repository"])
    contract = plan["contract"]
    fields(contract, "id path sha256", "contract")
    text(contract["id"], "contract.id")
    contract_path = safe_path(root, contract["path"], file=True)
    if not isinstance(contract["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", contract["sha256"]):
        raise FlowError("Freeze the contract with a lowercase SHA-256 digest first")
    if digest(contract_path.read_bytes()) != contract["sha256"]:
        raise FlowError("Contract baseline changed; stop and replan affected units")
    units = plan["units"]
    if not isinstance(units, list) or not 1 <= len(units) <= policy["limits"]["max_units"]:
        raise FlowError("Plan needs at least one unit and must respect max_units")
    owned: list[tuple[str, str]] = []
    ids: set[str] = set()
    ticket_count = 0
    for unit in units:
        fields(unit, "id title objective status depends_on owned_paths spec requirements acceptance_criteria test_commands test_double tickets", "unit")
        uid = unit["id"]
        if not isinstance(uid, str) or not re.fullmatch(r"U[0-9]{3,}", uid) or uid in ids:
            raise FlowError("Unit IDs must be unique and use U001-style identifiers")
        ids.add(uid)
        for key in ("title", "objective"):
            text(unit[key], f"{uid}.{key}")
        if unit["status"] != "ready" or unit["depends_on"] != []:
            raise FlowError(f"{uid}: only ready, dependency-free units are eligible; replan or merge")
        safe_path(root, unit["spec"], file=True)
        safe_path(root, unit["test_double"], file=True)
        for key in ("requirements", "acceptance_criteria", "test_commands"):
            strings(unit[key], f"{uid}.{key}")
        for path in strings(unit["owned_paths"], f"{uid}.owned_paths"):
            safe_path(root, path)
            if not any(contains(p, path) for p in policy["scope"]["allowed_paths"]):
                raise FlowError(f"{uid}: path outside policy scope: {path}")
            protected = [".git/", ".mbu-flow/", "AGENTS.md", contract["path"], *policy["scope"]["protected_paths"]]
            if any(overlaps(path, p) for p in protected):
                raise FlowError(f"{uid}: protected/shared path ownership: {path}")
            for other_id, other_path in owned:
                if other_id != uid and overlaps(path, other_path):
                    raise FlowError(f"Ownership conflict: {uid} {path} overlaps {other_id} {other_path}")
            owned.append((uid, path))
        tickets = unit["tickets"]
        if not isinstance(tickets, list) or not tickets:
            raise FlowError(f"{uid}: provide at least one ticket")
        keys = set()
        for ticket in tickets:
            fields(ticket, "key title", f"{uid}.ticket")
            key = ticket["key"]
            if not isinstance(key, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", key) or key in keys:
                raise FlowError(f"{uid}: ticket keys must be unique stable lowercase slugs")
            keys.add(key)
            if len(text(ticket["title"], "ticket.title")) > 200:
                raise FlowError("Ticket titles must not exceed 200 characters")
            ticket_count += 1
    if ticket_count > policy["limits"]["max_tickets_per_intent"]:
        raise FlowError("Intent ticket quota exceeded")
    width = policy["limits"]["max_parallel_units"]
    return {"valid": True, "units": len(units), "tickets": ticket_count,
            "suggested_batches": [[u["id"] for u in units[i:i + width]] for i in range(0, len(units), width)],
            "warning": "Static declarations checked only. Contract, isolation and integration tests remain required."}


def ticket_payloads(plan: dict) -> list[dict]:
    result = []
    titles = set()
    for unit in plan["units"]:
        for ticket in unit["tickets"]:
            identity = [repo_name(plan["repository"]), plan["project_id"], plan["intent_id"], unit["id"], ticket["key"]]
            key = fingerprint(identity)
            marker = f"<!-- mbu-flow:{key} -->"
            body = "\n".join([
                marker, "# MBUFlow work item", "", unit["objective"], "",
                f"Unit: `{unit['id']}` | Bolt: `{plan['bolt_id']}` | Intent: `{plan['intent_id']}`",
                f"Spec (repository-relative): `{unit['spec']}`",
                f"Requirements: {', '.join(unit['requirements'])}",
                f"Contract: `{plan['contract']['id']}` / SHA-256 `{plan['contract']['sha256']}`", "",
                "## Owned paths", *[f"- `{p}`" for p in unit["owned_paths"]], "",
                "## Acceptance criteria", *[f"- [ ] {a}" for a in unit["acceptance_criteria"]], "",
                "## Verification commands (not executed by ticket creation)",
                *[f"- `{c}`" for c in unit["test_commands"]], "",
                f"Independent test double: `{unit['test_double']}`", "",
                "## Delivery gate", "Attach PR and real test evidence. Integration must pass before delivery.",
            ])
            if len(body.encode("utf-8")) > 60_000:
                raise FlowError("Ticket body exceeds the safe 60000-byte limit")
            title = f"[{unit['id']}] {ticket['title']}"
            normalized_title = " ".join(title.split()).casefold()
            if normalized_title in titles:
                raise FlowError("Ticket titles must be distinct within a plan")
            titles.add(normalized_title)
            payload = {"title": title, "body": body}
            result.append({"key": key, "marker": marker, "payload": payload, "fingerprint": fingerprint(payload)})
    return result
