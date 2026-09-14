import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "contracts" / "requirements-pipeline" / "v1" / "pipeline_artifacts.py"
SYNC_TOOL = ROOT / "scripts" / "sync_requirements_contracts.py"


def valid_requirements() -> dict:
    return {
        "schema_version": "requirements/v1",
        "document": {
            "id": "REQSET-001",
            "title": "Портал заявок",
            "version": "1.0",
            "language": "uk",
        },
        "sources": [
            {
                "id": "SRC-001",
                "title": "brief.md",
                "kind": "markdown",
            }
        ],
        "requirements": [
            {
                "id": "FR-001",
                "type": "functional",
                "statement": "Система повинна зберігати заявку.",
                "provenance": "explicit",
                "source_refs": ["SRC-001#section-2"],
                "attributes": {"actor": "Користувач", "priority": "must"},
            }
        ],
        "open_items": [],
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_review(requirements_path: Path, findings: list[dict] | None = None) -> dict:
    return {
        "schema_version": "requirements-review/v1",
        "requirements_path": str(requirements_path),
        "requirements_sha256": sha256(requirements_path),
        "reviewed_at": "2026-09-11T10:00:00+03:00",
        "findings": findings or [],
    }


def open_blocker() -> dict:
    return {
        "id": "CRIT-001",
        "type": "LOCAL",
        "severity": "blocker",
        "affected_ids": ["FR-001"],
        "defect": "Не визначено формат номера заявки.",
        "evidence": ["FR-001 не містить формату номера."],
        "resolution_needed": "Уточнити формат номера.",
        "status": "open",
    }


def requirement(requirement_id: str, requirement_type: str) -> dict:
    return {
        "id": requirement_id,
        "type": requirement_type,
        "statement": f"Вимога {requirement_id}.",
        "provenance": "explicit",
        "source_refs": ["SRC-001#sorting"],
        "attributes": {},
    }


def open_item(item_id: str, severity: str, status: str) -> dict:
    return {
        "id": item_id,
        "question": f"Питання {item_id}?",
        "reason": "Потрібне уточнення.",
        "affected_ids": ["FR-001"],
        "severity": severity,
        "status": status,
    }


def finding(finding_id: str, finding_type: str, severity: str, status: str) -> dict:
    result = {
        "id": finding_id,
        "type": finding_type,
        "severity": severity,
        "affected_ids": ["FR-001"],
        "defect": f"Дефект {finding_id}.",
        "evidence": ["Перевірочний приклад."],
        "resolution_needed": "Уточнити вимогу.",
        "status": status,
    }
    if status != "open":
        result["resolution"] = {
            "by": "Максим",
            "at": "2026-09-14T12:00:00+03:00",
            "note": "Рішення зафіксовано.",
        }
    return result


def valid_specification(
    requirements_path: Path, baseline_path: Path, source_id: str = "FR-001"
) -> dict:
    return {
        "schema_version": "requirements-specification/v1",
        "requirements_sha256": sha256(requirements_path),
        "baseline_sha256": sha256(baseline_path),
        "invariants": [
            {
                "id": "INV-001",
                "statement": "Кожна збережена заявка має стабільний ID.",
                "scope": "Збережена заявка",
                "checkable_condition": "ID існує та не змінюється.",
                "violation_condition": "ID відсутній або змінився.",
                "source_requirement_ids": [source_id],
            }
        ],
        "acceptance_criteria": [
            {
                "id": "AC-001",
                "statement": "WHEN користувач зберігає заявку, THE SYSTEM SHALL повернути її ID.",
                "source_requirement_ids": [source_id],
            }
        ],
        "failure_scenarios": [
            {
                "id": "FAIL-001",
                "scenario": "Сховище недоступне.",
                "expected_behavior": "Система повідомляє про незбережену заявку.",
                "source_requirement_ids": [source_id],
            }
        ],
        "gaps": [],
        "traceability": [
            {
                "requirement_id": source_id,
                "invariants": ["INV-001"],
                "acceptance_criteria": ["AC-001"],
                "failure_scenarios": ["FAIL-001"],
                "gaps": [],
            }
        ],
    }


class RequirementsPipelineTests(unittest.TestCase):
    def run_tool(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(TOOL), *args],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

    def write_json(self, directory: Path, name: str, payload: dict) -> Path:
        path = directory / name
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return path

    def test_requirements_validator_accepts_traceable_document(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_json(
                Path(temp_dir), "requirements.json", valid_requirements()
            )

            result = self.run_tool("validate", "requirements", str(path))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("PASS requirements/v1", result.stdout)

    def test_safe_write_preserves_manual_requirements_and_creates_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            current = valid_requirements()
            current["document"]["title"] = "Ручна версія"
            proposed = valid_requirements()
            proposed["document"]["title"] = "Нова пропозиція"
            target = self.write_json(directory, "requirements.json", current)
            source = self.write_json(directory, "generated.json", proposed)

            result = self.run_tool(
                "safe-write", "requirements", str(source), str(target)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), current)
            candidate = directory / "requirements.candidate.json"
            self.assertTrue(candidate.is_file())
            self.assertEqual(
                json.loads(candidate.read_text(encoding="utf-8")), proposed
            )
            self.assertIn(str(candidate), result.stdout)

    def test_requirements_markdown_is_rendered_from_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            source = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            output = directory / "requirements.md"

            result = self.run_tool(
                "render", "requirements", str(source), "--output", str(output)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            self.assertIn("# Портал заявок", markdown)
            self.assertIn("FR-001", markdown)
            self.assertIn("SRC-001#section-2", markdown)

    def test_requirements_markdown_sorts_types_and_open_items_by_importance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            payload = valid_requirements()
            payload["requirements"] = [
                requirement("CON-001", "constraint"),
                requirement("FR-010", "functional"),
                requirement("BG-001", "business-goal"),
                requirement("FR-002", "functional"),
                requirement("FR-001", "functional"),
                requirement("BR-001", "business-rule"),
                requirement("NFR-001", "non-functional"),
            ]
            payload["open_items"] = [
                open_item("OPEN-005", "note", "open"),
                open_item("OPEN-004", "blocker", "resolved"),
                open_item("OPEN-003", "risk", "open"),
                open_item("OPEN-002", "blocker", "accepted-risk"),
                open_item("OPEN-001", "blocker", "open"),
            ]
            source = self.write_json(directory, "requirements.json", payload)
            output = directory / "requirements.md"

            result = self.run_tool(
                "render", "requirements", str(source), "--output", str(output)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            expected = [
                "BG-001",
                "BR-001",
                "FR-001",
                "FR-002",
                "FR-010",
                "NFR-001",
                "CON-001",
                "OPEN-001",
                "OPEN-002",
                "OPEN-004",
                "OPEN-003",
                "OPEN-005",
            ]
            positions = [markdown.index(item_id) for item_id in expected]
            self.assertEqual(positions, sorted(positions))

            self.assertEqual(payload["requirements"][0]["id"], "CON-001")
            self.assertEqual(payload["open_items"][0]["id"], "OPEN-005")

    def test_explicit_approval_creates_hash_bound_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory, "review.json", valid_review(requirements)
            )
            baseline = directory / "baseline.json"

            result = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-11T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(baseline),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(baseline.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "approved")
            self.assertEqual(payload["requirements_sha256"], sha256(requirements))
            self.assertEqual(payload["review_sha256"], sha256(review))
            self.assertEqual(payload["open_blockers"], 0)

    def test_compilation_gate_rejects_requirements_changed_after_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            payload = valid_requirements()
            requirements = self.write_json(directory, "requirements.json", payload)
            review = self.write_json(
                directory, "review.json", valid_review(requirements)
            )
            baseline = directory / "baseline.json"
            approval = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-11T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(baseline),
            )
            self.assertEqual(approval.returncode, 0, approval.stderr)
            payload["requirements"][0]["statement"] = "Змінена вручну вимога."
            self.write_json(directory, "requirements.json", payload)

            result = self.run_tool(
                "gate",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--baseline",
                str(baseline),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("requirements_sha256", result.stderr)

    def test_review_markdown_exposes_open_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory,
                "review.json",
                valid_review(requirements, [open_blocker()]),
            )
            output = directory / "review.md"

            result = self.run_tool(
                "render", "review", str(review), "--output", str(output)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            self.assertIn("CRIT-001", markdown)
            self.assertIn("blocker", markdown)
            self.assertIn("open", markdown)

    def test_review_markdown_sorts_by_severity_status_type_and_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory,
                "review.json",
                valid_review(
                    requirements,
                    [
                        finding("CRIT-008", "LOCAL", "note", "open"),
                        finding("CRIT-007", "LOCAL", "blocker", "resolved"),
                        finding("CRIT-006", "LOCAL", "risk", "open"),
                        finding("CRIT-005", "LOCAL", "blocker", "open"),
                        finding("CRIT-004", "MISSING", "blocker", "open"),
                        finding("CRIT-010", "CROSS", "blocker", "open"),
                        finding("CRIT-002", "CROSS", "blocker", "open"),
                    ],
                ),
            )
            output = directory / "review.md"

            result = self.run_tool(
                "render", "review", str(review), "--output", str(output)
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            expected = [
                "CRIT-002",
                "CRIT-010",
                "CRIT-004",
                "CRIT-005",
                "CRIT-007",
                "CRIT-006",
                "CRIT-008",
            ]
            positions = [markdown.index(item_id) for item_id in expected]
            self.assertEqual(positions, sorted(positions))

    def test_specification_validator_rejects_unknown_requirement_reference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory, "review.json", valid_review(requirements)
            )
            baseline = directory / "baseline.json"
            approval = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-11T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(baseline),
            )
            self.assertEqual(approval.returncode, 0, approval.stderr)
            specification = self.write_json(
                directory,
                "specification.json",
                valid_specification(requirements, baseline, source_id="FR-999"),
            )

            result = self.run_tool(
                "validate",
                "specification",
                str(specification),
                "--requirements",
                str(requirements),
                "--baseline",
                str(baseline),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unknown requirement ID 'FR-999'", result.stderr)

    def test_specification_markdown_contains_traceable_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory, "review.json", valid_review(requirements)
            )
            baseline = directory / "baseline.json"
            approval = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-11T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(baseline),
            )
            self.assertEqual(approval.returncode, 0, approval.stderr)
            specification = self.write_json(
                directory,
                "specification.json",
                valid_specification(requirements, baseline),
            )
            output = directory / "specification.md"

            result = self.run_tool(
                "render",
                "specification",
                str(specification),
                "--requirements",
                str(requirements),
                "--baseline",
                str(baseline),
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            self.assertIn("INV-001", markdown)
            self.assertIn("AC-001", markdown)
            self.assertIn("FAIL-001", markdown)
            self.assertIn("FR-001", markdown)

    def test_specification_markdown_sorts_output_types_and_numeric_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory, "review.json", valid_review(requirements)
            )
            baseline = directory / "baseline.json"
            approval = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-14T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(baseline),
            )
            self.assertEqual(approval.returncode, 0, approval.stderr)
            payload = valid_specification(requirements, baseline)
            payload["gaps"] = [
                {
                    "id": "GAP-010",
                    "description": "Прогалина 10.",
                    "source_requirement_ids": ["FR-001"],
                },
                {
                    "id": "GAP-002",
                    "description": "Прогалина 2.",
                    "source_requirement_ids": ["FR-001"],
                },
            ]
            payload["traceability"][0]["gaps"] = ["GAP-002", "GAP-010"]
            specification = self.write_json(
                directory, "specification.json", payload
            )
            output = directory / "specification.md"

            result = self.run_tool(
                "render",
                "specification",
                str(specification),
                "--requirements",
                str(requirements),
                "--baseline",
                str(baseline),
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            markdown = output.read_text(encoding="utf-8")
            expected = ["GAP-002", "GAP-010", "FAIL-001", "INV-001", "AC-001"]
            positions = [markdown.index(item_id) for item_id in expected]
            self.assertEqual(positions, sorted(positions))

    def test_installed_contract_copies_match_canonical_sources(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SYNC_TOOL), "--check"],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS contract copies", result.stdout)

    def test_digest_reports_sha256_for_artifact_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self.write_json(
                Path(temp_dir), "requirements.json", valid_requirements()
            )

            result = self.run_tool("digest", str(path))

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), sha256(path))

    def test_specification_requires_traceability_for_every_approved_requirement(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory, "review.json", valid_review(requirements)
            )
            baseline = directory / "baseline.json"
            approval = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-11T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(baseline),
            )
            self.assertEqual(approval.returncode, 0, approval.stderr)
            payload = valid_specification(requirements, baseline)
            payload["traceability"] = []
            specification = self.write_json(directory, "specification.json", payload)

            result = self.run_tool(
                "validate",
                "specification",
                str(specification),
                "--requirements",
                str(requirements),
                "--baseline",
                str(baseline),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing traceability row for 'FR-001'", result.stderr)

    def test_approval_rejects_open_critic_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            requirements = self.write_json(
                directory, "requirements.json", valid_requirements()
            )
            review = self.write_json(
                directory,
                "review.json",
                valid_review(requirements, [open_blocker()]),
            )

            result = self.run_tool(
                "approve",
                "--requirements",
                str(requirements),
                "--review",
                str(review),
                "--approved-by",
                "Максим",
                "--approved-at",
                "2026-09-11T12:00:00+03:00",
                "--scope",
                "all",
                "--output",
                str(directory / "baseline.json"),
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("open critic blockers: CRIT-001", result.stderr)

    def test_runtime_rejects_properties_forbidden_by_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            payload = valid_requirements()
            payload["unexpected"] = True
            path = self.write_json(Path(temp_dir), "requirements.json", payload)

            result = self.run_tool("validate", "requirements", str(path))

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("unexpected property 'unexpected'", result.stderr)


if __name__ == "__main__":
    unittest.main()
