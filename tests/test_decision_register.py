import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "skills" / "decision-register" / "scripts" / "decision_register.py"


def write_json(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def fixture(directory: Path) -> tuple[Path, Path]:
    requirements = {
        "schema_version": "requirements/v1",
        "document": {"id": "REQ-1", "title": "Приклад", "version": "1", "language": "uk"},
        "sources": [{"id": "SRC-1", "title": "Джерело"}],
        "requirements": [
            {
                "id": "BR-101",
                "type": "business-rule",
                "statement": "Система веде журнал.",
                "provenance": "explicit",
                "source_refs": ["SRC-1#L1", "SRC-1#L2"],
                "attributes": {"source_ids": ["Ф-101", "Ф-102"]},
            },
            {
                "id": "FR-101",
                "type": "functional",
                "statement": "Система показує журнал.",
                "provenance": "explicit",
                "source_refs": ["SRC-1#L3"],
                "attributes": {"source_id": "Ф-103"},
            },
        ],
        "open_items": [
            {
                "id": "OPEN-068",
                "question": "Хто затверджує?",
                "reason": "Немає рішення.",
                "affected_ids": ["BR-101"],
                "severity": "blocker",
                "status": "open",
            }
        ],
    }
    requirements_path = write_json(directory / "requirements.json", requirements)
    review = {
        "schema_version": "requirements-review/v1",
        "requirements_path": str(requirements_path),
        "requirements_sha256": hashlib.sha256(requirements_path.read_bytes()).hexdigest(),
        "reviewed_at": "2026-09-24T12:00:00+03:00",
        "findings": [
            {
                "id": "CRIT-020",
                "type": "MISSING",
                "severity": "blocker",
                "affected_ids": ["BR-101", "OPEN-068"],
                "defect": "Немає рішення.",
                "evidence": ["SRC-1#L1"],
                "resolution_needed": "Отримати рішення.",
                "status": "open",
            }
        ],
    }
    return requirements_path, write_json(directory / "review.json", review)


class DecisionRegisterTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *args], cwd=ROOT,
            text=True, capture_output=True, check=False,
        )

    def draft(self, directory: Path) -> tuple[Path, Path, Path]:
        requirements, review = fixture(directory)
        register = directory / "decision-register.json"
        result = self.run_tool(
            "draft", "--requirements", str(requirements), "--review", str(review),
            "--requirement-pattern", "(BR|FR)-101", "--open-pattern", "OPEN-068",
            "--output", str(register),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return requirements, review, register

    def test_draft_covers_clauses_requirements_and_open_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            requirements, review, register = self.draft(Path(temp))
            payload = json.loads(register.read_text(encoding="utf-8"))
            self.assertEqual(payload["scope"]["source_clause_ids"], ["Ф-101", "Ф-102", "Ф-103"])
            self.assertEqual(payload["source_clauses"][0]["source_refs"], ["SRC-1#L1"])
            self.assertEqual(payload["source_clauses"][1]["source_refs"], ["SRC-1#L2"])
            self.assertEqual(len(payload["requirement_owners"]), 2)
            self.assertEqual(len(payload["open_item_owners"]), 1)
            self.assertEqual(payload["open_item_owners"][0]["requirements_status"], "open")
            self.assertTrue(all(row["disposition"] == "pending" for row in payload["source_clauses"]))
            result = self.run_tool(
                "validate", "--requirements", str(requirements), "--review", str(review),
                "--register", str(register),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_review_must_match_requirements_before_draft(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            requirements, review = fixture(directory)
            requirements.write_bytes(requirements.read_bytes() + b"\n")
            result = self.run_tool(
                "draft", "--requirements", str(requirements), "--review", str(review),
                "--requirement-pattern", "BR-101", "--open-pattern", "OPEN-068",
                "--output", str(directory / "decision-register.json"),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requirements_sha256 does not match", result.stderr)

    def test_missing_ownership_row_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            requirements, review, register = self.draft(Path(temp))
            payload = json.loads(register.read_text(encoding="utf-8"))
            payload["open_item_owners"] = []
            write_json(register, payload)
            result = self.run_tool(
                "validate", "--requirements", str(requirements), "--review", str(review),
                "--register", str(register),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing OPEN-068", result.stderr)

    def test_open_status_drift_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            requirements, review, register = self.draft(Path(temp))
            payload = json.loads(register.read_text(encoding="utf-8"))
            payload["open_item_owners"][0]["requirements_status"] = "resolved"
            write_json(register, payload)
            result = self.run_tool(
                "validate", "--requirements", str(requirements), "--review", str(review),
                "--register", str(register),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("does not match requirements.json", result.stderr)

    def test_unsubstantiated_adoption_fails_and_provisional_decision_renders(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            requirements, review, register = self.draft(directory)
            payload = json.loads(register.read_text(encoding="utf-8"))
            invalid = copy.deepcopy(payload)
            invalid["source_clauses"][0]["disposition"] = "adopted"
            write_json(register, invalid)
            result = self.run_tool(
                "validate", "--requirements", str(requirements), "--review", str(review),
                "--register", str(register),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("decision_ref: required for adopted", result.stderr)

            clause = payload["source_clauses"][0]
            clause.update({
                "disposition": "provisional", "decision_owner": "Власник",
                "decision_ref": "docs/source/decision.md#R-1", "rationale": "Робочий напрям.",
                "provisional_rule": "Показувати журнал.",
                "review_trigger": "Відповідь бізнес-замовника.",
            })
            write_json(register, payload)
            output = directory / "decision-register.md"
            result = self.run_tool(
                "render", "--requirements", str(requirements), "--review", str(review),
                "--register", str(register), "--output", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            self.assertIn("Ф-101", markdown)
            self.assertIn("provisional", markdown)


if __name__ == "__main__":
    unittest.main()
