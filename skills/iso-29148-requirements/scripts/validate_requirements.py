#!/usr/bin/env python3
"""Validate canonical public-principles ISO 29148 requirements documents.

The module intentionally uses only the Python standard library.  Importers can
call ``validate_document`` without triggering command-line behaviour.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "1.1"
PROFILE = "public-principles/29148:2018"

LEVELS = ("BRS", "StRS", "SyRS", "SRS")
SOURCE_STATUSES = ("processed", "partial", "skipped")
CONTEXT_TYPES = ("goal", "assumption", "decision", "definition", "out-of-scope")
REQUIREMENT_CATEGORIES = (
    "functional",
    "quality",
    "interface",
    "data",
    "constraint",
    "business-rule",
    "regulatory",
    "transition",
    "other",
)
PROVENANCE_VALUES = ("explicit", "derived", "inferred")
CONFIDENCE_VALUES = ("high", "medium", "low")
QUALITY_STATUSES = (
    "normalized",
    "needs-review",
)
DISPOSITIONS = (
    "proposed",
    "accepted",
    "rejected",
    "superseded",
)
QUALITY_CODES = (
    "ambiguity",
    "compound",
    "unverifiable",
    "conflicting",
    "unclear-level",
    "unsupported-inference",
    "feasibility-unknown",
    "other",
)
FINDING_SEVERITIES = ("blocking", "warning")
RELATIONSHIP_TYPES = ("parent-of", "depends-on", "conflicts-with", "duplicates")
ISSUE_TYPES = (
    "gap",
    "ambiguity",
    "conflict",
    "duplicate",
    "unreadable-source",
    "assumption",
    "low-confidence",
    "quality",
    "decision-required",
    "other",
)
ISSUE_SEVERITIES = ("warning", "blocking")
ISSUE_STATUSES = ("open", "resolved")
COVERAGE_STATUSES = ("supported", "gap", "not-applicable")

SOURCE_ID_RE = re.compile(r"SRC-[0-9]{3,}\Z")
CONTEXT_ID_RE = re.compile(r"CTX-[0-9]{4,}\Z")
REQUIREMENT_ID_RE = re.compile(r"REQ-[0-9]{6,}\Z")
RELATIONSHIP_ID_RE = re.compile(r"REL-[0-9]{4,}\Z")
ISSUE_ID_RE = re.compile(r"ISS-[0-9]{4,}\Z")
SHA256_RE = re.compile(r"[0-9a-fA-F]{64}\Z")

RELATIONSHIP_FIELDS_IN_REQUIREMENT = (
    "parent_ids",
    "depends_on",
    "conflicts_with",
    "duplicate_of",
)


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _required_array(
    obj: dict[str, Any], key: str, base_path: str, errors: list[str]
) -> tuple[list[Any], bool]:
    path = f"{base_path}.{key}"
    if key not in obj:
        errors.append(f"{path}: required field is missing")
        return [], False
    value = obj[key]
    if not isinstance(value, list):
        errors.append(f"{path}: expected an array")
        return [], False
    return value, True


def _required_object(
    obj: dict[str, Any], key: str, base_path: str, errors: list[str]
) -> tuple[dict[str, Any], bool]:
    path = f"{base_path}.{key}"
    if key not in obj:
        errors.append(f"{path}: required field is missing")
        return {}, False
    value = obj[key]
    if not isinstance(value, dict):
        errors.append(f"{path}: expected an object")
        return {}, False
    return value, True


def _require_nonempty_string(
    obj: dict[str, Any], key: str, base_path: str, errors: list[str]
) -> Any:
    path = f"{base_path}.{key}"
    if key not in obj:
        errors.append(f"{path}: required field is missing")
        return None
    value = obj[key]
    if not _is_nonempty_string(value):
        errors.append(f"{path}: expected a non-empty string")
    return value


def _require_nullable_string(
    obj: dict[str, Any], key: str, base_path: str, errors: list[str]
) -> Any:
    path = f"{base_path}.{key}"
    if key not in obj:
        errors.append(f"{path}: required field is missing")
        return None
    value = obj[key]
    if value is not None and not isinstance(value, str):
        errors.append(f"{path}: expected a string or null")
    return value


def _require_nullable_id(
    obj: dict[str, Any],
    key: str,
    pattern: re.Pattern[str],
    example: str,
    base_path: str,
    errors: list[str],
) -> tuple[str | None, bool]:
    """Return ``(value, valid)`` for a required nullable identifier field."""

    path = f"{base_path}.{key}"
    if key not in obj:
        errors.append(f"{path}: required field is missing")
        return None, False

    value = obj[key]
    if value is None:
        return None, True
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        errors.append(f"{path}: expected null or an ID matching {example}")
        return None, False
    return value, True


def _require_enum(
    obj: dict[str, Any],
    key: str,
    allowed: tuple[str, ...],
    base_path: str,
    errors: list[str],
) -> Any:
    path = f"{base_path}.{key}"
    if key not in obj:
        errors.append(f"{path}: required field is missing")
        return None
    value = obj[key]
    if not isinstance(value, str) or value not in allowed:
        expected = ", ".join(allowed)
        errors.append(f"{path}: expected one of [{expected}]")
    return value


def _validate_id(
    obj: dict[str, Any],
    base_path: str,
    pattern: re.Pattern[str],
    example: str,
    seen: dict[str, str],
    valid_ids: set[str],
    errors: list[str],
) -> Any:
    path = f"{base_path}.id"
    if "id" not in obj:
        errors.append(f"{path}: required field is missing")
        return None

    value = obj["id"]
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        errors.append(f"{path}: expected an ID matching {example}")

    if isinstance(value, str):
        if value in seen:
            errors.append(f"{path}: duplicate ID {value!r}; first declared at {seen[value]}")
        else:
            seen[value] = path
        if pattern.fullmatch(value) is not None:
            valid_ids.add(value)
    return value


def _validate_source_refs(
    obj: dict[str, Any],
    key: str,
    base_path: str,
    valid_source_ids: set[str],
    source_status_by_id: dict[str, str],
    source_index_available: bool,
    errors: list[str],
    warnings: list[str],
    *,
    require_nonempty: bool,
) -> list[tuple[str, str]]:
    """Validate evidence references and return their non-empty source IDs."""

    refs, refs_are_array = _required_array(obj, key, base_path, errors)
    refs_path = f"{base_path}.{key}"
    if not refs_are_array:
        return []
    if require_nonempty and not refs:
        errors.append(f"{refs_path}: expected at least one source reference")

    referenced_source_ids: list[tuple[str, str]] = []
    for index, ref in enumerate(refs):
        path = f"{refs_path}[{index}]"
        if not isinstance(ref, dict):
            errors.append(f"{path}: expected an object")
            continue

        source_id = _require_nonempty_string(ref, "source_id", path, errors)
        if _is_nonempty_string(source_id):
            referenced_source_ids.append((f"{path}.source_id", source_id))
        _require_nonempty_string(ref, "locator", path, errors)
        _require_nonempty_string(ref, "evidence", path, errors)

        source_id_has_valid_shape = (
            isinstance(source_id, str) and SOURCE_ID_RE.fullmatch(source_id) is not None
        )
        if isinstance(source_id, str) and not source_id_has_valid_shape:
            errors.append(f"{path}.source_id: expected an ID matching SRC-[0-9]{{3,}}")
        elif (
            source_id_has_valid_shape
            and source_index_available
            and source_id not in valid_source_ids
        ):
            errors.append(f"{path}.source_id: unknown source ID {source_id!r}")
        elif (
            source_id_has_valid_shape
            and source_index_available
            and source_status_by_id.get(source_id) == "skipped"
        ):
            errors.append(
                f"{path}.source_id: source {source_id!r} has status 'skipped' "
                "and cannot supply evidence"
            )

        if "ocr" in ref:
            ocr = ref["ocr"]
            if type(ocr) is not bool:
                errors.append(f"{path}.ocr: expected a boolean")
            elif ocr:
                warnings.append(f"{path}.ocr: evidence was extracted with OCR")

    return referenced_source_ids


def _validate_string_list(
    obj: dict[str, Any],
    key: str,
    base_path: str,
    errors: list[str],
) -> tuple[list[str], bool]:
    values, values_are_array = _required_array(obj, key, base_path, errors)
    if not values_are_array:
        return [], False

    result: list[str] = []
    for index, value in enumerate(values):
        path = f"{base_path}.{key}[{index}]"
        if not _is_nonempty_string(value):
            errors.append(f"{path}: expected a non-empty string")
        else:
            result.append(value)
    return result, True


def _validate_source_id_list(
    obj: dict[str, Any],
    key: str,
    base_path: str,
    valid_source_ids: set[str],
    source_index_available: bool,
    errors: list[str],
) -> tuple[list[str], bool]:
    """Validate a required, duplicate-free list of source identifiers."""

    values, values_are_array = _required_array(obj, key, base_path, errors)
    if not values_are_array:
        return [], False

    result: list[str] = []
    first_index_by_id: dict[str, int] = {}
    for index, value in enumerate(values):
        path = f"{base_path}.{key}[{index}]"
        if not _is_nonempty_string(value):
            errors.append(f"{path}: expected a non-empty string")
            continue

        result.append(value)
        if value in first_index_by_id:
            errors.append(
                f"{path}: duplicate source ID {value!r}; first listed at "
                f"{base_path}.{key}[{first_index_by_id[value]}]"
            )
        else:
            first_index_by_id[value] = index

        if SOURCE_ID_RE.fullmatch(value) is None:
            errors.append(f"{path}: expected an ID matching SRC-[0-9]{{3,}}")
        elif source_index_available and value not in valid_source_ids:
            errors.append(f"{path}: unknown source ID {value!r}")

    return result, True


def _validate_sources(
    sources: list[Any], errors: list[str], warnings: list[str]
) -> tuple[set[str], dict[str, str]]:
    seen: dict[str, str] = {}
    valid_ids: set[str] = set()
    status_by_id: dict[str, str] = {}

    for index, source in enumerate(sources):
        path = f"$.sources[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{path}: expected an object")
            continue

        source_id = _validate_id(
            source,
            path,
            SOURCE_ID_RE,
            "SRC-[0-9]{3,}",
            seen,
            valid_ids,
            errors,
        )
        _require_nonempty_string(source, "name", path, errors)
        _require_nonempty_string(source, "media_type", path, errors)
        status = _require_enum(source, "status", SOURCE_STATUSES, path, errors)
        _require_nonempty_string(source, "locator_scheme", path, errors)

        if (
            isinstance(source_id, str)
            and SOURCE_ID_RE.fullmatch(source_id) is not None
            and status in SOURCE_STATUSES
            and source_id not in status_by_id
        ):
            status_by_id[source_id] = status

        if "path" in source and source["path"] is not None and not isinstance(
            source["path"], str
        ):
            errors.append(f"{path}.path: expected a string or null when present")
        if "notes" in source:
            notes = source["notes"]
            if not isinstance(notes, list):
                errors.append(f"{path}.notes: expected an array of strings when present")
            else:
                for note_index, note in enumerate(notes):
                    if not isinstance(note, str):
                        errors.append(
                            f"{path}.notes[{note_index}]: expected a string"
                        )
        if "digest_sha256" in source:
            digest = source["digest_sha256"]
            if digest is not None and (
                not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None
            ):
                errors.append(f"{path}.digest_sha256: expected 64 hexadecimal characters")

        if status == "partial":
            warnings.append(f"{path}.status: source is only partially processed")
        elif status == "skipped":
            warnings.append(f"{path}.status: source was skipped")

    return valid_ids, status_by_id


def _validate_context_items(
    context_items: list[Any],
    valid_source_ids: set[str],
    source_status_by_id: dict[str, str],
    source_index_available: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    seen: dict[str, str] = {}
    valid_ids: set[str] = set()

    for index, item in enumerate(context_items):
        path = f"$.context_items[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{path}: expected an object")
            continue

        _validate_id(
            item,
            path,
            CONTEXT_ID_RE,
            "CTX-[0-9]{4,}",
            seen,
            valid_ids,
            errors,
        )
        _require_enum(item, "type", CONTEXT_TYPES, path, errors)
        _require_nonempty_string(item, "text", path, errors)
        _validate_source_refs(
            item,
            "source_refs",
            path,
            valid_source_ids,
            source_status_by_id,
            source_index_available,
            errors,
            warnings,
            require_nonempty=True,
        )


def _index_requirements(
    requirements: list[Any], errors: list[str]
) -> tuple[set[str], dict[str, str]]:
    seen: dict[str, str] = {}
    valid_ids: set[str] = set()
    id_by_path: dict[str, str] = {}

    for index, requirement in enumerate(requirements):
        path = f"$.requirements[{index}]"
        if not isinstance(requirement, dict):
            errors.append(f"{path}: expected an object")
            continue
        requirement_id = _validate_id(
            requirement,
            path,
            REQUIREMENT_ID_RE,
            "REQ-[0-9]{6,}",
            seen,
            valid_ids,
            errors,
        )
        if (
            isinstance(requirement_id, str)
            and REQUIREMENT_ID_RE.fullmatch(requirement_id) is not None
        ):
            id_by_path[path] = requirement_id

    return valid_ids, id_by_path


def _validate_priority(
    requirement: dict[str, Any], path: str, errors: list[str], warnings: list[str]
) -> None:
    priority, priority_is_object = _required_object(requirement, "priority", path, errors)
    if not priority_is_object:
        return

    value = _require_nullable_string(priority, "value", f"{path}.priority", errors)
    basis = _require_nullable_string(priority, "basis", f"{path}.priority", errors)

    if not _is_nonempty_string(value):
        warnings.append(f"{path}.priority.value: priority is not recorded")
    elif not _is_nonempty_string(basis):
        errors.append(f"{path}.priority.basis: a non-empty basis is required when value is set")


def _validate_verification(
    requirement: dict[str, Any], path: str, errors: list[str], warnings: list[str]
) -> None:
    verification, verification_is_object = _required_object(
        requirement, "verification", path, errors
    )
    if not verification_is_object:
        return

    method = _require_nullable_string(
        verification, "method", f"{path}.verification", errors
    )
    acceptance_criteria = _require_nullable_string(
        verification, "acceptance_criteria", f"{path}.verification", errors
    )
    if not _is_nonempty_string(method):
        warnings.append(f"{path}.verification.method: verification method is not recorded")
    if not _is_nonempty_string(acceptance_criteria):
        warnings.append(
            f"{path}.verification.acceptance_criteria: acceptance criteria are not recorded"
        )


def _validate_requirements(
    requirements: list[Any],
    valid_requirement_ids: set[str],
    valid_source_ids: set[str],
    source_status_by_id: dict[str, str],
    source_index_available: bool,
    errors: list[str],
    warnings: list[str],
) -> tuple[
    dict[str, int],
    list[tuple[str, str]],
    dict[str, dict[str, Any]],
]:
    active_by_level = {level: 0 for level in LEVELS}
    pending_issue_refs: list[tuple[str, str]] = []
    details_by_requirement: dict[str, dict[str, Any]] = {}

    for index, requirement in enumerate(requirements):
        path = f"$.requirements[{index}]"
        if not isinstance(requirement, dict):
            continue

        requirement_id = requirement.get("id")
        level = _require_enum(requirement, "level", LEVELS, path, errors)
        _require_enum(requirement, "category", REQUIREMENT_CATEGORIES, path, errors)
        _require_nonempty_string(requirement, "statement", path, errors)
        _validate_source_refs(
            requirement,
            "source_refs",
            path,
            valid_source_ids,
            source_status_by_id,
            source_index_available,
            errors,
            warnings,
            require_nonempty=True,
        )
        provenance = _require_enum(
            requirement, "provenance", PROVENANCE_VALUES, path, errors
        )
        confidence = _require_enum(
            requirement, "confidence", CONFIDENCE_VALUES, path, errors
        )

        rationale = _require_nullable_string(requirement, "rationale", path, errors)
        if "rationale" in requirement and not _is_nonempty_string(rationale):
            warnings.append(f"{path}.rationale: rationale is not recorded")

        stakeholders, stakeholders_are_array = _validate_string_list(
            requirement, "stakeholders", path, errors
        )
        if stakeholders_are_array and not stakeholders:
            warnings.append(f"{path}.stakeholders: no stakeholders are recorded")

        _validate_priority(requirement, path, errors, warnings)
        _validate_verification(requirement, path, errors, warnings)
        quality_status = _require_enum(
            requirement, "quality_status", QUALITY_STATUSES, path, errors
        )
        disposition = _require_enum(
            requirement, "disposition", DISPOSITIONS, path, errors
        )
        if "status" in requirement:
            errors.append(
                f"{path}.status: legacy field is not allowed; use quality_status "
                "and disposition"
            )
        decision_basis = _require_nullable_string(
            requirement, "decision_basis", path, errors
        )
        superseded_by, superseded_by_is_valid = _require_nullable_id(
            requirement,
            "superseded_by",
            REQUIREMENT_ID_RE,
            "REQ-[0-9]{6,}",
            path,
            errors,
        )

        for field in RELATIONSHIP_FIELDS_IN_REQUIREMENT:
            if field in requirement:
                errors.append(
                    f"{path}.{field}: relationship data must appear only in $.relationships"
                )

        findings, findings_are_array = _required_array(
            requirement, "quality_findings", path, errors
        )
        has_blocking_finding = False
        blocking_finding_codes: set[str] = set()
        if findings_are_array:
            for finding_index, finding in enumerate(findings):
                finding_path = f"{path}.quality_findings[{finding_index}]"
                if not isinstance(finding, dict):
                    errors.append(f"{finding_path}: expected an object")
                    continue

                code = _require_enum(
                    finding, "code", QUALITY_CODES, finding_path, errors
                )
                severity = _require_enum(
                    finding, "severity", FINDING_SEVERITIES, finding_path, errors
                )
                message = _require_nonempty_string(
                    finding, "message", finding_path, errors
                )
                issue_id, issue_id_is_valid = _require_nullable_id(
                    finding,
                    "issue_id",
                    ISSUE_ID_RE,
                    "ISS-[0-9]{4,}",
                    finding_path,
                    errors,
                )
                if issue_id_is_valid and issue_id is not None:
                    pending_issue_refs.append((f"{finding_path}.issue_id", issue_id))

                if severity == "blocking":
                    has_blocking_finding = True
                    if code in QUALITY_CODES:
                        blocking_finding_codes.add(code)
                if severity == "blocking" and quality_status == "normalized":
                    errors.append(
                        f"{finding_path}.severity: blocking finding is incompatible "
                        "with quality_status 'normalized'"
                    )
                if severity in FINDING_SEVERITIES:
                    finding_label = code if isinstance(code, str) else "quality"
                    finding_message = message.strip() if _is_nonempty_string(message) else ""
                    warnings.append(
                        f"{finding_path}: {severity} {finding_label} finding"
                        + (f": {finding_message}" if finding_message else "")
                    )

        if (
            quality_status == "needs-review"
            and findings_are_array
            and not has_blocking_finding
        ):
            errors.append(
                f"{path}.quality_status: needs-review requires at least one blocking "
                "quality finding"
            )

        if confidence == "low":
            warnings.append(f"{path}.confidence: requirement confidence is low")

        if provenance == "inferred" and quality_status != "needs-review":
            errors.append(
                f"{path}.quality_status: inferred requirement must be needs-review"
            )

        if disposition in ("accepted", "rejected", "superseded") and not _is_nonempty_string(decision_basis):
            errors.append(
                f"{path}.decision_basis: a non-empty decision basis is required "
                f"for disposition {disposition!r}"
            )
        elif disposition == "proposed" and decision_basis is not None:
            errors.append(
                f"{path}.decision_basis: must be null for disposition 'proposed'"
            )

        if disposition == "superseded" and superseded_by_is_valid:
            superseded_path = f"{path}.superseded_by"
            if superseded_by is None:
                errors.append(
                    f"{superseded_path}: a replacement requirement ID is required"
                )
            elif superseded_by not in valid_requirement_ids:
                errors.append(
                    f"{superseded_path}: unknown requirement ID {superseded_by!r}"
                )
            elif superseded_by == requirement_id:
                errors.append(f"{superseded_path}: requirement cannot supersede itself")
        elif (
            disposition in DISPOSITIONS
            and disposition != "superseded"
            and superseded_by_is_valid
            and superseded_by is not None
        ):
            errors.append(
                f"{path}.superseded_by: must be null unless disposition is 'superseded'"
            )

        if level in LEVELS and disposition in ("proposed", "accepted"):
            active_by_level[level] += 1

        if (
            isinstance(requirement_id, str)
            and REQUIREMENT_ID_RE.fullmatch(requirement_id) is not None
            and requirement_id not in details_by_requirement
        ):
            details_by_requirement[requirement_id] = {
                "quality_status": quality_status,
                "disposition": disposition,
                "blocking_finding_codes": blocking_finding_codes,
            }

    return active_by_level, pending_issue_refs, details_by_requirement


def _validate_relationships(
    relationships: list[Any],
    valid_requirement_ids: set[str],
    requirement_index_available: bool,
    errors: list[str],
) -> tuple[list[tuple[str, str]], list[dict[str, Any]]]:
    seen_ids: dict[str, str] = {}
    valid_ids: set[str] = set()
    seen_edges: dict[tuple[str, str, str], str] = {}
    pending_issue_refs: list[tuple[str, str]] = []
    conflict_relationships: list[dict[str, Any]] = []

    for index, relationship in enumerate(relationships):
        path = f"$.relationships[{index}]"
        if not isinstance(relationship, dict):
            errors.append(f"{path}: expected an object")
            continue

        _validate_id(
            relationship,
            path,
            RELATIONSHIP_ID_RE,
            "REL-[0-9]{4,}",
            seen_ids,
            valid_ids,
            errors,
        )
        relationship_type = _require_enum(
            relationship, "type", RELATIONSHIP_TYPES, path, errors
        )
        from_id = _require_nonempty_string(relationship, "from_id", path, errors)
        to_id = _require_nonempty_string(relationship, "to_id", path, errors)
        _require_nonempty_string(relationship, "basis", path, errors)
        issue_id, issue_id_is_valid = _require_nullable_id(
            relationship,
            "issue_id",
            ISSUE_ID_RE,
            "ISS-[0-9]{4,}",
            path,
            errors,
        )
        if issue_id_is_valid and issue_id is not None:
            pending_issue_refs.append((f"{path}.issue_id", issue_id))
        if relationship_type == "conflicts-with":
            if issue_id_is_valid and issue_id is None:
                errors.append(
                    f"{path}.issue_id: a conflict issue ID is required for "
                    "a conflicts-with relationship"
                )
            conflict_relationships.append(
                {
                    "path": path,
                    "from_id": from_id,
                    "to_id": to_id,
                    "issue_id": issue_id if issue_id_is_valid else None,
                }
            )

        endpoints: list[tuple[str, Any]] = [("from_id", from_id), ("to_id", to_id)]
        endpoint_shapes_valid = True
        for field, endpoint in endpoints:
            endpoint_path = f"{path}.{field}"
            if not isinstance(endpoint, str) or REQUIREMENT_ID_RE.fullmatch(endpoint) is None:
                if isinstance(endpoint, str) and endpoint.strip():
                    errors.append(
                        f"{endpoint_path}: expected an ID matching REQ-[0-9]{{6,}}"
                    )
                endpoint_shapes_valid = False
            elif requirement_index_available and endpoint not in valid_requirement_ids:
                errors.append(f"{endpoint_path}: unknown requirement ID {endpoint!r}")
                endpoint_shapes_valid = False

        if isinstance(from_id, str) and isinstance(to_id, str) and from_id == to_id:
            errors.append(f"{path}.to_id: relationship endpoints must be distinct")
            endpoint_shapes_valid = False

        if relationship_type in RELATIONSHIP_TYPES and endpoint_shapes_valid:
            if relationship_type in ("conflicts-with", "duplicates"):
                endpoint_a, endpoint_b = sorted((from_id, to_id))
            else:
                endpoint_a, endpoint_b = from_id, to_id
            edge = (relationship_type, endpoint_a, endpoint_b)
            if edge in seen_edges:
                errors.append(
                    f"{path}: duplicate relationship edge; first declared at {seen_edges[edge]}"
                )
            else:
                seen_edges[edge] = path

    return pending_issue_refs, conflict_relationships


def _validate_issues(
    issues: list[Any],
    valid_source_ids: set[str],
    source_status_by_id: dict[str, str],
    source_index_available: bool,
    valid_requirement_ids: set[str],
    requirement_index_available: bool,
    errors: list[str],
    warnings: list[str],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    seen: dict[str, str] = {}
    valid_ids: set[str] = set()
    details_by_issue: dict[str, dict[str, Any]] = {}

    for index, issue in enumerate(issues):
        path = f"$.issues[{index}]"
        if not isinstance(issue, dict):
            errors.append(f"{path}: expected an object")
            continue

        issue_id = _validate_id(
            issue,
            path,
            ISSUE_ID_RE,
            "ISS-[0-9]{4,}",
            seen,
            valid_ids,
            errors,
        )
        issue_type = _require_enum(issue, "type", ISSUE_TYPES, path, errors)
        severity = _require_enum(
            issue, "severity", ISSUE_SEVERITIES, path, errors
        )
        status = _require_enum(issue, "status", ISSUE_STATUSES, path, errors)
        _require_nonempty_string(issue, "message", path, errors)
        source_ids, source_ids_are_array = _validate_source_id_list(
            issue,
            "source_ids",
            path,
            valid_source_ids,
            source_index_available,
            errors,
        )
        source_id_set = set(source_ids)
        evidence_source_refs = _validate_source_refs(
            issue,
            "source_refs",
            path,
            valid_source_ids,
            source_status_by_id,
            source_index_available,
            errors,
            warnings,
            require_nonempty=False,
        )
        if source_ids_are_array:
            for ref_path, source_id in evidence_source_refs:
                if source_id not in source_id_set:
                    errors.append(
                        f"{ref_path}: source {source_id!r} must also appear in "
                        f"{path}.source_ids"
                    )

        if issue_type == "unreadable-source" and source_ids_are_array:
            unreadable_targets = [
                source_id
                for source_id in source_id_set
                if source_status_by_id.get(source_id) in ("partial", "skipped")
            ]
            if not unreadable_targets:
                errors.append(
                    f"{path}.source_ids: an unreadable-source issue must target "
                    "at least one source whose status is 'partial' or 'skipped'"
                )

        requirement_ids, requirement_ids_are_array = _validate_string_list(
            issue, "requirement_ids", path, errors
        )
        if requirement_ids_are_array:
            first_requirement_index: dict[str, int] = {}
            for requirement_index, requirement_id in enumerate(requirement_ids):
                ref_path = f"{path}.requirement_ids[{requirement_index}]"
                if requirement_id in first_requirement_index:
                    errors.append(
                        f"{ref_path}: duplicate requirement ID {requirement_id!r}; "
                        f"first listed at {path}.requirement_ids["
                        f"{first_requirement_index[requirement_id]}]"
                    )
                else:
                    first_requirement_index[requirement_id] = requirement_index
                if REQUIREMENT_ID_RE.fullmatch(requirement_id) is None:
                    errors.append(
                        f"{ref_path}: expected an ID matching REQ-[0-9]{{6,}}"
                    )
                elif (
                    requirement_index_available
                    and requirement_id not in valid_requirement_ids
                ):
                    errors.append(f"{ref_path}: unknown requirement ID {requirement_id!r}")

        affected_levels, affected_levels_are_array = _validate_string_list(
            issue, "affected_levels", path, errors
        )
        valid_affected_levels: set[str] = set()
        if affected_levels_are_array:
            first_level_index: dict[str, int] = {}
            for level_index, level in enumerate(affected_levels):
                ref_path = f"{path}.affected_levels[{level_index}]"
                if level in first_level_index:
                    errors.append(
                        f"{ref_path}: duplicate level {level!r}; first listed at "
                        f"{path}.affected_levels[{first_level_index[level]}]"
                    )
                else:
                    first_level_index[level] = level_index
                if level not in LEVELS:
                    expected = ", ".join(LEVELS)
                    errors.append(
                        f"{ref_path}: expected one of [{expected}]"
                    )
                else:
                    valid_affected_levels.add(level)

        if (
            isinstance(issue_id, str)
            and ISSUE_ID_RE.fullmatch(issue_id) is not None
            and issue_id not in details_by_issue
        ):
            details_by_issue[issue_id] = {
                "type": issue_type,
                "status": status,
                "affected_levels": valid_affected_levels,
                "requirement_ids": set(requirement_ids),
                "source_ids": source_id_set,
            }

        if status == "resolved":
            if "resolution" not in issue:
                errors.append(f"{path}.resolution: required for a resolved issue")
            elif not _is_nonempty_string(issue["resolution"]):
                errors.append(
                    f"{path}.resolution: expected a non-empty string for a resolved issue"
                )
        elif status == "open":
            if "resolution" not in issue:
                errors.append(f"{path}.resolution: required field is missing")
            elif issue["resolution"] is not None:
                errors.append(f"{path}.resolution: must be null for an open issue")

        if status == "open":
            issue_label = issue_id if isinstance(issue_id, str) else f"index {index}"
            severity_label = severity if severity in ISSUE_SEVERITIES else "unknown-severity"
            type_label = issue_type if issue_type in ISSUE_TYPES else "issue"
            warnings.append(
                f"{path}.status: open {severity_label} {type_label} {issue_label!r}"
            )

    return valid_ids, details_by_issue


def _validate_issue_refs(
    pending_refs: list[tuple[str, str]],
    valid_issue_ids: set[str],
    issue_index_available: bool,
    errors: list[str],
) -> None:
    for path, issue_id in pending_refs:
        if issue_index_available and issue_id not in valid_issue_ids:
            errors.append(f"{path}: unknown issue ID {issue_id!r}")


def _validate_conflict_relationships(
    conflict_relationships: list[dict[str, Any]],
    issue_details_by_id: dict[str, dict[str, Any]],
    issue_index_available: bool,
    requirement_details_by_id: dict[str, dict[str, Any]],
    requirement_index_available: bool,
    errors: list[str],
) -> None:
    """Validate the issue and quality semantics of conflicts-with edges."""

    for relationship in conflict_relationships:
        path = relationship["path"]
        issue_id = relationship.get("issue_id")
        from_id = relationship.get("from_id")
        to_id = relationship.get("to_id")

        if not isinstance(issue_id, str) or ISSUE_ID_RE.fullmatch(issue_id) is None:
            continue
        if not issue_index_available or issue_id not in issue_details_by_id:
            continue

        issue_details = issue_details_by_id[issue_id]
        if issue_details.get("type") != "conflict":
            errors.append(
                f"{path}.issue_id: linked issue {issue_id!r} must have type 'conflict'"
            )

        linked_requirement_ids = issue_details.get("requirement_ids", set())
        for endpoint_field, endpoint_id in (
            ("from_id", from_id),
            ("to_id", to_id),
        ):
            if (
                isinstance(endpoint_id, str)
                and REQUIREMENT_ID_RE.fullmatch(endpoint_id) is not None
                and endpoint_id not in linked_requirement_ids
            ):
                errors.append(
                    f"{path}.issue_id: linked issue {issue_id!r} must include "
                    f"{endpoint_field} {endpoint_id!r} in requirement_ids"
                )

        if issue_details.get("status") != "open":
            continue

        for endpoint_field, endpoint_id in (
            ("from_id", from_id),
            ("to_id", to_id),
        ):
            if (
                not isinstance(endpoint_id, str)
                or REQUIREMENT_ID_RE.fullmatch(endpoint_id) is None
                or not requirement_index_available
                or endpoint_id not in requirement_details_by_id
            ):
                continue
            blocking_codes = requirement_details_by_id[endpoint_id].get(
                "blocking_finding_codes", set()
            )
            if "conflicting" not in blocking_codes:
                errors.append(
                    f"{path}.{endpoint_field}: requirement {endpoint_id!r} must "
                    "have a blocking quality finding with code 'conflicting' "
                    f"while linked issue {issue_id!r} is open"
                )


def _validate_level_coverage(
    coverage: dict[str, Any],
    active_by_level: dict[str, int],
    valid_issue_ids: set[str],
    issue_details_by_id: dict[str, dict[str, Any]],
    issue_index_available: bool,
    errors: list[str],
    warnings: list[str],
) -> None:
    expected_keys = set(LEVELS)
    actual_keys = set(coverage)
    for level in LEVELS:
        if level not in actual_keys:
            errors.append(f"$.level_coverage.{level}: required level entry is missing")
    for extra_key in sorted(actual_keys - expected_keys, key=str):
        errors.append(f"$.level_coverage[{extra_key!r}]: unexpected level entry")

    for level in LEVELS:
        if level not in coverage:
            continue
        entry_path = f"$.level_coverage.{level}"
        entry = coverage[level]
        if not isinstance(entry, dict):
            errors.append(f"{entry_path}: expected an object")
            continue

        status = _require_enum(entry, "status", COVERAGE_STATUSES, entry_path, errors)
        _require_nonempty_string(entry, "basis", entry_path, errors)
        issue_id, issue_id_is_valid = _require_nullable_id(
            entry,
            "issue_id",
            ISSUE_ID_RE,
            "ISS-[0-9]{4,}",
            entry_path,
            errors,
        )
        active_count = active_by_level.get(level, 0)

        if status == "supported" and active_count == 0:
            errors.append(
                f"{entry_path}.status: supported level has no active requirements"
            )
        elif status in ("gap", "not-applicable") and active_count != 0:
            errors.append(
                f"{entry_path}.status: {status} level has {active_count} active requirement(s)"
            )

        if status == "gap":
            warnings.append(f"{entry_path}.status: requirements coverage gap is recorded")
            if issue_id_is_valid and issue_id is None:
                errors.append(f"{entry_path}.issue_id: a gap issue ID is required")
            elif (
                issue_id_is_valid
                and issue_id is not None
                and issue_index_available
                and issue_id not in valid_issue_ids
            ):
                errors.append(f"{entry_path}.issue_id: unknown issue ID {issue_id!r}")
            elif (
                issue_id_is_valid
                and issue_id is not None
                and issue_index_available
                and issue_id in issue_details_by_id
            ):
                details = issue_details_by_id[issue_id]
                issue_type = details.get("type")
                issue_status = details.get("status")
                affected_levels = details.get("affected_levels", set())
                if issue_type in ISSUE_TYPES and issue_type != "gap":
                    errors.append(
                        f"{entry_path}.issue_id: issue {issue_id!r} must have type 'gap'"
                    )
                if issue_status in ISSUE_STATUSES and issue_status != "open":
                    errors.append(
                        f"{entry_path}.issue_id: issue {issue_id!r} must be open"
                    )
                if level not in affected_levels:
                    errors.append(
                        f"{entry_path}.issue_id: issue {issue_id!r} does not affect "
                        f"level {level}"
                    )
        elif (
            status in COVERAGE_STATUSES
            and issue_id_is_valid
            and issue_id is not None
        ):
            errors.append(
                f"{entry_path}.issue_id: must be null unless status is 'gap'"
            )


def validate_document(data: Any) -> tuple[list[str], list[str]]:
    """Return deterministic ``(errors, warnings)`` for a requirements document."""

    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(data, dict):
        return ["$: expected an object"], warnings

    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"$.schema_version: expected exactly {SCHEMA_VERSION!r}")
    if data.get("profile") != PROFILE:
        errors.append(f"$.profile: expected exactly {PROFILE!r}")
    _require_nonempty_string(data, "title", "$", errors)
    _require_nonempty_string(data, "language", "$", errors)
    if "generated_at" in data:
        generated_at = data["generated_at"]
        generated_at_is_valid = isinstance(generated_at, str) and "T" in generated_at
        if generated_at_is_valid:
            try:
                datetime.fromisoformat(generated_at)
            except ValueError:
                generated_at_is_valid = False
        if not generated_at_is_valid:
            errors.append(
                "$.generated_at: expected an ISO 8601 date-time string"
            )

    sources, sources_are_array = _required_array(data, "sources", "$", errors)
    coverage, coverage_is_object = _required_object(
        data, "level_coverage", "$", errors
    )
    context_items, context_items_are_array = _required_array(
        data, "context_items", "$", errors
    )
    requirements, requirements_are_array = _required_array(
        data, "requirements", "$", errors
    )
    relationships, relationships_are_array = _required_array(
        data, "relationships", "$", errors
    )
    issues, issues_are_array = _required_array(data, "issues", "$", errors)

    valid_source_ids, source_status_by_id = _validate_sources(
        sources, errors, warnings
    )

    if context_items_are_array:
        _validate_context_items(
            context_items,
            valid_source_ids,
            source_status_by_id,
            sources_are_array,
            errors,
            warnings,
        )

    valid_requirement_ids, _ = _index_requirements(requirements, errors)
    (
        active_by_level,
        pending_finding_issue_refs,
        requirement_details_by_id,
    ) = _validate_requirements(
        requirements,
        valid_requirement_ids,
        valid_source_ids,
        source_status_by_id,
        sources_are_array,
        errors,
        warnings,
    )

    pending_relationship_issue_refs: list[tuple[str, str]] = []
    conflict_relationships: list[dict[str, Any]] = []
    if relationships_are_array:
        (
            pending_relationship_issue_refs,
            conflict_relationships,
        ) = _validate_relationships(
            relationships,
            valid_requirement_ids,
            requirements_are_array,
            errors,
        )

    valid_issue_ids, issue_details_by_id = _validate_issues(
        issues,
        valid_source_ids,
        source_status_by_id,
        sources_are_array,
        valid_requirement_ids,
        requirements_are_array,
        errors,
        warnings,
    )
    _validate_issue_refs(
        pending_finding_issue_refs + pending_relationship_issue_refs,
        valid_issue_ids,
        issues_are_array,
        errors,
    )
    _validate_conflict_relationships(
        conflict_relationships,
        issue_details_by_id,
        issues_are_array,
        requirement_details_by_id,
        requirements_are_array,
        errors,
    )

    if coverage_is_object:
        _validate_level_coverage(
            coverage,
            active_by_level,
            valid_issue_ids,
            issue_details_by_id,
            issues_are_array,
            errors,
            warnings,
        )

    return errors, warnings


class _DuplicateJSONKey(ValueError):
    pass


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateJSONKey(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _print_result(errors: list[str], warnings: list[str], as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                {"valid": not errors, "errors": errors, "warnings": warnings},
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
        )
        return

    if errors:
        print("Validation errors:")
        for error in errors:
            print(f"- {error}")
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"- {warning}")
    if not errors and not warnings:
        print("Document is structurally valid.")
    elif not errors:
        print("Document is structurally valid with warnings.")


def _configure_console() -> None:
    """Use deterministic UTF-8 output for multilingual evidence and diagnostics."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (AttributeError, OSError, ValueError):
            pass


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a canonical ISO 29148 public-principles JSON document."
    )
    parser.add_argument("path", type=Path, help="path to the JSON document")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="json_output",
        help="emit machine-readable validation results",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_console()
    args = _build_argument_parser().parse_args(argv)
    try:
        with args.path.open("r", encoding="utf-8-sig") as stream:
            data = json.load(
                stream,
                object_pairs_hook=_reject_duplicate_json_keys,
                parse_constant=_reject_json_constant,
            )
    except json.JSONDecodeError as exc:
        errors = [
            f"$: invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ]
        _print_result(errors, [], args.json_output)
        return 2
    except (_DuplicateJSONKey, ValueError) as exc:
        _print_result([f"$: invalid JSON: {exc}"], [], args.json_output)
        return 2
    except UnicodeError:
        _print_result(["$: input is not valid UTF-8"], [], args.json_output)
        return 2
    except OSError as exc:
        _print_result([f"$: unable to read {str(args.path)!r}: {exc.strerror or 'I/O error'}"], [], args.json_output)
        return 2

    errors, warnings = validate_document(data)
    _print_result(errors, warnings, args.json_output)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
