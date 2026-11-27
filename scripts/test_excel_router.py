import json
from pathlib import Path
import subprocess
import sys
from typing import Any
import unittest


ROUTER = (Path(__file__).resolve().parents[1] / "skills" / "in-progress"
          / "excel-router" / "route.py")


class ExcelRouterTest(unittest.TestCase):
    def setUp(self):
        self.scope = {
            "operation": "update-test-formula", "profile": "simple", "class": "save",
            "effects": ["save-separate-copy"], "controls": ["independent-readback"],
            "environment": "synthetic-host-build-1", "boundary": "synthetic-simple-copy",
            "target_kind": "synthetic",
        }
        self.request: dict[str, Any] = {
            "scope": self.scope,
            "candidates": [
                {"interface": "test-cli", "version": "2", "methods": ["update"]},
                {"interface": "test-com", "version": "1", "methods": ["assign"]},
            ],
            "evidence": [],
        }

    def run_router(self):
        return subprocess.run(
            [sys.executable, "-B", "-X", "utf8", str(ROUTER)],
            input=json.dumps(self.request), capture_output=True, encoding="utf-8", timeout=10,
        )

    def route(self):
        result = self.run_router()
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_matching_evidence_beats_candidate_order(self):
        self.request["evidence"] = [{
            "scope": self.scope, "interface": "test-com", "version": "1",
            "method": "assign", "outcome": "verified", "reference": "synthetic-proof-1",
        }]
        self.assertEqual(self.route(), {
            "decision": "selected", "interface": "test-com", "version": "1",
            "method": "assign", "qualification": "synthetic-proof-1",
        })

    def test_stale_or_differently_scoped_evidence_does_not_authorize_routine_work(self):
        valid = {"scope": self.scope, "interface": "test-cli", "version": "2",
                 "method": "update", "outcome": "verified", "reference": "synthetic-proof"}
        mismatches = [{**valid, "version": "1"}]
        for key, value in {
            "operation": "read-test-formula", "profile": "application",
            "effects": [], "controls": [], "environment": "synthetic-host-build-2",
            "boundary": "user-workbook",
        }.items():
            mismatches.append({**valid, "scope": {**self.scope, key: value}})
        for row in mismatches:
            with self.subTest(row=row):
                self.request["evidence"] = [row]
                result = self.route()
                self.assertEqual(result["decision"], "blocked")
                self.assertEqual(result["reason"], "no-matching-evidence")

    def test_qualification_moves_to_next_interface_after_five_distinct_admissible_methods(self):
        cli, com = self.request["candidates"]
        cli["methods"] = ["excluded", "a", "a", "b", "c", "d", "e", "sixth"]
        self.request["evidence"] = [{
            "scope": self.scope, "interface": "test-cli", "version": "2",
            "method": "excluded", "outcome": "excluded", "reference": "synthetic-gap-1",
        }]
        self.start_trial()
        for method in ["a", "b", "c", "d", "e"]:
            result = self.route()
            self.assertEqual(result["excluded"], [{
                "interface": "test-cli", "version": "2", "method": "excluded",
                "reference": "synthetic-gap-1",
            }])
            self.assertEqual((result["decision"], result["interface"], result["method"]),
                             ("trial", "test-cli", method))
            self.record(result, "gap")
        result = self.route()
        self.assertEqual((result["decision"], result["interface"], result["method"]),
                         ("trial", com["interface"], "assign"))

    def test_first_verified_success_ends_qualification_not_routine_execution(self):
        self.start_trial()
        self.record(self.route(), "verified")
        self.assertEqual(self.route(), {
            "decision": "verified", "interface": "test-cli", "version": "2", "method": "update",
        })

    def test_exhaustion_reports_human_step_without_retry(self):
        self.start_trial()
        self.record(self.route(), "gap")
        self.record(self.route(), "unavailable")
        result = self.route()
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["reason"], "methods-exhausted")
        self.assertIn("test-com 1", result["human_step"])
        self.assertIn("assign", result["human_step"])

    def test_unknown_save_effect_blocks_other_methods_and_interfaces(self):
        self.start_trial()
        self.record(self.route(), "unresolved-effects")
        result = self.route()
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["reason"], "unresolved-effects")
        self.assertIn("inspect the synthetic copy", result["human_step"])

    def test_decision_only_can_name_candidate_but_cannot_start_trial(self):
        self.start_trial(authorization="decision-only")
        self.assertEqual(self.route(), {
            "decision": "candidate", "interface": "test-cli", "version": "2",
            "method": "update", "qualification": "NOT_VERIFIED",
        })

    def test_trial_authorization_never_allows_a_non_synthetic_target(self):
        self.scope["target_kind"] = "target"
        self.start_trial()
        self.assertEqual(self.route()["decision"], "blocked")

    def test_unknown_profile_requires_passive_profiling_before_save(self):
        self.scope["profile"] = "unknown"
        self.start_trial()
        self.assertEqual(self.route()["reason"], "unknown-profile")

    def test_incomplete_scope_cannot_match_equally_incomplete_evidence(self):
        self.scope.pop("controls")
        self.request["evidence"] = [{
            "scope": self.scope, "interface": "test-cli", "version": "2",
            "method": "update", "outcome": "verified", "reference": "synthetic-proof",
        }]
        result = self.run_router()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_accounted_for_save_with_inconclusive_check_can_move_on(self):
        self.start_trial()
        self.record(self.route(), "not-verified")
        self.assertEqual(self.route()["interface"], "test-com")

    def test_stricter_operation_limit_survives_interface_change(self):
        cli, com = self.request["candidates"]
        cli["methods"] = ["a", "b"]
        com["methods"] = ["c", "d"]
        self.start_trial(limit=3)
        for _ in range(3):
            self.record(self.route(), "gap")
        result = self.route()
        self.assertEqual(result["decision"], "blocked")
        self.assertEqual(result["reason"], "operation-limit")
        self.assertIn("independent-readback", result["human_step"])

    def test_qualification_requires_a_checkable_success_criterion(self):
        self.scope["controls"] = []
        self.start_trial()
        self.assertEqual(self.route()["reason"], "missing-checks")

    def test_empty_plan_names_the_missing_capability(self):
        self.request["candidates"] = []
        self.start_trial()
        result = self.route()
        self.assertEqual(result["reason"], "methods-exhausted")
        self.assertIn("update-test-formula", result["human_step"])
        self.assertIn("independent-readback", result["human_step"])

    def test_history_after_terminal_result_cannot_be_reported_as_success(self):
        self.start_trial()
        self.record(self.route(), "verified")
        self.record({"interface": "test-com", "version": "1", "method": "assign"}, "unresolved-effects")
        result = self.run_router()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_output_omits_raw_trial_observations_even_when_blocked(self):
        self.start_trial()
        self.record(self.route(), "unresolved-effects")
        observation = "C:/test/private.xlsx FAKE_CELL_VALUE FAKE_SECRET"
        self.request["trial"]["attempts"][0]["raw_output"] = observation
        result = self.run_router()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["reason"], "unresolved-effects")
        for raw_value in observation.split():
            self.assertNotIn(raw_value, result.stdout + result.stderr)

    def start_trial(self, authorization="execute", limit=None):
        self.request["trial"] = {"authorization": authorization, "attempts": [], "limit": limit}

    def record(self, decision, outcome):
        self.request["trial"]["attempts"].append({
            **{key: decision[key] for key in ("interface", "version", "method")},
            "outcome": outcome,
            **({"control": "independent-readback"} if outcome in ("gap", "not-verified") else {}),
        })


if __name__ == "__main__":
    unittest.main()
