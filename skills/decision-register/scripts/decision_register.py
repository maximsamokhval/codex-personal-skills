#!/usr/bin/env python3
"""Draft, validate and render a requirements-bound decision register."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from pipeline_artifacts import (
    ArtifactError,
    load_json,
    sha256,
    validate_requirements,
    validate_review,
)

SCHEMA_VERSION = "requirements-decision-register/v1"
DISPOSITIONS = {
    "pending",
    "provisional",
    "adopted",
    "accepted-risk",
    "rejected",
    "deferred",
}
ROOT_KEYS = {
    "schema_version",
    "requirements_path",
    "requirements_sha256",
    "review_path",
    "review_sha256",
    "scope",
    "source_clauses",
    "requirement_owners",
    "open_item_owners",
}
SOURCE_KEYS = {
    "source_clause_id",
    "requirement_ids",
    "source_refs",
    "disposition",
    "decision_owner",
    "decision_ref",
    "rationale",
    "provisional_rule",
    "review_trigger",
    "verification",
}
REQUIREMENT_OWNER_KEYS = {
    "requirement_id",
    "feature_id",
    "feature_owner",
    "assignment_ref",
}
OPEN_OWNER_KEYS = {
    "open_item_id",
    "requirements_status",
    "feature_id",
    "decision_owner",
    "assignment_ref",
    "decision_ref",
    "provisional_rule",
    "review_trigger",
}


def _keys(value: Any, expected: set[str], where: str, errors: list[str]) -> bool:
    if not isinstance(value, dict):
        errors.append(f"{where}: expected an object")
        return False
    for key in sorted(expected - value.keys()):
        errors.append(f"{where}.{key}: missing")
    for key in sorted(value.keys() - expected):
        errors.append(f"{where}.{key}: unexpected")
    return True


def _text(value: Any, where: str, errors: list[str], nullable: bool = False) -> None:
    if nullable and value is None:
        return
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{where}: expected non-empty text{' or null' if nullable else ''}")


def _ids(value: Any, where: str, known: set[str], errors: list[str]) -> set[str]:
    if not isinstance(value, list):
        errors.append(f"{where}: expected an array")
        return set()
    seen: set[str] = set()
    for index, item in enumerate(value):
        if not isinstance(item, str) or item not in known:
            errors.append(f"{where}[{index}]: unknown ID {item!r}")
        elif item in seen:
            errors.append(f"{where}[{index}]: duplicate ID {item!r}")
        else:
            seen.add(item)
    return seen


def _exact(actual: set[str], expected: set[str], where: str, errors: list[str]) -> None:
    for item in sorted(expected - actual):
        errors.append(f"{where}: missing {item}")
    for item in sorted(actual - expected):
        errors.append(f"{where}: unexpected {item}")


def _source_ids(requirement: dict[str, Any]) -> list[str]:
    attrs = requirement.get("attributes", {})
    result: list[str] = []
    one = attrs.get("source_id")
    many = attrs.get("source_ids", [])
    if one is not None:
        if not isinstance(one, str) or not one.strip():
            raise ArtifactError(f"{requirement['id']}.attributes.source_id: invalid")
        result.append(one)
    if not isinstance(many, list) or any(
        not isinstance(item, str) or not item.strip() for item in many
    ):
        raise ArtifactError(f"{requirement['id']}.attributes.source_ids: invalid")
    result.extend(many)
    if len(result) != len(set(result)):
        raise ArtifactError(f"{requirement['id']}: duplicate source clause ID")
    return result


def _source_map(
    requirements: dict[str, Any], selected: set[str]
) -> dict[str, dict[str, set[str]]]:
    result: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: {"requirement_ids": set(), "source_refs": set()}
    )
    for requirement in requirements["requirements"]:
        if requirement["id"] not in selected:
            continue
        clause_ids = _source_ids(requirement)
        refs = requirement["source_refs"]
        if len(clause_ids) > 1 and len(clause_ids) != len(refs):
            raise ArtifactError(
                f"{requirement['id']}: multiple source clauses need one ordered source_ref each"
            )
        for index, source_id in enumerate(clause_ids):
            result[source_id]["requirement_ids"].add(requirement["id"])
            result[source_id]["source_refs"].update(
                [refs[index]] if len(clause_ids) > 1 else refs
            )
    return dict(result)


def _load_inputs(
    requirements_path: Path, review_path: Path
) -> tuple[dict[str, Any], dict[str, Any]]:
    requirements = load_json(requirements_path)
    errors = validate_requirements(requirements)
    if errors:
        raise ArtifactError(f"{requirements_path}: " + "\n".join(errors))
    review = load_json(review_path)
    known = {item["id"] for item in requirements["requirements"]}
    known.update(item["id"] for item in requirements["open_items"])
    errors = validate_review(review, known)
    if errors:
        raise ArtifactError(f"{review_path}: " + "\n".join(errors))
    if review["requirements_sha256"] != sha256(requirements_path):
        raise ArtifactError(f"{review_path}: requirements_sha256 does not match")
    return requirements, review


def draft(
    requirements_path: Path,
    review_path: Path,
    requirement_pattern: str,
    open_pattern: str,
    output: Path,
) -> None:
    if output.exists():
        raise ArtifactError(f"{output}: already exists")
    requirements, _ = _load_inputs(requirements_path, review_path)
    try:
        requirement_re = re.compile(requirement_pattern)
        open_re = re.compile(open_pattern)
    except re.error as exc:
        raise ArtifactError(f"invalid scope regex: {exc}") from exc
    selected_requirements = sorted(
        item["id"]
        for item in requirements["requirements"]
        if requirement_re.fullmatch(item["id"])
    )
    selected_open = sorted(
        item["id"]
        for item in requirements["open_items"]
        if open_re.fullmatch(item["id"])
    )
    if not selected_requirements and not selected_open:
        raise ArtifactError("scope matched no requirements or open items")
    source_map = _source_map(requirements, set(selected_requirements))
    open_by_id = {item["id"]: item for item in requirements["open_items"]}
    source_ids = sorted(source_map)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "requirements_path": str(requirements_path),
        "requirements_sha256": sha256(requirements_path),
        "review_path": str(review_path),
        "review_sha256": sha256(review_path),
        "scope": {
            "requirement_ids": selected_requirements,
            "open_item_ids": selected_open,
            "source_clause_ids": source_ids,
        },
        "source_clauses": [
            {
                "source_clause_id": source_id,
                "requirement_ids": sorted(source_map[source_id]["requirement_ids"]),
                "source_refs": sorted(source_map[source_id]["source_refs"]),
                "disposition": "pending",
                "decision_owner": None,
                "decision_ref": None,
                "rationale": None,
                "provisional_rule": None,
                "review_trigger": None,
                "verification": None,
            }
            for source_id in source_ids
        ],
        "requirement_owners": [
            {
                "requirement_id": requirement_id,
                "feature_id": None,
                "feature_owner": None,
                "assignment_ref": None,
            }
            for requirement_id in selected_requirements
        ],
        "open_item_owners": [
            {
                "open_item_id": open_item_id,
                "requirements_status": open_by_id[open_item_id]["status"],
                "feature_id": None,
                "decision_owner": None,
                "assignment_ref": None,
                "decision_ref": None,
                "provisional_rule": None,
                "review_trigger": None,
            }
            for open_item_id in selected_open
        ],
    }
    _validate_payload(payload, requirements, requirements_path, review_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE {output}: {len(source_ids)} clauses, "
        f"{len(selected_requirements)} requirements, {len(selected_open)} OPEN"
    )


def _validate_payload(
    data: dict[str, Any],
    requirements: dict[str, Any],
    requirements_path: Path,
    review_path: Path,
) -> None:
    errors: list[str] = []
    _keys(data, ROOT_KEYS, "$", errors)
    if data.get("schema_version") != SCHEMA_VERSION:
        errors.append("$.schema_version: unsupported version")
    for field, path in (("requirements", requirements_path), ("review", review_path)):
        _text(data.get(f"{field}_path"), f"$.{field}_path", errors)
        if data.get(f"{field}_path") != str(path):
            errors.append(f"$.{field}_path: does not match input path")
        if data.get(f"{field}_sha256") != sha256(path):
            errors.append(f"$.{field}_sha256: does not match input bytes")
    scope = data.get("scope")
    if not _keys(
        scope, {"requirement_ids", "open_item_ids", "source_clause_ids"}, "$.scope", errors
    ):
        scope = {}
    requirements_by_id = {item["id"]: item for item in requirements["requirements"]}
    open_by_id = {item["id"]: item for item in requirements["open_items"]}
    requirement_ids = _ids(
        scope.get("requirement_ids"), "$.scope.requirement_ids", set(requirements_by_id), errors
    )
    open_ids = _ids(
        scope.get("open_item_ids"), "$.scope.open_item_ids", set(open_by_id), errors
    )
    source_map = _source_map(requirements, requirement_ids)
    source_ids = _ids(
        scope.get("source_clause_ids"), "$.scope.source_clause_ids", set(source_map), errors
    )
    _exact(source_ids, set(source_map), "$.scope.source_clause_ids", errors)

    clauses = data.get("source_clauses")
    if not isinstance(clauses, list):
        errors.append("$.source_clauses: expected an array")
        clauses = []
    seen_clauses: set[str] = set()
    for index, clause in enumerate(clauses):
        where = f"$.source_clauses[{index}]"
        if not _keys(clause, SOURCE_KEYS, where, errors):
            continue
        source_id = clause.get("source_clause_id")
        if not isinstance(source_id, str) or source_id not in source_map:
            errors.append(f"{where}.source_clause_id: unknown source clause {source_id!r}")
            continue
        if source_id in seen_clauses:
            errors.append(f"{where}.source_clause_id: duplicate {source_id}")
        seen_clauses.add(source_id)
        linked_ids = _ids(
            clause.get("requirement_ids"), f"{where}.requirement_ids", requirement_ids, errors
        )
        _exact(linked_ids, source_map[source_id]["requirement_ids"], f"{where}.requirement_ids", errors)
        refs = _ids(
            clause.get("source_refs"), f"{where}.source_refs", source_map[source_id]["source_refs"], errors
        )
        _exact(refs, source_map[source_id]["source_refs"], f"{where}.source_refs", errors)
        status = clause.get("disposition")
        if not isinstance(status, str) or status not in DISPOSITIONS:
            errors.append(f"{where}.disposition: invalid")
        for field in (
            "decision_owner", "decision_ref", "rationale", "provisional_rule", "review_trigger", "verification"
        ):
            _text(clause.get(field), f"{where}.{field}", errors, nullable=True)
        if status != "pending":
            for field in ("decision_owner", "decision_ref", "rationale"):
                if clause.get(field) is None:
                    errors.append(f"{where}.{field}: required for {status}")
        if status in {"provisional", "accepted-risk", "deferred"} and clause.get("review_trigger") is None:
            errors.append(f"{where}.review_trigger: required for {status}")
        if status == "provisional" and clause.get("provisional_rule") is None:
            errors.append(f"{where}.provisional_rule: required for provisional")
        if status == "adopted" and clause.get("verification") is None:
            errors.append(f"{where}.verification: required for adopted")
    _exact(seen_clauses, source_ids, "$.source_clauses", errors)

    for field, key, selected, expected_keys, assignment_fields in (
        (
            "requirement_owners", "requirement_id", requirement_ids,
            REQUIREMENT_OWNER_KEYS, ("feature_id", "feature_owner", "assignment_ref"),
        ),
        (
            "open_item_owners", "open_item_id", open_ids,
            OPEN_OWNER_KEYS, ("feature_id", "decision_owner", "assignment_ref"),
        ),
    ):
        rows = data.get(field)
        if not isinstance(rows, list):
            errors.append(f"$.{field}: expected an array")
            rows = []
        seen: set[str] = set()
        for index, row in enumerate(rows):
            where = f"$.{field}[{index}]"
            if not _keys(row, expected_keys, where, errors):
                continue
            target = row.get(key)
            if not isinstance(target, str) or target not in selected:
                errors.append(f"{where}.{key}: unknown scoped ID {target!r}")
                continue
            if target in seen:
                errors.append(f"{where}.{key}: duplicate {target}")
            seen.add(target)
            for assignment_field in assignment_fields:
                _text(row.get(assignment_field), f"{where}.{assignment_field}", errors, nullable=True)
            if any(row.get(name) is not None for name in assignment_fields[:-1]) and row.get("assignment_ref") is None:
                errors.append(f"{where}.assignment_ref: required for an assignment")
            if field == "open_item_owners":
                if row.get("requirements_status") != open_by_id[target]["status"]:
                    errors.append(f"{where}.requirements_status: does not match requirements.json")
                for decision_field in ("decision_ref", "provisional_rule", "review_trigger"):
                    _text(row.get(decision_field), f"{where}.{decision_field}", errors, nullable=True)
                if row.get("provisional_rule") is not None and (
                    row.get("decision_ref") is None or row.get("review_trigger") is None
                ):
                    errors.append(f"{where}: provisional rule needs decision_ref and review_trigger")
        _exact(seen, selected, f"$.{field}", errors)
    if errors:
        raise ArtifactError("\n".join(errors))


def validate(
    requirements_path: Path, review_path: Path, register_path: Path
) -> dict[str, Any]:
    requirements, _ = _load_inputs(requirements_path, review_path)
    register = load_json(register_path)
    _validate_payload(register, requirements, requirements_path, review_path)
    print(f"PASS {SCHEMA_VERSION}: {register_path}")
    return register


def _cell(value: Any) -> str:
    if value is None:
        return "—"
    if isinstance(value, list):
        value = ", ".join(value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def render(
    requirements_path: Path, review_path: Path, register_path: Path, output: Path
) -> None:
    register = validate(requirements_path, review_path, register_path)
    requirements = load_json(requirements_path)
    statements = {item["id"]: item["statement"] for item in requirements["requirements"]}
    questions = {item["id"]: item["question"] for item in requirements["open_items"]}
    source_clauses = register["source_clauses"]
    requirement_owners = register["requirement_owners"]
    open_owners = register["open_item_owners"]
    lines = [
        "# Реєстр рішень",
        "",
        f"Контракт: `{SCHEMA_VERSION}`  ",
        f"SHA-256 вимог: `{register['requirements_sha256']}`  ",
        f"SHA-256 критики: `{register['review_sha256']}`",
        "",
        "Статус `pending` і порожній власник означають, що рішення або призначення ще не зафіксовано.",
        "",
        f"Покриття: {len(source_clauses)} джерельних положень, {len(requirement_owners)} вимог, {len(open_owners)} OPEN.",
        "",
        "## Статус положень джерела",
        "",
        "| ID | Вимоги | Що вирішити | Статус | Хто вирішує | Підстава | Робоче правило | Тригер перегляду | Перевірка |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for clause in source_clauses:
        lines.append(
            "| {source_clause_id} | {requirement_ids} | {decision_text} | {disposition} | {decision_owner} | {decision_ref} | {provisional_rule} | {review_trigger} | {verification} |".format(
                decision_text=_cell(" ".join(statements[item] for item in clause["requirement_ids"])),
                **{key: _cell(clause[key]) for key in (
                    "source_clause_id", "requirement_ids", "disposition", "decision_owner",
                    "decision_ref", "provisional_rule", "review_trigger", "verification"
                )}
            )
        )
    lines.extend([
        "", "## Feature ownership вимог", "",
        "| Вимога | Feature | Власник | Підстава |",
        "| --- | --- | --- | --- |",
    ])
    for row in requirement_owners:
        lines.append(
            "| {requirement_id} | {feature_id} | {feature_owner} | {assignment_ref} |".format(
                **{key: _cell(row[key]) for key in REQUIREMENT_OWNER_KEYS}
            )
        )
    lines.extend([
        "", "## Ownership відкритих питань", "",
        "| OPEN | Що вирішити | Статус вимог | Feature | Хто вирішує | Підстава призначення | Рішення | Тимчасове правило | Тригер перегляду |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in open_owners:
        lines.append(
            "| {open_item_id} | {question} | {requirements_status} | {feature_id} | {decision_owner} | {assignment_ref} | {decision_ref} | {provisional_rule} | {review_trigger} |".format(
                question=_cell(questions[row["open_item_id"]]),
                **{key: _cell(row[key]) for key in OPEN_OWNER_KEYS}
            )
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {output}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("draft", "validate", "render"):
        sub = subparsers.add_parser(command)
        sub.add_argument("--requirements", type=Path, required=True)
        sub.add_argument("--review", type=Path, required=True)
        if command == "draft":
            sub.add_argument("--requirement-pattern", required=True)
            sub.add_argument("--open-pattern", required=True)
            sub.add_argument("--output", type=Path, required=True)
        else:
            sub.add_argument("--register", type=Path, required=True)
            if command == "render":
                sub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "draft":
            draft(
                args.requirements, args.review, args.requirement_pattern,
                args.open_pattern, args.output,
            )
        elif args.command == "validate":
            validate(args.requirements, args.review, args.register)
        else:
            render(args.requirements, args.review, args.register, args.output)
    except ArtifactError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
