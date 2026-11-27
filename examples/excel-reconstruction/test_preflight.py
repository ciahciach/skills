import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


EXAMPLE = Path(__file__).resolve().parent


class ReconstructionPreflightTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.example = Path(temp.name) / "example"
        shutil.copytree(EXAMPLE, self.example, ignore=shutil.ignore_patterns("__pycache__"))

    def preflight(self, *args):
        return subprocess.run(
            [sys.executable, self.example / "preflight.py", *args],
            capture_output=True, text=True, check=False,
        )

    def test_complete_example_is_ready_only_for_source_inspection(self):
        result = self.preflight()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["READY: inputs only; desktop NOT_RUN"])

    def test_missing_or_empty_required_source_blocks_reconstruction(self):
        source = self.example / "Desk.vba"
        source.unlink()
        for state in ("missing", "empty"):
            with self.subTest(state=state):
                if state == "empty":
                    source.touch()
                result = self.preflight()
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [
                    "BLOCKED: missing, unreadable or empty source Desk.vba; desktop NOT_RUN",
                ])

    def test_manifest_cannot_waive_required_versioned_sources(self):
        manifest = '{"sources": ["README.md"], "companions": []}'
        (self.example / "inputs.json").write_text(manifest, encoding="utf-8")
        (self.example / "Desk.vba").unlink()
        result = self.preflight()
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "BLOCKED: missing, unreadable or empty source Desk.vba; desktop NOT_RUN",
        ])

    def test_device_names_cannot_stand_in_for_required_companion_files(self):
        store = self.example.parent / "companions"
        (store / "v2").mkdir(parents=True)
        manifest_path = self.example / "inputs.json"
        for name, version in (("NUL", "v2"), ("NUL.txt", "v2"), ("synthetic.bin", "NUL")):
            with self.subTest(name=name, version=version):
                manifest_path.write_text(json.dumps({"companions": [{
                    "name": name,
                    "version": version,
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "obtain": "Use only the local test directory.",
                }]}), encoding="utf-8")
                result = self.preflight("--companions", store)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [
                    "BLOCKED: invalid companion pin in inputs.json; desktop NOT_RUN",
                ])

    def test_required_external_companion_must_match_pinned_version_and_sha256(self):
        manifest_path = self.example / "inputs.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["companions"] = [{
            "name": "synthetic.bin",
            "version": "v2",
            "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            "obtain": "Use local synthetic bytes from the test.",
        }]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        store = self.example.parent / "companions"
        old_version = store / "v1"
        old_version.mkdir(parents=True)
        (old_version / "synthetic.bin").write_bytes(b"abc")

        result = self.preflight("--companions", store)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "BLOCKED: missing or unreadable companion synthetic.bin@v2; desktop NOT_RUN",
        ])

        pinned = store / "v2" / "synthetic.bin"
        pinned.parent.mkdir()
        pinned.write_bytes(b"wrong")
        result = self.preflight("--companions", store)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "BLOCKED: SHA-256 mismatch for companion synthetic.bin@v2; desktop NOT_RUN",
        ])

        pinned.write_bytes(b"abc")
        result = self.preflight("--companions", store)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ["READY: inputs only; desktop NOT_RUN"])

        for key in ("name", "version"):
            with self.subTest(key=key):
                companion = manifest["companions"][0]
                original = companion[key]
                companion[key] += "."
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                companion[key] = original
                result = self.preflight("--companions", store)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout.splitlines(), [
                    "BLOCKED: invalid companion pin in inputs.json; desktop NOT_RUN",
                ])
