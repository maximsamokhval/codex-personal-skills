import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "ucd-status"
TOOL = SKILL / "scripts" / "render_ucd.py"
SPEC = importlib.util.spec_from_file_location("render_ucd", TOOL)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


def fixture():
    return {
        "schema_version": "ucd-status/v1",
        "title": "Library",
        "language": "en",
        "snapshot": {
            "checked_at": "2026-01-01T12:00:00Z",
            "revision": "test-revision",
            "worktree": "clean",
            "tracker": "local fixture",
        },
        "labels": {key: key.replace("_", " ") for key in renderer.LABELS},
        "sources": [
            {"id": "S1", "locator": "docs/requirements.md"},
            {"id": "S2", "locator": "inspected checkout"},
        ],
        "requirements": [{"id": "FR-1", "source": "S1"}],
        "actors": [{"id": "reader", "label": "Reader", "source": "S1"}],
        "views": [
            {
                "id": "reading",
                "title": "Reading",
                "system": "Library",
                "actors": ["reader"],
                "cases": [
                    {
                        "id": "UC-1",
                        "label": "Read item",
                        "status": "implemented",
                        "actors": ["reader"],
                        "requirements": ["FR-1"],
                        "tasks": [],
                        "evidence": [
                            {
                                "kind": k,
                                "source": "S2",
                                "locator": f"example/{k}",
                                "detail": "Synthetic static inspection fixture.",
                            }
                            for k in ("code", "wiring", "test")
                        ],
                        "notes": "",
                    }
                ],
            }
        ],
        "notes": ["Synthetic fixture, not project status."],
    }


class UcdStatusTests(unittest.TestCase):
    @unittest.skipUnless(
        shutil.which("node"), "Node is only needed for the optional DOM probe"
    )
    def test_runtime_layout_and_tabs_with_unicode_and_long_labels(self):
        data = fixture()
        first = data["views"][0]
        first["system"] = "A system boundary with a longer localized name"
        data["actors"][0]["label"] = "Читач із довгою назвою ролі"
        for number in range(2, 9):
            case = copy.deepcopy(first["cases"][0])
            case["id"] = f"UC-{number}"
            case["label"] = (
                "Переглянути довгий текст повідомлення 日本語 "
                + "UnbrokenIdentifier" * 3
            )
            first["cases"].append(case)
        for number in range(2, 4):
            actor = {
                "id": f"actor-{number}",
                "label": "External service",
                "source": "S1",
            }
            data["actors"].append(actor)
            first["actors"].append(actor["id"])
            first["cases"][number]["actors"].append(actor["id"])
        second = copy.deepcopy(first)
        second["id"] = "second"
        data["views"].append(second)
        result = subprocess.run(
            [shutil.which("node"), str(ROOT / "tests" / "ucd_dom_probe.cjs")],
            input=renderer.render(data),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_implemented_needs_behavior_wiring_and_tests(self):
        for missing in ("code", "wiring", "test"):
            data = fixture()
            case = data["views"][0]["cases"][0]
            case["evidence"] = [p for p in case["evidence"] if p["kind"] != missing]
            with self.subTest(missing=missing), self.assertRaises(ValueError):
                renderer.validate(data)

    def test_closed_or_superseded_task_is_not_active_work(self):
        for state, superseded in (
            ("closed", False),
            ("open", False),
            ("in_progress", True),
        ):
            data = fixture()
            case = data["views"][0]["cases"][0]
            case["status"] = "in_progress"
            case["tasks"] = [
                {"id": "T1", "status": state, "superseded": superseded, "source": "S2"}
            ]
            with (
                self.subTest(state=state, superseded=superseded),
                self.assertRaises(ValueError),
            ):
                renderer.validate(data)

    def test_progress_with_task_or_actual_wip(self):
        for use_task in (True, False):
            data = fixture()
            case = data["views"][0]["cases"][0]
            case["status"] = "in_progress"
            if use_task:
                case["tasks"] = [
                    {
                        "id": "T1",
                        "status": "in_progress",
                        "superseded": False,
                        "source": "S2",
                    }
                ]
            else:
                case["evidence"][0]["kind"] = "work"
            self.assertIs(renderer.validate(data), data)

    def test_pending_needs_gap_and_unknown_needs_explanation(self):
        data = fixture()
        case = data["views"][0]["cases"][0]
        case["status"] = "pending"
        with self.assertRaises(ValueError):
            renderer.validate(data)
        case["evidence"][0]["kind"] = "gap"
        renderer.validate(data)
        case["status"] = "unknown"
        case["requirements"] = []
        with self.assertRaises(ValueError):
            renderer.validate(data)
        case["notes"] = "Requirement authority unavailable."
        renderer.validate(data)

    def test_references_and_snapshot_are_validated(self):
        mutations = [
            lambda d: d["views"][0]["cases"][0].update(requirements=["retired"]),
            lambda d: d["views"][0]["cases"][0].update(actors=["missing"]),
            lambda d: d["views"][0]["cases"][0]["evidence"][0].update(source="missing"),
            lambda d: d["sources"][0].update(sha256="not-a-hash"),
            lambda d: d["sources"].append(copy.deepcopy(d["sources"][0])),
            lambda d: d["snapshot"].update(checked_at="2026-01-01T12:00:00"),
            lambda d: d["views"][0]["cases"][0].update(status="almost done"),
            lambda d: d["views"][0]["cases"][0].update(requirements=[]),
        ]
        for change in mutations:
            data = fixture()
            change(data)
            with self.subTest(change=change), self.assertRaises(ValueError):
                renderer.validate(data)

    def test_duplicate_goal_requires_same_scope(self):
        data = fixture()
        second = copy.deepcopy(data["views"][0])
        second["id"] = "secondary"
        data["views"].append(second)
        renderer.validate(data)
        second["cases"][0]["label"] = "A different goal"
        with self.assertRaises(ValueError):
            renderer.validate(data)

    def test_plain_text_cannot_break_out_of_data_script(self):
        data = fixture()
        attack = '</script><script>alert("bad")</script>'
        data["title"] = attack
        data["views"][0]["cases"][0]["label"] = attack
        fragment = renderer.render(data)
        self.assertNotIn(attack, fragment)
        self.assertEqual(fragment.count("<script"), 2)
        payload = re.search(
            r'type="application/json"[^>]*>(.*?)</script>', fragment, re.DOTALL
        ).group(1)
        self.assertEqual(json.loads(payload)["title"], attack)
        self.assertNotIn("<!doctype", fragment)
        self.assertNotIn("__PAYLOAD__", fragment)
        self.assertNotIn("__ROOT__", fragment)
        standalone = renderer.render(data, True)
        self.assertTrue(standalone.startswith("<!doctype html>"))
        self.assertIn("&lt;/script&gt;", standalone)

    def test_cli_refuses_overwrite_and_preserves_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "input.json"
            manifest.write_text(json.dumps(fixture()), encoding="utf-8")
            original = manifest.read_bytes()
            output = Path(directory) / "view.html"
            command = [sys.executable, str(TOOL), str(manifest), str(output)]
            first = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(first.returncode, 0, first.stderr)
            saved = output.read_bytes()
            self.assertEqual(
                subprocess.run(command, capture_output=True, check=False).returncode, 2
            )
            self.assertEqual(output.read_bytes(), saved)
            same = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    str(manifest),
                    str(manifest),
                    "--overwrite",
                ],
                capture_output=True,
                check=False,
            )
            self.assertEqual(same.returncode, 2)
            self.assertEqual(manifest.read_bytes(), original)
            self.assertEqual(
                subprocess.run(
                    [sys.executable, str(TOOL), str(manifest), "--check"],
                    capture_output=True,
                    check=False,
                ).returncode,
                0,
            )


if __name__ == "__main__":
    unittest.main()
