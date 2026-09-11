#!/usr/bin/env python3
"""Validate and render versioned requirements-pipeline artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

REQUIREMENT_ID = re.compile(r"^(BG|BR|FR|NFR|CON)-\d{3,}$")
OPEN_ID = re.compile(r"^OPEN-\d{3,}$")
CRIT_ID = re.compile(r"^CRIT-\d{3,}$")
OUTPUT_ID = {
    "invariants": re.compile(r"^INV-\d{3,}$"),
    "acceptance_criteria": re.compile(r"^AC-\d{3,}$"),
    "failure_scenarios": re.compile(r"^FAIL-\d{3,}$"),
    "gaps": re.compile(r"^GAP-\d{3,}$"),
}
SHA256 = re.compile(r"^[0-9a-f]{64}$")
TYPE_BY_PREFIX = {
    "BG": "business-goal",
    "BR": "business-rule",
    "FR": "functional",
    "NFR": "non-functional",
    "CON": "constraint",
}


class ArtifactError(ValueError):
    """Raised when an artifact does not satisfy its public contract."""


def _reject_constant(value: str) -> None:
    raise ArtifactError(f"non-finite JSON number is not allowed: {value}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ArtifactError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise ArtifactError(f"{path}: cannot read UTF-8 JSON: {exc}") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (json.JSONDecodeError, ArtifactError) as exc:
        raise ArtifactError(f"{path}: invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ArtifactError(f"{path}: root must be an object")
    return value


def _non_empty_string(value: Any, path: str, errors: list[str]) -> bool:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{path}: expected a non-empty string")
        return False
    return True


def _object(value: Any, path: str, errors: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return {}
    return value


def _array(value: Any, path: str, errors: list[str]) -> list[Any]:
    if not isinstance(value, list):
        errors.append(f"{path}: expected an array")
        return []
    return value


def _require_keys(
    value: dict[str, Any], keys: set[str], path: str, errors: list[str]
) -> None:
    for key in sorted(keys - value.keys()):
        errors.append(f"{path}.{key}: required property is missing")


def _allow_keys(
    value: dict[str, Any], keys: set[str], path: str, errors: list[str]
) -> None:
    for key in sorted(value.keys() - keys):
        errors.append(f"{path}: unexpected property '{key}'")


def validate_requirements(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    root_keys = {"schema_version", "document", "sources", "requirements", "open_items"}
    _require_keys(
        data,
        root_keys,
        "$",
        errors,
    )
    _allow_keys(data, root_keys, "$", errors)
    if data.get("schema_version") != "requirements/v1":
        errors.append("$.schema_version: expected 'requirements/v1'")

    document = _object(data.get("document"), "$.document", errors)
    document_keys = {"id", "title", "version", "language"}
    _require_keys(document, document_keys, "$.document", errors)
    _allow_keys(document, document_keys, "$.document", errors)
    for key in ("id", "title", "version", "language"):
        _non_empty_string(document.get(key), f"$.document.{key}", errors)

    source_ids: set[str] = set()
    for index, raw_source in enumerate(
        _array(data.get("sources"), "$.sources", errors)
    ):
        path = f"$.sources[{index}]"
        source = _object(raw_source, path, errors)
        _require_keys(source, {"id", "title"}, path, errors)
        source_id = source.get("id")
        if _non_empty_string(source_id, f"{path}.id", errors):
            if source_id in source_ids:
                errors.append(f"{path}.id: duplicate source ID '{source_id}'")
            source_ids.add(source_id)
        _non_empty_string(source.get("title"), f"{path}.title", errors)

    requirement_ids: set[str] = set()
    requirements = _array(data.get("requirements"), "$.requirements", errors)
    for index, raw_requirement in enumerate(requirements):
        path = f"$.requirements[{index}]"
        requirement = _object(raw_requirement, path, errors)
        requirement_keys = {
            "id",
            "type",
            "statement",
            "provenance",
            "source_refs",
            "attributes",
            "derivation",
        }
        _require_keys(
            requirement,
            {"id", "type", "statement", "provenance", "source_refs", "attributes"},
            path,
            errors,
        )
        _allow_keys(requirement, requirement_keys, path, errors)
        requirement_id = requirement.get("id")
        if _non_empty_string(requirement_id, f"{path}.id", errors):
            if not REQUIREMENT_ID.fullmatch(requirement_id):
                errors.append(f"{path}.id: invalid requirement ID '{requirement_id}'")
            elif requirement_id in requirement_ids:
                errors.append(f"{path}.id: duplicate requirement ID '{requirement_id}'")
            else:
                requirement_ids.add(requirement_id)
                prefix = requirement_id.split("-", 1)[0]
                expected_type = TYPE_BY_PREFIX[prefix]
                if requirement.get("type") != expected_type:
                    errors.append(
                        f"{path}.type: '{requirement_id}' requires '{expected_type}'"
                    )
        _non_empty_string(requirement.get("statement"), f"{path}.statement", errors)
        provenance = requirement.get("provenance")
        if provenance not in {"explicit", "derived"}:
            errors.append(f"{path}.provenance: expected 'explicit' or 'derived'")
        source_refs = _array(
            requirement.get("source_refs"), f"{path}.source_refs", errors
        )
        if not source_refs:
            errors.append(
                f"{path}.source_refs: at least one source reference is required"
            )
        for ref_index, source_ref in enumerate(source_refs):
            ref_path = f"{path}.source_refs[{ref_index}]"
            if _non_empty_string(source_ref, ref_path, errors):
                source_id = source_ref.split("#", 1)[0]
                if source_id not in source_ids:
                    errors.append(f"{ref_path}: unknown source ID '{source_id}'")
        if not isinstance(requirement.get("attributes"), dict):
            errors.append(f"{path}.attributes: expected an object")
        if provenance == "derived":
            derivation = _object(
                requirement.get("derivation"), f"{path}.derivation", errors
            )
            derivation_keys = {"support_refs", "explanation"}
            _require_keys(derivation, derivation_keys, f"{path}.derivation", errors)
            _allow_keys(derivation, derivation_keys, f"{path}.derivation", errors)
            supports = _array(
                derivation.get("support_refs"),
                f"{path}.derivation.support_refs",
                errors,
            )
            if not supports:
                errors.append(
                    f"{path}.derivation.support_refs: at least one reference is required"
                )
            _non_empty_string(
                derivation.get("explanation"),
                f"{path}.derivation.explanation",
                errors,
            )

    open_ids: set[str] = set()
    for index, raw_item in enumerate(
        _array(data.get("open_items"), "$.open_items", errors)
    ):
        path = f"$.open_items[{index}]"
        item = _object(raw_item, path, errors)
        item_keys = {"id", "question", "reason", "affected_ids", "severity", "status"}
        _require_keys(
            item,
            item_keys,
            path,
            errors,
        )
        _allow_keys(item, item_keys, path, errors)
        item_id = item.get("id")
        if _non_empty_string(item_id, f"{path}.id", errors):
            if not OPEN_ID.fullmatch(item_id):
                errors.append(f"{path}.id: invalid open-item ID '{item_id}'")
            elif item_id in open_ids:
                errors.append(f"{path}.id: duplicate open-item ID '{item_id}'")
            open_ids.add(item_id)
        _non_empty_string(item.get("question"), f"{path}.question", errors)
        _non_empty_string(item.get("reason"), f"{path}.reason", errors)
        affected = _array(item.get("affected_ids"), f"{path}.affected_ids", errors)
        for affected_index, requirement_id in enumerate(affected):
            affected_path = f"{path}.affected_ids[{affected_index}]"
            if requirement_id not in requirement_ids:
                errors.append(
                    f"{affected_path}: unknown requirement ID '{requirement_id}'"
                )
        if item.get("severity") not in {"blocker", "risk", "note"}:
            errors.append(f"{path}.severity: expected blocker, risk, or note")
        if item.get("status") not in {"open", "resolved", "accepted-risk"}:
            errors.append(f"{path}.status: expected open, resolved, or accepted-risk")

    return errors


def validate_review(
    data: dict[str, Any], requirement_ids: set[str] | None = None
) -> list[str]:
    errors: list[str] = []
    root_keys = {
        "schema_version",
        "requirements_path",
        "requirements_sha256",
        "reviewed_at",
        "findings",
    }
    _require_keys(data, root_keys, "$", errors)
    _allow_keys(data, root_keys, "$", errors)
    if data.get("schema_version") != "requirements-review/v1":
        errors.append("$.schema_version: expected 'requirements-review/v1'")
    _non_empty_string(data.get("requirements_path"), "$.requirements_path", errors)
    digest = data.get("requirements_sha256")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        errors.append("$.requirements_sha256: expected a lowercase SHA-256 digest")
    _non_empty_string(data.get("reviewed_at"), "$.reviewed_at", errors)

    finding_ids: set[str] = set()
    for index, raw_finding in enumerate(
        _array(data.get("findings"), "$.findings", errors)
    ):
        path = f"$.findings[{index}]"
        finding = _object(raw_finding, path, errors)
        finding_keys = {
            "id",
            "type",
            "severity",
            "affected_ids",
            "defect",
            "evidence",
            "resolution_needed",
            "status",
            "resolution",
        }
        _require_keys(
            finding,
            {
                "id",
                "type",
                "severity",
                "affected_ids",
                "defect",
                "evidence",
                "resolution_needed",
                "status",
            },
            path,
            errors,
        )
        _allow_keys(finding, finding_keys, path, errors)
        finding_id = finding.get("id")
        if _non_empty_string(finding_id, f"{path}.id", errors):
            if not CRIT_ID.fullmatch(finding_id):
                errors.append(f"{path}.id: invalid finding ID '{finding_id}'")
            elif finding_id in finding_ids:
                errors.append(f"{path}.id: duplicate finding ID '{finding_id}'")
            finding_ids.add(finding_id)
        if finding.get("type") not in {"LOCAL", "CROSS", "MISSING"}:
            errors.append(f"{path}.type: expected LOCAL, CROSS, or MISSING")
        if finding.get("severity") not in {"blocker", "risk", "note"}:
            errors.append(f"{path}.severity: expected blocker, risk, or note")
        affected = _array(finding.get("affected_ids"), f"{path}.affected_ids", errors)
        for affected_index, requirement_id in enumerate(affected):
            affected_path = f"{path}.affected_ids[{affected_index}]"
            if requirement_ids is not None and requirement_id not in requirement_ids:
                errors.append(
                    f"{affected_path}: unknown requirement ID '{requirement_id}'"
                )
        _non_empty_string(finding.get("defect"), f"{path}.defect", errors)
        evidence = _array(finding.get("evidence"), f"{path}.evidence", errors)
        if not evidence:
            errors.append(f"{path}.evidence: at least one evidence item is required")
        for evidence_index, item in enumerate(evidence):
            _non_empty_string(item, f"{path}.evidence[{evidence_index}]", errors)
        _non_empty_string(
            finding.get("resolution_needed"), f"{path}.resolution_needed", errors
        )
        status = finding.get("status")
        if status not in {"open", "resolved", "accepted-risk"}:
            errors.append(f"{path}.status: expected open, resolved, or accepted-risk")
        if status in {"resolved", "accepted-risk"}:
            resolution = _object(
                finding.get("resolution"), f"{path}.resolution", errors
            )
            resolution_keys = {"by", "at", "note"}
            _require_keys(resolution, resolution_keys, f"{path}.resolution", errors)
            _allow_keys(resolution, resolution_keys, f"{path}.resolution", errors)
            for key in ("by", "at", "note"):
                _non_empty_string(
                    resolution.get(key), f"{path}.resolution.{key}", errors
                )
    return errors


def validate_baseline(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "schema_version",
        "status",
        "approved_by",
        "approved_at",
        "scope",
        "requirements_path",
        "requirements_version",
        "requirements_sha256",
        "review_path",
        "review_sha256",
        "open_blockers",
    }
    _require_keys(data, required, "$", errors)
    _allow_keys(data, required, "$", errors)
    if data.get("schema_version") != "requirements-baseline/v1":
        errors.append("$.schema_version: expected 'requirements-baseline/v1'")
    if data.get("status") != "approved":
        errors.append("$.status: expected 'approved'")
    for key in (
        "approved_by",
        "approved_at",
        "scope",
        "requirements_path",
        "requirements_version",
        "review_path",
    ):
        _non_empty_string(data.get(key), f"$.{key}", errors)
    for key in ("requirements_sha256", "review_sha256"):
        digest = data.get(key)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"$.{key}: expected a lowercase SHA-256 digest")
    if type(data.get("open_blockers")) is not int or data.get("open_blockers") != 0:
        errors.append("$.open_blockers: expected 0")
    return errors


def validate_specification(
    data: dict[str, Any], requirement_ids: set[str] | None = None
) -> list[str]:
    errors: list[str] = []
    root_keys = {
        "schema_version",
        "requirements_sha256",
        "baseline_sha256",
        "invariants",
        "acceptance_criteria",
        "failure_scenarios",
        "gaps",
        "traceability",
    }
    _require_keys(data, root_keys, "$", errors)
    _allow_keys(data, root_keys, "$", errors)
    if data.get("schema_version") != "requirements-specification/v1":
        errors.append("$.schema_version: expected 'requirements-specification/v1'")
    for key in ("requirements_sha256", "baseline_sha256"):
        digest = data.get(key)
        if not isinstance(digest, str) or not SHA256.fullmatch(digest):
            errors.append(f"$.{key}: expected a lowercase SHA-256 digest")

    output_ids: dict[str, set[str]] = {key: set() for key in OUTPUT_ID}
    text_fields = {
        "invariants": (
            "statement",
            "scope",
            "checkable_condition",
            "violation_condition",
        ),
        "acceptance_criteria": ("statement",),
        "failure_scenarios": ("scenario", "expected_behavior"),
        "gaps": ("description",),
    }
    for collection, pattern in OUTPUT_ID.items():
        for index, raw_item in enumerate(
            _array(data.get(collection), f"$.{collection}", errors)
        ):
            path = f"$.{collection}[{index}]"
            item = _object(raw_item, path, errors)
            required = {"id", "source_requirement_ids", *text_fields[collection]}
            _require_keys(item, required, path, errors)
            _allow_keys(item, required, path, errors)
            item_id = item.get("id")
            if _non_empty_string(item_id, f"{path}.id", errors):
                if not pattern.fullmatch(item_id):
                    errors.append(f"{path}.id: invalid {collection} ID '{item_id}'")
                elif item_id in output_ids[collection]:
                    errors.append(f"{path}.id: duplicate output ID '{item_id}'")
                output_ids[collection].add(item_id)
            for field in text_fields[collection]:
                _non_empty_string(item.get(field), f"{path}.{field}", errors)
            refs = _array(
                item.get("source_requirement_ids"),
                f"{path}.source_requirement_ids",
                errors,
            )
            if not refs:
                errors.append(
                    f"{path}.source_requirement_ids: at least one ID is required"
                )
            for ref_index, requirement_id in enumerate(refs):
                ref_path = f"{path}.source_requirement_ids[{ref_index}]"
                if (
                    requirement_ids is not None
                    and requirement_id not in requirement_ids
                ):
                    errors.append(
                        f"{ref_path}: unknown requirement ID '{requirement_id}'"
                    )

    traceability = _array(data.get("traceability"), "$.traceability", errors)
    traced_requirements: set[str] = set()
    trace_fields = {
        "invariants": "invariants",
        "acceptance_criteria": "acceptance_criteria",
        "failure_scenarios": "failure_scenarios",
        "gaps": "gaps",
    }
    for index, raw_row in enumerate(traceability):
        path = f"$.traceability[{index}]"
        row = _object(raw_row, path, errors)
        row_keys = {"requirement_id", *trace_fields}
        _require_keys(row, row_keys, path, errors)
        _allow_keys(row, row_keys, path, errors)
        requirement_id = row.get("requirement_id")
        if _non_empty_string(requirement_id, f"{path}.requirement_id", errors):
            if requirement_ids is not None and requirement_id not in requirement_ids:
                errors.append(
                    f"{path}.requirement_id: unknown requirement ID '{requirement_id}'"
                )
            if requirement_id in traced_requirements:
                errors.append(
                    f"{path}.requirement_id: duplicate traceability row '{requirement_id}'"
                )
            traced_requirements.add(requirement_id)
        for field, collection in trace_fields.items():
            refs = _array(row.get(field), f"{path}.{field}", errors)
            for ref_index, output_id in enumerate(refs):
                if output_id not in output_ids[collection]:
                    errors.append(
                        f"{path}.{field}[{ref_index}]: unknown output ID '{output_id}'"
                    )
    return errors


def validate(
    kind: str,
    path: Path,
    requirements_path: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    data = load_json(path)
    if kind == "review" and requirements_path is not None:
        requirements = load_json(requirements_path)
        validate_data("requirements", requirements, requirements_path)
        errors = validate_review(
            data, {item["id"] for item in requirements["requirements"]}
        )
        version = "requirements-review/v1"
        if errors:
            raise ArtifactError("\n".join(f"{path}: {error}" for error in errors))
        if data.get("requirements_sha256") != sha256(requirements_path):
            raise ArtifactError(
                f"{path}: requirements_sha256 does not match {requirements_path}"
            )
    elif kind == "specification":
        if requirements_path is None or baseline_path is None:
            raise ArtifactError(
                "specification validation requires --requirements and --baseline"
            )
        requirements = load_json(requirements_path)
        validate_data("requirements", requirements, requirements_path)
        baseline = load_json(baseline_path)
        validate_data("baseline", baseline, baseline_path)
        errors = validate_specification(
            data, {item["id"] for item in requirements["requirements"]}
        )
        if baseline.get("scope") == "all":
            traced = {
                row.get("requirement_id")
                for row in data.get("traceability", [])
                if isinstance(row, dict)
            }
            for requirement_id in sorted(
                {item["id"] for item in requirements["requirements"]} - traced
            ):
                errors.append(
                    f"$.traceability: missing traceability row for '{requirement_id}'"
                )
        version = "requirements-specification/v1"
        if errors:
            raise ArtifactError("\n".join(f"{path}: {error}" for error in errors))
        if data.get("requirements_sha256") != sha256(requirements_path):
            raise ArtifactError(
                f"{path}: requirements_sha256 does not match {requirements_path}"
            )
        if data.get("baseline_sha256") != sha256(baseline_path):
            raise ArtifactError(
                f"{path}: baseline_sha256 does not match {baseline_path}"
            )
    else:
        version = validate_data(kind, data, path)
    print(f"PASS {version}: {path}")


def validate_data(kind: str, data: dict[str, Any], path: Path) -> str:
    if kind == "requirements":
        errors = validate_requirements(data)
        version = "requirements/v1"
    elif kind == "review":
        errors = validate_review(data)
        version = "requirements-review/v1"
    elif kind == "baseline":
        errors = validate_baseline(data)
        version = "requirements-baseline/v1"
    elif kind == "specification":
        errors = validate_specification(data)
        version = "requirements-specification/v1"
    else:
        raise ArtifactError(f"unsupported artifact kind: {kind}")
    if errors:
        raise ArtifactError("\n".join(f"{path}: {error}" for error in errors))
    return version


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ArtifactError(f"{path}: cannot calculate SHA-256: {exc}") from exc
    return digest.hexdigest()


def write_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def approve(
    requirements_path: Path,
    review_path: Path,
    approved_by: str,
    approved_at: str,
    scope: str,
    output: Path,
) -> None:
    if not approved_by.strip():
        raise ArtifactError("--approved-by must not be empty")
    if not approved_at.strip():
        raise ArtifactError("--approved-at must not be empty")
    if not scope.strip():
        raise ArtifactError("--scope must not be empty")
    requirements = load_json(requirements_path)
    validate_data("requirements", requirements, requirements_path)
    requirement_ids = {item["id"] for item in requirements["requirements"]}
    review = load_json(review_path)
    review_errors = validate_review(review, requirement_ids)
    if review_errors:
        raise ArtifactError(
            "\n".join(f"{review_path}: {error}" for error in review_errors)
        )
    requirements_digest = sha256(requirements_path)
    if review["requirements_sha256"] != requirements_digest:
        raise ArtifactError(
            f"{review_path}: requirements_sha256 does not match {requirements_path}"
        )
    open_blockers = [
        finding
        for finding in review["findings"]
        if finding["severity"] == "blocker" and finding["status"] == "open"
    ]
    if open_blockers:
        ids = ", ".join(finding["id"] for finding in open_blockers)
        raise ArtifactError(f"cannot approve: open critic blockers: {ids}")
    open_items = [
        item for item in requirements["open_items"] if item["status"] == "open"
    ]
    if open_items:
        ids = ", ".join(item["id"] for item in open_items)
        raise ArtifactError(f"cannot approve: unresolved open items: {ids}")
    if output.exists():
        raise ArtifactError(
            f"{output}: baseline already exists; choose a new versioned path"
        )
    baseline = {
        "schema_version": "requirements-baseline/v1",
        "status": "approved",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "scope": scope,
        "requirements_path": str(requirements_path),
        "requirements_version": requirements["document"]["version"],
        "requirements_sha256": requirements_digest,
        "review_path": str(review_path),
        "review_sha256": sha256(review_path),
        "open_blockers": 0,
    }
    write_json_atomic(output, baseline)
    print(f"WROTE {output}")


def gate(requirements_path: Path, review_path: Path, baseline_path: Path) -> None:
    requirements = load_json(requirements_path)
    validate_data("requirements", requirements, requirements_path)
    requirement_ids = {item["id"] for item in requirements["requirements"]}
    review = load_json(review_path)
    review_errors = validate_review(review, requirement_ids)
    if review_errors:
        raise ArtifactError(
            "\n".join(f"{review_path}: {error}" for error in review_errors)
        )
    baseline = load_json(baseline_path)
    baseline_errors = validate_baseline(baseline)
    if baseline_errors:
        raise ArtifactError(
            "\n".join(f"{baseline_path}: {error}" for error in baseline_errors)
        )

    requirements_digest = sha256(requirements_path)
    review_digest = sha256(review_path)
    failures: list[str] = []
    if review["requirements_sha256"] != requirements_digest:
        failures.append(
            f"{review_path}: requirements_sha256 does not match {requirements_path}"
        )
    if baseline["requirements_sha256"] != requirements_digest:
        failures.append(
            f"{baseline_path}: requirements_sha256 does not match {requirements_path}"
        )
    if baseline["review_sha256"] != review_digest:
        failures.append(f"{baseline_path}: review_sha256 does not match {review_path}")
    if baseline["requirements_version"] != requirements["document"]["version"]:
        failures.append(
            f"{baseline_path}: requirements_version does not match $.document.version"
        )
    open_blockers = [
        item["id"]
        for item in review["findings"]
        if item["severity"] == "blocker" and item["status"] == "open"
    ]
    if open_blockers:
        failures.append(
            f"{review_path}: open critic blockers: {', '.join(open_blockers)}"
        )
    open_items = [
        item["id"] for item in requirements["open_items"] if item["status"] == "open"
    ]
    if open_items:
        failures.append(
            f"{requirements_path}: unresolved open items: {', '.join(open_items)}"
        )
    if failures:
        raise ArtifactError("\n".join(failures))
    print(f"PASS compilation gate: {baseline_path}")


def _candidate_path(target: Path) -> Path:
    first = target.with_name(f"{target.stem}.candidate{target.suffix}")
    if not first.exists():
        return first
    sequence = 2
    while True:
        candidate = target.with_name(
            f"{target.stem}.candidate-{sequence:02d}{target.suffix}"
        )
        if not candidate.exists():
            return candidate
        sequence += 1


def safe_write(kind: str, source: Path, target: Path, replace: bool) -> None:
    data = load_json(source)
    validate_data(kind, data, source)
    destination = target
    if target.exists() and not replace:
        destination = _candidate_path(target)
    write_json_atomic(destination, data)
    print(f"WROTE {destination}")


def _cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def render_requirements(data: dict[str, Any]) -> str:
    document = data["document"]
    lines = [
        f"# {document['title']}",
        "",
        f"Версія: `{document['version']}`  ",
        f"Мова: `{document['language']}`  ",
        f"Контракт: `{data['schema_version']}`",
        "",
        "## Вимоги",
        "",
        "| ID | Тип | Формулювання | Походження | Джерела |",
        "| --- | --- | --- | --- | --- |",
    ]
    for requirement in data["requirements"]:
        lines.append(
            "| {id} | {type} | {statement} | {provenance} | {sources} |".format(
                id=_cell(requirement["id"]),
                type=_cell(requirement["type"]),
                statement=_cell(requirement["statement"]),
                provenance=_cell(requirement["provenance"]),
                sources=_cell(", ".join(requirement["source_refs"])),
            )
        )
    lines.extend(["", "## Відкриті питання", ""])
    if not data["open_items"]:
        lines.append("Немає.")
    else:
        lines.extend(
            [
                "| ID | Серйозність | Статус | Питання | Пов'язані вимоги |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in data["open_items"]:
            lines.append(
                "| {id} | {severity} | {status} | {question} | {affected} |".format(
                    id=_cell(item["id"]),
                    severity=_cell(item["severity"]),
                    status=_cell(item["status"]),
                    question=_cell(item["question"]),
                    affected=_cell(", ".join(item["affected_ids"])),
                )
            )
    lines.extend(["", "## Джерела", ""])
    for source in data["sources"]:
        lines.append(f"- `{_cell(source['id'])}` — {_cell(source['title'])}")
    return "\n".join(lines) + "\n"


def render_review(data: dict[str, Any]) -> str:
    findings = data["findings"]
    lines = [
        "# Критика вимог",
        "",
        f"Перевірено: `{data['reviewed_at']}`  ",
        f"SHA-256 вимог: `{data['requirements_sha256']}`",
        "",
        "| ID | Тип | Серйозність | Статус | Вимоги | Дефект | Потрібне рішення |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for finding in findings:
        lines.append(
            "| {id} | {type} | {severity} | {status} | {affected} | {defect} | {resolution} |".format(
                id=_cell(finding["id"]),
                type=_cell(finding["type"]),
                severity=_cell(finding["severity"]),
                status=_cell(finding["status"]),
                affected=_cell(", ".join(finding["affected_ids"])),
                defect=_cell(finding["defect"]),
                resolution=_cell(finding["resolution_needed"]),
            )
        )
    counts = {
        severity: sum(
            1
            for finding in findings
            if finding["severity"] == severity and finding["status"] == "open"
        )
        for severity in ("blocker", "risk", "note")
    }
    lines.extend(
        [
            "",
            "## Підсумок",
            "",
            f"- Відкриті blockers: {counts['blocker']}",
            f"- Відкриті risks: {counts['risk']}",
            f"- Відкриті notes: {counts['note']}",
        ]
    )
    return "\n".join(lines) + "\n"


def render_specification(data: dict[str, Any]) -> str:
    labels = {
        "statement": "Формулювання",
        "scope": "Область",
        "checkable_condition": "Умова перевірки",
        "violation_condition": "Умова порушення",
        "scenario": "Сценарій",
        "expected_behavior": "Очікувана поведінка",
        "description": "Опис",
    }
    lines = [
        "# Специфікація",
        "",
        f"Контракт: `{data['schema_version']}`  ",
        f"SHA-256 вимог: `{data['requirements_sha256']}`  ",
        f"SHA-256 baseline: `{data['baseline_sha256']}`",
    ]
    sections = [
        (
            "Інваріанти",
            "invariants",
            ("statement", "scope", "checkable_condition", "violation_condition"),
        ),
        ("Критерії приймання", "acceptance_criteria", ("statement",)),
        ("Сценарії відмов", "failure_scenarios", ("scenario", "expected_behavior")),
        ("Прогалини", "gaps", ("description",)),
    ]
    for title, collection, fields in sections:
        lines.extend(["", f"## {title}", ""])
        if not data[collection]:
            lines.append("Немає.")
            continue
        for item in data[collection]:
            lines.append(f"### `{item['id']}`")
            lines.append("")
            for field in fields:
                lines.append(f"- **{labels[field]}:** {_cell(item[field])}")
            lines.append(
                f"- **Вихідні вимоги:** {_cell(', '.join(item['source_requirement_ids']))}"
            )
            lines.append("")
    lines.extend(
        [
            "## Матриця трасування",
            "",
            "| Вимога | INV | AC | FAIL | GAP |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in data["traceability"]:
        lines.append(
            "| {requirement} | {inv} | {ac} | {fail} | {gap} |".format(
                requirement=_cell(row["requirement_id"]),
                inv=_cell(", ".join(row["invariants"])),
                ac=_cell(", ".join(row["acceptance_criteria"])),
                fail=_cell(", ".join(row["failure_scenarios"])),
                gap=_cell(", ".join(row["gaps"])),
            )
        )
    return "\n".join(lines) + "\n"


def render(
    kind: str,
    source: Path,
    output: Path | None,
    requirements_path: Path | None = None,
    baseline_path: Path | None = None,
) -> None:
    data = load_json(source)
    validate(kind, source, requirements_path, baseline_path)
    if kind == "requirements":
        markdown = render_requirements(data)
    elif kind == "review":
        markdown = render_review(data)
    elif kind == "specification":
        markdown = render_specification(data)
    else:
        raise ArtifactError(f"unsupported artifact kind: {kind}")
    destination = output or source.with_suffix(".md")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(markdown, encoding="utf-8")
    print(f"WROTE {destination}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate an artifact")
    validate_parser.add_argument(
        "kind", choices=["requirements", "review", "baseline", "specification"]
    )
    validate_parser.add_argument("path", type=Path)
    validate_parser.add_argument("--requirements", type=Path)
    validate_parser.add_argument("--baseline", type=Path)
    write_parser = subparsers.add_parser(
        "safe-write",
        help="write a validated artifact without replacing the primary file implicitly",
    )
    write_parser.add_argument(
        "kind", choices=["requirements", "review", "baseline", "specification"]
    )
    write_parser.add_argument("source", type=Path)
    write_parser.add_argument("target", type=Path)
    write_parser.add_argument("--replace", action="store_true")
    render_parser = subparsers.add_parser("render", help="render Markdown from JSON")
    render_parser.add_argument(
        "kind", choices=["requirements", "review", "specification"]
    )
    render_parser.add_argument("source", type=Path)
    render_parser.add_argument("--output", type=Path)
    render_parser.add_argument("--requirements", type=Path)
    render_parser.add_argument("--baseline", type=Path)
    approve_parser = subparsers.add_parser(
        "approve", help="create an immutable baseline after explicit human approval"
    )
    approve_parser.add_argument("--requirements", type=Path, required=True)
    approve_parser.add_argument("--review", type=Path, required=True)
    approve_parser.add_argument("--approved-by", required=True)
    approve_parser.add_argument("--approved-at", required=True)
    approve_parser.add_argument("--scope", required=True)
    approve_parser.add_argument("--output", type=Path, required=True)
    gate_parser = subparsers.add_parser(
        "gate", help="verify approved inputs before specification compilation"
    )
    gate_parser.add_argument("--requirements", type=Path, required=True)
    gate_parser.add_argument("--review", type=Path, required=True)
    gate_parser.add_argument("--baseline", type=Path, required=True)
    digest_parser = subparsers.add_parser("digest", help="print an artifact SHA-256")
    digest_parser.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "validate":
            validate(args.kind, args.path, args.requirements, args.baseline)
        elif args.command == "safe-write":
            safe_write(args.kind, args.source, args.target, args.replace)
        elif args.command == "render":
            render(
                args.kind,
                args.source,
                args.output,
                args.requirements,
                args.baseline,
            )
        elif args.command == "approve":
            approve(
                args.requirements,
                args.review,
                args.approved_by,
                args.approved_at,
                args.scope,
                args.output,
            )
        elif args.command == "gate":
            gate(args.requirements, args.review, args.baseline)
        elif args.command == "digest":
            print(sha256(args.path))
        return 0
    except ArtifactError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
