"""Offline regression tests. No test contacts GitHub or creates live issues."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/mbu-flow"
sys.path.insert(0, str(SKILL / "scripts"))

import core
import mbu
import ticketing
import yaml


def fixture(root: Path, count: int = 2) -> tuple[dict, dict]:
    policy = core.load_yaml(SKILL / "assets/policy.example.yaml")
    policy["autonomy"]["enabled"] = True
    policy["scope"]["repositories"] = ["example/project"]
    contract = root / "contracts/public.md"
    contract.parent.mkdir(parents=True)
    contract.write_text("# Frozen record v1\nInput: {id: string, value: string}.\n", encoding="utf-8")
    units = []
    for index in range(1, count + 1):
        name = f"part{index}"
        spec = root / f"docs/units/U{index:03}.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text(f"# U{index:03}\nUse the frozen record contract and a local test double.\n", encoding="utf-8")
        double = root / f"tests/{name}/fixture.json"
        double.parent.mkdir(parents=True, exist_ok=True)
        double.write_text('{"id":"sample","value":"hello"}\n', encoding="utf-8")
        units.append({"id": f"U{index:03}", "title": f"Independent {name}",
            "objective": f"Build and verify {name} against the frozen record, not another unfinished unit.",
            "status": "ready", "depends_on": [], "owned_paths": [f"src/{name}/", f"tests/{name}/"],
            "spec": spec.relative_to(root).as_posix(), "requirements": [f"REQ-{index:03}"],
            "acceptance_criteria": ["Valid records are accepted", "Invalid records produce a structured error"],
            "test_commands": [f"python -m unittest discover -s tests/{name}"],
            "test_double": double.relative_to(root).as_posix(),
            "tickets": [{"key": "implementation", "title": f"Implement {name}"}]})
    plan = {"schema_version": 1, "project_id": "demo", "intent_id": "record-feature-v1",
            "repository": "example/project", "bolt_id": "B001",
            "contract": {"id": "record-v1", "path": "contracts/public.md", "sha256": core.digest(contract.read_bytes())},
            "units": units}
    return plan, policy


class FakeGitHub:
    def __init__(self):
        self.issues = []
        self.creates = 0
        self.fail = False
        self.persist_then_fail = False

    def list_issues(self, repository):
        return copy.deepcopy(self.issues)

    def create_issue(self, repository, payload):
        self.creates += 1
        result = {**copy.deepcopy(payload), "number": self.creates, "state": "open"}
        if self.persist_then_fail:
            self.issues.append(result)
            self.persist_then_fail = False
            raise TimeoutError("connection lost after server accepted write")
        if self.fail:
            raise TimeoutError("unknown outcome")
        self.issues.append(result)
        return result


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.plan, self.policy = fixture(self.root)
        self.client = FakeGitHub()

    def validate(self):
        return core.validate_plan(self.plan, self.policy, self.root)

    def apply(self):
        return ticketing.apply_tickets(self.plan, self.policy, self.root, self.client)

    def test_valid_independent_plan(self):
        report = self.validate()
        self.assertEqual(report["suggested_batches"], [["U001", "U002"]])
        self.assertEqual(report["tickets"], 2)

    def test_parallel_limit(self):
        self.policy["limits"]["max_parallel_units"] = 1
        self.assertEqual(self.validate()["suggested_batches"], [["U001"], ["U002"]])

    def test_reject_cross_unit_dependency(self):
        self.plan["units"][1]["depends_on"] = ["U001"]
        with self.assertRaisesRegex(core.FlowError, "replan or merge"):
            self.validate()

    def test_reject_unready(self):
        self.plan["units"][0]["status"] = "draft"
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_reject_duplicate_unit_id(self):
        self.plan["units"][1]["id"] = "U001"
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_reject_parent_path_overlap(self):
        self.plan["units"][0]["owned_paths"] = ["src/"]
        with self.assertRaisesRegex(core.FlowError, "Ownership conflict"):
            self.validate()

    def test_reject_case_insensitive_overlap(self):
        self.plan["units"][1]["owned_paths"] = ["src/PART1/"]
        with self.assertRaisesRegex(core.FlowError, "Ownership conflict"):
            self.validate()

    def test_reject_path_traversal_absolute_glob_and_windows(self):
        for bad in ("../secret", "/etc/passwd", "src/../other", "src//other", "src/**", "C:\\secret", ".", "src/./a"):
            with self.subTest(path=bad), self.assertRaises(core.FlowError):
                core.safe_path(self.root, bad)

    def test_reject_symlink(self):
        link = self.root / "src/link"
        link.parent.mkdir()
        link.symlink_to(self.root / "tests", target_is_directory=True)
        self.plan["units"][0]["owned_paths"] = ["src/link/"]
        with self.assertRaisesRegex(core.FlowError, "Symlink"):
            self.validate()

    def test_protected_contract(self):
        self.policy["scope"]["allowed_paths"].append("contracts/")
        self.plan["units"][0]["owned_paths"] = ["contracts/"]
        with self.assertRaisesRegex(core.FlowError, "protected"):
            self.validate()

    def test_protected_git_even_when_allowlisted(self):
        self.policy["scope"]["allowed_paths"].append(".git/")
        self.plan["units"][0]["owned_paths"] = [".git/"]
        with self.assertRaisesRegex(core.FlowError, "protected"):
            self.validate()

    def test_contract_drift(self):
        (self.root / "contracts/public.md").write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(core.FlowError, "baseline changed"):
            self.validate()

    def test_missing_test_double(self):
        (self.root / self.plan["units"][0]["test_double"]).unlink()
        with self.assertRaisesRegex(core.FlowError, "missing"):
            self.validate()

    def test_missing_acceptance(self):
        self.plan["units"][0]["acceptance_criteria"] = []
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_unknown_policy_fields_fail_closed(self):
        self.policy["skip_checks"] = True
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_unknown_plan_fields_fail_closed(self):
        self.plan["units"][0]["ignore_dependency"] = True
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_reject_boolean_as_integer(self):
        self.policy["limits"]["max_units"] = True
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_reject_unsupported_adapter(self):
        self.policy["ticketing"]["provider"] = "jira"
        with self.assertRaisesRegex(core.FlowError, "only implements GitHub"):
            self.validate()

    def test_yaml_duplicates_aliases_and_unsafe_tags(self):
        file = self.root / "bad.yaml"
        for value in ("x: 1\nx: 2", "x: &ref 1\ny: *ref", "x: !!python/object:evil {}", "- not-a-mapping"):
            file.write_text(value, encoding="utf-8")
            with self.subTest(value=value), self.assertRaises(core.FlowError):
                core.load_yaml(file)

    def test_policy_disabled_blocks_all_writes(self):
        self.policy["autonomy"]["enabled"] = False
        with self.assertRaisesRegex(core.FlowError, "disabled"):
            self.apply()
        self.assertEqual(self.client.creates, 0)

    def test_allowlist_blocks_wrong_repository(self):
        self.policy["scope"]["repositories"] = ["other/project"]
        with self.assertRaisesRegex(core.FlowError, "allowlist"):
            self.apply()
        self.assertEqual(self.client.creates, 0)

    def test_ticket_quota(self):
        self.policy["limits"]["max_tickets_per_intent"] = 1
        with self.assertRaisesRegex(core.FlowError, "quota"):
            self.apply()
        self.assertEqual(self.client.creates, 0)

    def test_multiple_tickets_per_unit(self):
        self.plan["units"][0]["tickets"].append({"key": "verification", "title": "Verify part1"})
        self.assertEqual(len(self.apply()), 3)

    def test_oversized_ticket_body_is_rejected_before_writes(self):
        self.plan["units"][0]["acceptance_criteria"] = [str(i) + "x" * 9000 for i in range(8)]
        with self.assertRaisesRegex(core.FlowError, "60000"):
            self.apply()
        self.assertEqual(self.client.creates, 0)

    def test_duplicate_ticket_key(self):
        self.plan["units"][0]["tickets"] *= 2
        with self.assertRaises(core.FlowError):
            self.validate()

    def test_duplicate_ticket_title(self):
        self.plan["units"][0]["tickets"].append({"key": "another", "title": "Implement part1"})
        with self.assertRaisesRegex(core.FlowError, "distinct"):
            self.apply()

    def test_repeat_is_idempotent(self):
        self.assertEqual([r["action"] for r in self.apply()], ["create", "create"])
        self.assertEqual([r["action"] for r in self.apply()], ["reuse", "reuse"])
        self.assertEqual(self.client.creates, 2)

    def test_closed_issue_is_reused_not_reopened(self):
        self.apply()
        self.client.issues[0]["state"] = "closed"
        self.apply()
        self.assertEqual(self.client.issues[0]["state"], "closed")
        self.assertEqual(self.client.creates, 2)

    def test_title_change_does_not_create_another_identity(self):
        before = core.ticket_payloads(self.plan)[0]["key"]
        self.apply()
        self.plan["units"][0]["tickets"][0]["title"] = "A revised title"
        self.assertEqual(before, core.ticket_payloads(self.plan)[0]["key"])
        with self.assertRaisesRegex(core.FlowError, "differs"):
            self.apply()
        self.assertEqual(self.client.creates, 2)

    def test_human_edit_blocks_entire_batch_before_writes(self):
        item = core.ticket_payloads(self.plan)[1]["payload"]
        self.client.issues = [{**item, "body": item["body"] + "\nHuman note", "number": 10, "state": "open"}]
        with self.assertRaisesRegex(core.FlowError, "human edits"):
            self.apply()
        self.assertEqual(self.client.creates, 0)

    def test_ambiguous_title_blocks_writes(self):
        self.client.issues = [{"number": 10, "title": "[U001] Implement part1", "body": "Unmanaged", "state": "open"}]
        with self.assertRaisesRegex(core.FlowError, "ambiguous"):
            self.apply()
        self.assertEqual(self.client.creates, 0)

    def test_duplicate_remote_marker_blocks_writes(self):
        item = core.ticket_payloads(self.plan)[0]["payload"]
        self.client.issues = [{**item, "number": 10}, {**item, "number": 11}]
        with self.assertRaisesRegex(core.FlowError, "Duplicate identity"):
            self.apply()

    def test_uncertain_write_is_never_blindly_retried(self):
        self.client.fail = True
        with self.assertRaises(TimeoutError):
            self.apply()
        self.client.fail = False
        with self.assertRaisesRegex(core.FlowError, "uncertain"):
            self.apply()
        self.assertEqual(self.client.creates, 1)

    def test_lost_response_recovers_from_remote_marker(self):
        self.client.persist_then_fail = True
        with self.assertRaises(TimeoutError):
            self.apply()
        result = self.apply()
        self.assertEqual([r["action"] for r in result], ["reuse", "create"])
        self.assertEqual(self.client.creates, 2)

    def test_lock_prevents_second_local_writer(self):
        with ticketing.journal(self.root):
            with self.assertRaisesRegex(core.FlowError, "locked"):
                self.apply()
            self.assertTrue((self.root / ".mbu-flow/local/tickets.lock").exists())
        self.assertFalse((self.root / ".mbu-flow/local/tickets.lock").exists())

    def test_audit_records_actions_without_payloads(self):
        self.apply()
        with contextlib.closing(sqlite3.connect(self.root / ".mbu-flow/local/tickets.sqlite3")) as db:
            events = [row[0] for row in db.execute("SELECT event FROM audit")]
        self.assertEqual(events, ["create_requested", "created", "create_requested", "created"])

    def test_cumulative_local_quota_across_plan_revisions(self):
        second = self.plan["units"][1]
        self.plan["units"] = self.plan["units"][:1]
        self.policy["limits"]["max_tickets_per_intent"] = 1
        self.apply()
        self.plan["units"] = [second]
        with self.assertRaisesRegex(core.FlowError, "Cumulative"):
            self.apply()
        self.assertEqual(self.client.creates, 1)

    def test_cli_preview_uses_no_network(self):
        (self.root / ".mbu-flow").mkdir()
        (self.root / ".mbu-flow/plan.yaml").write_text(yaml.safe_dump(self.plan), encoding="utf-8")
        (self.root / ".mbu-flow/policy.yaml").write_text(yaml.safe_dump(self.policy), encoding="utf-8")
        with patch("mbu.GitHubClient", side_effect=AssertionError("network must not be used")), contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(mbu.main(["tickets", "--root", str(self.root)]), 0)
        self.assertFalse(json.loads(output.getvalue())["network_used"])

    def test_scaffold_preserves_existing_documents(self):
        doc = self.root / "docs/product/PRD.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("Human specification", encoding="utf-8")
        result = mbu.scaffold(self.root, "backend", "example/project")
        self.assertIn("docs/product/PRD.md", result["preserved"])
        self.assertEqual(doc.read_text(), "Human specification")
        self.assertFalse(core.load_yaml(self.root / ".mbu-flow/policy.yaml")["autonomy"]["enabled"])

    def test_scaffold_profiles_are_adaptive(self):
        with tempfile.TemporaryDirectory() as directory:
            result = mbu.scaffold(Path(directory), "minimal", None)
            self.assertNotIn("docs/design/UI_DESIGN.md", result["created"])
            self.assertIn("docs/product/PRD.md", result["created"])

    def test_search_returns_local_evidence(self):
        result = mbu.search_notes(self.root, "frozen record", 1)
        self.assertEqual(len(result), 1)
        self.assertIn("frozen record", result[0]["excerpt"])


class TransportTests(unittest.TestCase):
    def test_pagination_includes_closed_and_skips_prs(self):
        client = ticketing.GitHubClient()
        first = [{"number": i + 1, "title": "x", "body": "", "state": "closed"} for i in range(99)]
        first.append({"pull_request": {}})
        with patch.object(client, "request", side_effect=[first, []]) as request:
            result = client.list_issues("example/project")
        self.assertEqual(len(result), 99)
        self.assertIn("state=all", request.call_args_list[0].args[2])
        self.assertIn("page=2", request.call_args_list[1].args[2])

    def test_incomplete_scan_fails_closed(self):
        client = ticketing.GitHubClient()
        with patch.object(client, "request", return_value=[{"pull_request": {}}] * 100):
            with self.assertRaisesRegex(core.FlowError, "incomplete"):
                client.list_issues("example/project")

    def test_unexpected_issue_fields(self):
        client = ticketing.GitHubClient()
        with patch.object(client, "request", return_value=[{"number": "wrong"}]):
            with self.assertRaises(core.FlowError):
                client.list_issues("example/project")

    def test_redirect_refused(self):
        with self.assertRaises(core.FlowError):
            ticketing.NoRedirect().redirect_request(None, None, 302, "moved", {}, "https://other.invalid")

    def test_missing_token_fails_before_post(self):
        client = ticketing.GitHubClient()
        with patch.object(client, "request") as request:
            with self.assertRaisesRegex(core.FlowError, "TOKEN"):
                client.create_issue("example/project", {"title": "x"})
            request.assert_not_called()

    def test_http_error_is_sanitized_and_not_retried(self):
        from unittest.mock import Mock
        opener = Mock()
        opener.open.side_effect = urllib.error.HTTPError("https://api.github.com", 403, "sensitive detail", {}, None)
        client = ticketing.GitHubClient("test-secret", opener=opener)
        with self.assertRaises(core.FlowError) as error:
            client.request("POST", "example/project", "", {"title": "x"})
        self.assertNotIn("sensitive", str(error.exception))
        self.assertNotIn("test-secret", str(error.exception))
        self.assertEqual(opener.open.call_count, 1)


class DistributionTests(unittest.TestCase):
    def test_skill_metadata_and_local_references(self):
        import re
        contents = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        metadata = yaml.safe_load(contents.split("---", 2)[1])
        self.assertEqual(metadata["name"], "mbu-flow")
        self.assertLessEqual(len(metadata["description"]), 1024)
        self.assertLess(len(contents.splitlines()), 500)
        for target in re.findall(r"\]\((references/[^)]+)\)", contents):
            self.assertTrue((SKILL / target).is_file(), target)

    def test_every_template_exists_and_is_draft(self):
        manifest = json.loads((SKILL / "assets/templates.json").read_text())
        for name in manifest:
            content = (SKILL / "assets/templates" / f"{name}.md").read_text()
            self.assertIn("status: draft", content)
            self.assertGreater(len(content), 100)


if __name__ == "__main__":
    unittest.main()
