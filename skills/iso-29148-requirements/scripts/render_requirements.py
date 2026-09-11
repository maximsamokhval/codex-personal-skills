#!/usr/bin/env python3
"""Render a validated ISO 29148-inspired requirements package as Markdown."""

from __future__ import annotations

import argparse
import copy
import html
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from validate_requirements import validate_document


LEVELS = ("BRS", "StRS", "SyRS", "SRS")
LEVEL_TITLES = {
    "en": {
        "BRS": "Business or Mission Requirements Specification",
        "StRS": "Stakeholder Requirements Specification",
        "SyRS": "System Requirements Specification",
        "SRS": "Software Requirements Specification",
    },
    "ru": {
        "BRS": "Спецификация бизнес-требований или требований миссии",
        "StRS": "Спецификация требований заинтересованных сторон",
        "SyRS": "Спецификация системных требований",
        "SRS": "Спецификация требований к программному обеспечению",
    },
}
ACTIVE_DISPOSITIONS = frozenset({"proposed", "accepted"})
SOURCE_STATUSES = ("processed", "partial", "skipped")
QUALITY_STATUSES = ("normalized", "needs-review")
DISPOSITIONS = (
    "proposed",
    "accepted",
    "rejected",
    "superseded",
)
ISSUE_SEVERITIES = ("blocking", "warning")
ARTIFACT_NAMES = (
    "requirements.json",
    "requirements-register.md",
    "BRS.md",
    "StRS.md",
    "SyRS.md",
    "SRS.md",
    "traceability-matrix.md",
    "open-issues.md",
)
NOTICES = {
    "en": (
        "> Structured using a practical method informed by publicly described principles "
        "of ISO/IEC/IEEE 29148:2018; this is not a certification or normative "
        "conformity assessment."
    ),
    "ru": (
        "> Структурировано с применением практического метода, основанного на публично "
        "описанных принципах ISO/IEC/IEEE 29148:2018; это не сертификация и не оценка "
        "нормативного соответствия."
    ),
}

TEXT = {
    "en": {
        "requirements_register": "Requirements Register",
        "metadata": "Metadata",
        "title": "Title",
        "schema_version": "Schema version",
        "profile": "Profile",
        "language": "Language",
        "generated_at": "Generated at",
        "field": "Field",
        "value": "Value",
        "counts": "Counts",
        "requirement_level": "Requirement level",
        "requirement_quality_status": "Requirement quality status",
        "requirement_disposition": "Requirement disposition",
        "provenance": "Provenance",
        "source_status": "Source status",
        "dimension": "Dimension",
        "count": "Count",
        "level_coverage": "Level coverage",
        "level": "Level",
        "status": "Status",
        "quality_status": "Quality status",
        "disposition": "Disposition",
        "basis": "Basis",
        "issue": "Issue",
        "source_inventory": "Source inventory",
        "source_id": "Source ID",
        "name": "Name",
        "media_type": "Media type",
        "path": "Path",
        "sha256": "SHA-256",
        "locator_scheme": "Locator scheme",
        "notes": "Notes",
        "no_sources": "No sources are present in the canonical register.",
        "requirements": "Requirements",
        "no_requirements": "No evidence-backed requirements were identified.",
        "category": "Category",
        "statement": "Statement",
        "confidence": "Confidence",
        "rationale": "Rationale",
        "stakeholders": "Stakeholders",
        "priority": "Priority",
        "priority_basis": "Priority basis",
        "verification_method": "Verification method",
        "acceptance_criteria": "Acceptance criteria",
        "decision_basis": "Decision basis",
        "superseded_by": "Superseded by",
        "historical_record": "Historical record: {status}.",
        "needs_review_notice": (
            "This requirement needs review and is not presented as settled."
        ),
        "source_evidence": "Source evidence",
        "locator": "Locator",
        "ocr": "OCR",
        "evidence": "Evidence",
        "quality_findings": "Quality findings",
        "code": "Code",
        "severity": "Severity",
        "message": "Message",
        "related_issues": "Related issues: {issues}",
        "context_items": "Context items",
        "type": "Type",
        "text": "Text",
        "no_context": "No source-backed context items were recorded.",
        "relationship_summary": "Relationship summary",
        "relationship_id": "Relationship ID",
        "from": "From",
        "to": "To",
        "no_relationships_recorded": (
            "No requirement-to-requirement relationships were recorded."
        ),
        "coverage": "Coverage",
        "no_active_gap": (
            "No evidence-backed active requirement is available for this level. "
            "See {issue}."
        ),
        "not_applicable": (
            "This level is not applicable for the evidence-backed scope. "
            "Basis: {basis}"
        ),
        "no_normalized_accepted": (
            "No active requirement with normalized quality is available for this level."
        ),
        "needs_review_appendix": "Needs-review appendix",
        "no_awaiting_review": (
            "No requirements are awaiting review for this level."
        ),
        "traceability_matrix": "Traceability Matrix",
        "requirement_to_source": "Requirement-to-source traceability",
        "requirement_id": "Requirement ID",
        "no_trace_rows": "No requirement-to-source rows are present.",
        "canonical_relationships": "Canonical relationships",
        "no_canonical_relationships": (
            "No canonical requirement relationships are present."
        ),
        "coverage_gaps": "Coverage gaps",
        "no_coverage_gaps": "No level coverage gaps are recorded.",
        "open_issues_title": "Open Issues and Review Items",
        "summary": "Summary",
        "issue_status": "Issue status",
        "issue_severity": "Issue severity",
        "sources_requiring_attention": "Sources requiring attention",
        "no_attention_sources": "No partial or skipped sources are recorded.",
        "requirements_requiring_attention": "Requirements requiring attention",
        "no_attention_requirements": (
            "No needs-review or low-confidence requirements are recorded."
        ),
        "source_backed_assumptions": "Source-backed assumptions",
        "context_id": "Context ID",
        "assumption": "Assumption",
        "source_ids": "Source IDs",
        "no_assumptions": "No source-backed assumptions are recorded.",
        "no_quality_findings": "No quality findings are recorded.",
        "issues": "Issues",
        "affected_sources": "Affected sources",
        "requirement_ids": "Requirement IDs",
        "affected_levels": "Affected levels",
        "resolution": "Resolution",
        "no_issue_refs": "No source references are recorded for this issue.",
        "no_issues": "No issues are recorded in the canonical register.",
        "generated_warnings": "Generated warnings",
        "warning_source": "Source",
        "warning": "Warning",
        "validator": "Validator",
        "renderer": "Renderer",
        "no_generated_warnings": "No validator or renderer warnings were emitted.",
        "unlinked": "Unlinked",
    },
    "ru": {
        "requirements_register": "Реестр требований",
        "metadata": "Метаданные",
        "title": "Название",
        "schema_version": "Версия схемы",
        "profile": "Профиль",
        "language": "Язык",
        "generated_at": "Дата формирования",
        "field": "Поле",
        "value": "Значение",
        "counts": "Количество записей",
        "requirement_level": "Уровень требования",
        "requirement_quality_status": "Статус качества требования",
        "requirement_disposition": "Решение по требованию",
        "provenance": "Происхождение",
        "source_status": "Статус источника",
        "dimension": "Разрез",
        "count": "Количество",
        "level_coverage": "Покрытие уровней",
        "level": "Уровень",
        "status": "Статус",
        "quality_status": "Статус качества",
        "disposition": "Решение",
        "basis": "Основание",
        "issue": "Проблема",
        "source_inventory": "Перечень источников",
        "source_id": "ID источника",
        "name": "Название",
        "media_type": "Тип носителя",
        "path": "Путь",
        "sha256": "SHA-256",
        "locator_scheme": "Схема указателей",
        "notes": "Примечания",
        "no_sources": "В каноническом реестре нет источников.",
        "requirements": "Требования",
        "no_requirements": "Требования, подтверждённые источниками, не выявлены.",
        "category": "Категория",
        "statement": "Формулировка",
        "confidence": "Уверенность",
        "rationale": "Обоснование",
        "stakeholders": "Заинтересованные стороны",
        "priority": "Приоритет",
        "priority_basis": "Основание приоритета",
        "verification_method": "Метод проверки",
        "acceptance_criteria": "Критерии приёмки",
        "decision_basis": "Основание решения",
        "superseded_by": "Заменено требованием",
        "historical_record": "Историческая запись: {status}.",
        "needs_review_notice": (
            "Это требование требует проверки и не представлено как согласованное."
        ),
        "source_evidence": "Свидетельства из источников",
        "locator": "Указатель",
        "ocr": "OCR",
        "evidence": "Свидетельство",
        "quality_findings": "Замечания по качеству",
        "code": "Код",
        "severity": "Серьёзность",
        "message": "Сообщение",
        "related_issues": "Связанные проблемы: {issues}",
        "context_items": "Контекстные элементы",
        "type": "Тип",
        "text": "Текст",
        "no_context": "Контекстные элементы из источников не зарегистрированы.",
        "relationship_summary": "Сводка связей",
        "relationship_id": "ID связи",
        "from": "От",
        "to": "К",
        "no_relationships_recorded": "Связи между требованиями не зарегистрированы.",
        "coverage": "Покрытие",
        "no_active_gap": (
            "Для этого уровня нет активного требования, подтверждённого источниками. "
            "См. {issue}."
        ),
        "not_applicable": (
            "Этот уровень неприменим к области, подтверждённой источниками. "
            "Основание: {basis}"
        ),
        "no_normalized_accepted": (
            "Для этого уровня нет активного требования с нормализованным качеством."
        ),
        "needs_review_appendix": "Приложение: требования на проверке",
        "no_awaiting_review": "Для этого уровня нет требований, ожидающих проверки.",
        "traceability_matrix": "Матрица прослеживаемости",
        "requirement_to_source": "Прослеживаемость требований к источникам",
        "requirement_id": "ID требования",
        "no_trace_rows": "Строки прослеживаемости требований к источникам отсутствуют.",
        "canonical_relationships": "Канонические связи",
        "no_canonical_relationships": "Канонические связи требований отсутствуют.",
        "coverage_gaps": "Пробелы покрытия",
        "no_coverage_gaps": "Пробелы покрытия уровней не зарегистрированы.",
        "open_issues_title": "Открытые проблемы и элементы для проверки",
        "summary": "Сводка",
        "issue_status": "Статус проблемы",
        "issue_severity": "Серьёзность проблемы",
        "sources_requiring_attention": "Источники, требующие внимания",
        "no_attention_sources": "Частично обработанные или пропущенные источники отсутствуют.",
        "requirements_requiring_attention": "Требования, требующие внимания",
        "no_attention_requirements": (
            "Требования на проверке или с низкой уверенностью отсутствуют."
        ),
        "source_backed_assumptions": "Предположения, подтверждённые источниками",
        "context_id": "ID контекста",
        "assumption": "Предположение",
        "source_ids": "ID источников",
        "no_assumptions": "Предположения, подтверждённые источниками, отсутствуют.",
        "no_quality_findings": "Замечания по качеству отсутствуют.",
        "issues": "Проблемы",
        "affected_sources": "Затронутые источники",
        "requirement_ids": "ID требований",
        "affected_levels": "Затронутые уровни",
        "resolution": "Решение",
        "no_issue_refs": "Для этой проблемы ссылки на источники не зарегистрированы.",
        "no_issues": "Проблемы в каноническом реестре не зарегистрированы.",
        "generated_warnings": "Сформированные предупреждения",
        "warning_source": "Источник",
        "warning": "Предупреждение",
        "validator": "Валидатор",
        "renderer": "Рендерер",
        "no_generated_warnings": "Предупреждения валидатора или рендерера отсутствуют.",
        "unlinked": "Без связи",
    },
}


def _labels(locale: str) -> Mapping[str, str]:
    return TEXT[locale]


def _locale_for_language(language: Any) -> tuple[str, list[str]]:
    value = str(language).strip()
    normalized = value.casefold()
    if normalized == "russian" or normalized == "русский" or re.match(
        r"^ru(?:$|[-_])", normalized
    ):
        return "ru", []
    if normalized == "english" or re.match(r"^en(?:$|[-_])", normalized):
        return "en", []
    return (
        "en",
        [
            f"Unsupported document language {value!r}; using English structural "
            "headings and labels."
        ],
    )


def _natural_key(value: object) -> tuple[Any, ...]:
    """Return a total natural-sort key with a lexical tie-breaker."""
    text = str(value)
    parts = re.split(r"(\d+)", text)
    natural = tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in parts
        if part
    )
    return natural, text.casefold(), text


def _records_by_id(records: Iterable[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(records, key=lambda record: _natural_key(record.get("id", "")))


def _source_ref_key(reference: Mapping[str, Any]) -> tuple[Any, ...]:
    return (
        _natural_key(reference.get("source_id", "")),
        str(reference.get("locator", "")).casefold(),
        str(reference.get("evidence", "")).casefold(),
    )


def _canonical_document(document: Mapping[str, Any]) -> dict[str, Any]:
    """Sort top-level ID collections while preserving every nested array order."""
    canonical = copy.deepcopy(dict(document))

    for collection_name in (
        "sources",
        "context_items",
        "requirements",
        "relationships",
        "issues",
    ):
        records = canonical.get(collection_name)
        if isinstance(records, list):
            records.sort(key=lambda record: _natural_key(record.get("id", "")))

    return canonical


def _plain(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ": "))


def _sequence_text(values: Any) -> str:
    if not isinstance(values, list):
        return _plain(values)
    return "\n".join(_plain(value) for value in values)


def _markdown_cell(value: Any) -> str:
    """Escape user/source content for a GitHub-Flavored Markdown table cell."""
    text = _plain(value).replace("\r\n", "\n").replace("\r", "\n")
    text = html.escape(text, quote=False)
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return text.replace("\n", "<br>")


def _markdown_text(value: Any) -> str:
    """Escape source-controlled text interpolated outside Markdown tables."""
    text = _plain(value).replace("\r\n", "\n").replace("\r", "\n")
    text = html.escape(text, quote=False).replace("\\", "\\\\")
    for marker in ("`", "*", "_", "[", "]"):
        text = text.replace(marker, f"\\{marker}")
    return text.replace("\n", "<br>")


def _table(headers: Sequence[str], rows: Iterable[Sequence[Any]]) -> str:
    escaped_headers = [_markdown_cell(header) for header in headers]
    lines = [
        "| " + " | ".join(escaped_headers) + " |",
        "| " + " | ".join("---" for _ in escaped_headers) + " |",
    ]
    for row in rows:
        cells = list(row)
        if len(cells) != len(headers):
            raise ValueError("Markdown table row has the wrong number of cells")
        lines.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")
    return "\n".join(lines)


def _finish(lines: Sequence[str]) -> str:
    return "\n".join(lines).rstrip() + "\n"


def _issue_anchor(issue_id: str) -> str:
    return issue_id.casefold()


def _issue_link(issue_id: Any) -> str:
    if not issue_id:
        return ""
    text = str(issue_id)
    return f"[{text}](open-issues.md#{_issue_anchor(text)})"


def _source_reference_table(
    references: Iterable[Mapping[str, Any]], locale: str
) -> str:
    labels = _labels(locale)
    rows = [
        (
            reference.get("source_id"),
            reference.get("locator"),
            reference.get("ocr", False),
            reference.get("evidence"),
        )
        for reference in sorted(references, key=_source_ref_key)
    ]
    return _table(
        (
            labels["source_id"],
            labels["locator"],
            labels["ocr"],
            labels["evidence"],
        ),
        rows,
    )


def _relationship_table(
    relationships: Iterable[Mapping[str, Any]], locale: str
) -> str:
    labels = _labels(locale)
    rows = [
        (
            relationship.get("id"),
            relationship.get("type"),
            relationship.get("from_id"),
            relationship.get("to_id"),
            relationship.get("basis"),
            _issue_link(relationship.get("issue_id")),
        )
        for relationship in _records_by_id(relationships)
    ]
    return _table(
        (
            labels["relationship_id"],
            labels["type"],
            labels["from"],
            labels["to"],
            labels["basis"],
            labels["issue"],
        ),
        rows,
    )


def _issues_for_requirements(
    issues: Iterable[Mapping[str, Any]],
) -> dict[str, list[str]]:
    result: dict[str, set[str]] = {}
    for issue in issues:
        issue_id = issue.get("id")
        if not issue_id:
            continue
        for requirement_id in issue.get("requirement_ids", []):
            result.setdefault(str(requirement_id), set()).add(str(issue_id))
    return {
        requirement_id: sorted(issue_ids, key=_natural_key)
        for requirement_id, issue_ids in result.items()
    }


def _requirement_issue_ids(
    requirement: Mapping[str, Any], issue_map: Mapping[str, Sequence[str]]
) -> list[str]:
    identifiers = set(issue_map.get(str(requirement.get("id", "")), []))
    for finding in requirement.get("quality_findings", []):
        issue_id = finding.get("issue_id")
        if issue_id:
            identifiers.add(str(issue_id))
    return sorted(identifiers, key=_natural_key)


def _requirement_block(
    requirement: Mapping[str, Any],
    issue_map: Mapping[str, Sequence[str]],
    locale: str,
    heading_level: int = 3,
) -> list[str]:
    labels = _labels(locale)
    priority = requirement.get("priority") or {}
    verification = requirement.get("verification") or {}
    requirement_id = str(requirement.get("id", ""))
    quality_status = requirement.get("quality_status")
    disposition = requirement.get("disposition")

    lines = [f"{'#' * heading_level} {requirement_id}", ""]
    if disposition in {"rejected", "superseded"}:
        lines.extend(
            [
                f"> {labels['historical_record'].format(status=disposition)}",
                "",
            ]
        )
    elif quality_status == "needs-review":
        lines.extend([f"> {labels['needs_review_notice']}", ""])

    lines.extend(
        [
            _table(
                (labels["field"], labels["value"]),
                (
                    (labels["level"], requirement.get("level")),
                    (labels["category"], requirement.get("category")),
                    (labels["quality_status"], quality_status),
                    (labels["disposition"], disposition),
                    (labels["statement"], requirement.get("statement")),
                    (labels["provenance"], requirement.get("provenance")),
                    (labels["confidence"], requirement.get("confidence")),
                    (labels["rationale"], requirement.get("rationale")),
                    (
                        labels["stakeholders"],
                        _sequence_text(requirement.get("stakeholders", [])),
                    ),
                    (labels["priority"], priority.get("value")),
                    (labels["priority_basis"], priority.get("basis")),
                    (labels["verification_method"], verification.get("method")),
                    (
                        labels["acceptance_criteria"],
                        verification.get("acceptance_criteria"),
                    ),
                    (labels["decision_basis"], requirement.get("decision_basis")),
                    (labels["superseded_by"], requirement.get("superseded_by")),
                ),
            ),
            "",
            f"{'#' * (heading_level + 1)} {labels['source_evidence']}",
            "",
            _source_reference_table(requirement.get("source_refs", []), locale),
        ]
    )

    findings = requirement.get("quality_findings", [])
    if findings:
        lines.extend(
            [
                "",
                f"{'#' * (heading_level + 1)} {labels['quality_findings']}",
                "",
                _table(
                    (
                        labels["code"],
                        labels["severity"],
                        labels["message"],
                        labels["issue"],
                    ),
                    (
                        (
                            finding.get("code"),
                            finding.get("severity"),
                            finding.get("message"),
                            _issue_link(finding.get("issue_id")),
                        )
                        for finding in findings
                    ),
                ),
            ]
        )

    related_issues = _requirement_issue_ids(requirement, issue_map)
    if related_issues:
        lines.extend(
            [
                "",
                labels["related_issues"].format(
                    issues=", ".join(
                        _issue_link(issue_id) for issue_id in related_issues
                    )
                ),
            ]
        )
    return lines


def _count_rows(
    values: Iterable[Any], preferred_order: Sequence[str] = ()
) -> list[tuple[str, int]]:
    counts = Counter(str(value) for value in values)
    rows: list[tuple[str, int]] = []
    for value in preferred_order:
        rows.append((value, counts.pop(value, 0)))
    rows.extend((value, counts[value]) for value in sorted(counts, key=_natural_key))
    return rows


def _render_register(document: Mapping[str, Any], locale: str) -> str:
    labels = _labels(locale)
    sources = _records_by_id(document.get("sources", []))
    requirements = _records_by_id(document.get("requirements", []))
    contexts = _records_by_id(document.get("context_items", []))
    relationships = _records_by_id(document.get("relationships", []))
    issue_map = _issues_for_requirements(document.get("issues", []))

    lines = [
        f"# {labels['requirements_register']}",
        "",
        NOTICES[locale],
        "",
        f"## {labels['metadata']}",
        "",
    ]
    metadata_rows = [
        (labels["title"], document.get("title")),
        (labels["schema_version"], document.get("schema_version")),
        (labels["profile"], document.get("profile")),
        (labels["language"], document.get("language")),
    ]
    if "generated_at" in document:
        metadata_rows.append((labels["generated_at"], document.get("generated_at")))
    lines.extend(
        [
            _table((labels["field"], labels["value"]), metadata_rows),
            "",
            f"## {labels['counts']}",
            "",
        ]
    )

    count_rows: list[tuple[Any, ...]] = []
    count_rows.extend(
        (labels["requirement_level"], value, count)
        for value, count in _count_rows(
            (requirement.get("level") for requirement in requirements), LEVELS
        )
    )
    count_rows.extend(
        (labels["requirement_quality_status"], value, count)
        for value, count in _count_rows(
            (requirement.get("quality_status") for requirement in requirements),
            QUALITY_STATUSES,
        )
    )
    count_rows.extend(
        (labels["requirement_disposition"], value, count)
        for value, count in _count_rows(
            (requirement.get("disposition") for requirement in requirements),
            DISPOSITIONS,
        )
    )
    count_rows.extend(
        (labels["provenance"], value, count)
        for value, count in _count_rows(
            (requirement.get("provenance") for requirement in requirements),
            ("explicit", "derived", "inferred"),
        )
    )
    count_rows.extend(
        (labels["source_status"], value, count)
        for value, count in _count_rows(
            (source.get("status") for source in sources),
            SOURCE_STATUSES,
        )
    )
    lines.extend(
        [
            _table(
                (labels["dimension"], labels["value"], labels["count"]),
                count_rows,
            ),
            "",
            f"## {labels['level_coverage']}",
            "",
            _table(
                (
                    labels["level"],
                    labels["status"],
                    labels["basis"],
                    labels["issue"],
                ),
                (
                    (
                        level,
                        document["level_coverage"][level].get("status"),
                        document["level_coverage"][level].get("basis"),
                        _issue_link(document["level_coverage"][level].get("issue_id")),
                    )
                    for level in LEVELS
                ),
            ),
            "",
            f"## {labels['source_inventory']}",
            "",
        ]
    )

    if sources:
        lines.append(
            _table(
                (
                    labels["source_id"],
                    labels["name"],
                    labels["media_type"],
                    labels["path"],
                    labels["sha256"],
                    labels["status"],
                    labels["locator_scheme"],
                    labels["notes"],
                ),
                (
                    (
                        source.get("id"),
                        source.get("name"),
                        source.get("media_type"),
                        source.get("path"),
                        source.get("digest_sha256"),
                        source.get("status"),
                        source.get("locator_scheme"),
                        _sequence_text(source.get("notes", [])),
                    )
                    for source in sources
                ),
            )
        )
    else:
        lines.append(labels["no_sources"])

    lines.extend(["", f"## {labels['requirements']}", ""])
    if requirements:
        for index, requirement in enumerate(requirements):
            if index:
                lines.append("")
            lines.extend(
                _requirement_block(
                    requirement, issue_map, locale, heading_level=3
                )
            )
    else:
        lines.append(labels["no_requirements"])

    lines.extend(["", f"## {labels['context_items']}", ""])
    if contexts:
        for context in contexts:
            lines.extend(
                [
                    f"### {context.get('id')}",
                    "",
                    _table(
                        (labels["field"], labels["value"]),
                        (
                            (labels["type"], context.get("type")),
                            (labels["text"], context.get("text")),
                        ),
                    ),
                    "",
                    f"#### {labels['source_evidence']}",
                    "",
                    _source_reference_table(context.get("source_refs", []), locale),
                    "",
                ]
            )
    else:
        lines.append(labels["no_context"])

    lines.extend(["", f"## {labels['relationship_summary']}", ""])
    if relationships:
        lines.append(_relationship_table(relationships, locale))
    else:
        lines.append(labels["no_relationships_recorded"])
    return _finish(lines)


def _render_level(document: Mapping[str, Any], level: str, locale: str) -> str:
    labels = _labels(locale)
    coverage = document["level_coverage"][level]
    requirements = [
        requirement
        for requirement in _records_by_id(document.get("requirements", []))
        if requirement.get("level") == level
    ]
    main_requirements = [
        requirement
        for requirement in requirements
        if requirement.get("quality_status") == "normalized"
        and requirement.get("disposition") in ACTIVE_DISPOSITIONS
    ]
    review_requirements = [
        requirement
        for requirement in requirements
        if requirement.get("quality_status") == "needs-review"
        and requirement.get("disposition") in ACTIVE_DISPOSITIONS
    ]
    issue_map = _issues_for_requirements(document.get("issues", []))
    coverage_issue = _issue_link(coverage.get("issue_id"))

    lines = [
        f"# {level} — {LEVEL_TITLES[locale][level]}",
        "",
        NOTICES[locale],
        "",
        f"## {labels['coverage']}",
        "",
        _table(
            (labels["status"], labels["basis"], labels["issue"]),
            ((coverage.get("status"), coverage.get("basis"), coverage_issue),),
        ),
        "",
        f"## {labels['requirements']}",
        "",
    ]

    if main_requirements:
        for index, requirement in enumerate(main_requirements):
            if index:
                lines.append("")
            lines.extend(
                _requirement_block(
                    requirement, issue_map, locale, heading_level=3
                )
            )
    elif coverage.get("status") == "gap":
        lines.append(labels["no_active_gap"].format(issue=coverage_issue))
    elif coverage.get("status") == "not-applicable":
        lines.append(
            labels["not_applicable"].format(
                basis=_markdown_text(coverage.get("basis"))
            )
        )
    else:
        lines.append(labels["no_normalized_accepted"])

    lines.extend(["", f"## {labels['needs_review_appendix']}", ""])
    if review_requirements:
        for index, requirement in enumerate(review_requirements):
            if index:
                lines.append("")
            lines.extend(
                _requirement_block(
                    requirement, issue_map, locale, heading_level=3
                )
            )
    else:
        lines.append(labels["no_awaiting_review"])
    return _finish(lines)


def _render_traceability(document: Mapping[str, Any], locale: str) -> str:
    labels = _labels(locale)
    requirements = _records_by_id(document.get("requirements", []))
    relationships = _records_by_id(document.get("relationships", []))
    source_status_by_id = {
        str(source.get("id")): source.get("status")
        for source in document.get("sources", [])
    }
    trace_rows: list[tuple[Any, ...]] = []
    for requirement in requirements:
        for reference in sorted(requirement.get("source_refs", []), key=_source_ref_key):
            trace_rows.append(
                (
                    requirement.get("id"),
                    requirement.get("level"),
                    requirement.get("quality_status"),
                    requirement.get("disposition"),
                    reference.get("source_id"),
                    source_status_by_id.get(str(reference.get("source_id")), ""),
                    reference.get("locator"),
                    requirement.get("provenance"),
                    reference.get("ocr", False),
                    reference.get("evidence"),
                )
            )

    lines = [
        f"# {labels['traceability_matrix']}",
        "",
        NOTICES[locale],
        "",
        f"## {labels['requirement_to_source']}",
        "",
    ]
    if trace_rows:
        lines.append(
            _table(
                (
                    labels["requirement_id"],
                    labels["level"],
                    labels["quality_status"],
                    labels["disposition"],
                    labels["source_id"],
                    labels["source_status"],
                    labels["locator"],
                    labels["provenance"],
                    labels["ocr"],
                    labels["evidence"],
                ),
                trace_rows,
            )
        )
    else:
        lines.append(labels["no_trace_rows"])

    lines.extend(["", f"## {labels['canonical_relationships']}", ""])
    if relationships:
        lines.append(_relationship_table(relationships, locale))
    else:
        lines.append(labels["no_canonical_relationships"])

    gap_rows = []
    for level in LEVELS:
        coverage = document["level_coverage"][level]
        if coverage.get("status") == "gap":
            gap_rows.append(
                (level, coverage.get("basis"), _issue_link(coverage.get("issue_id")))
            )
    lines.extend(["", f"## {labels['coverage_gaps']}", ""])
    if gap_rows:
        lines.append(
            _table(
                (labels["level"], labels["basis"], labels["issue"]),
                gap_rows,
            )
        )
    else:
        lines.append(labels["no_coverage_gaps"])
    return _finish(lines)


def _render_open_issues(
    document: Mapping[str, Any],
    validator_warnings: Sequence[str],
    renderer_warnings: Sequence[str],
    locale: str,
) -> str:
    labels = _labels(locale)
    issues = _records_by_id(document.get("issues", []))
    sources = _records_by_id(document.get("sources", []))
    requirements = _records_by_id(document.get("requirements", []))
    assumptions = [
        item
        for item in _records_by_id(document.get("context_items", []))
        if item.get("type") == "assumption"
    ]
    attention_sources = [
        source for source in sources if source.get("status") in {"partial", "skipped"}
    ]
    review_requirements = [
        requirement
        for requirement in requirements
        if requirement.get("quality_status") == "needs-review"
        or requirement.get("confidence") == "low"
    ]
    quality_rows = [
        (
            requirement.get("id"),
            finding.get("code"),
            finding.get("severity"),
            finding.get("message"),
            _issue_link(finding.get("issue_id")) or labels["unlinked"],
        )
        for requirement in requirements
        for finding in requirement.get("quality_findings", [])
    ]

    lines = [
        f"# {labels['open_issues_title']}",
        "",
        NOTICES[locale],
        "",
        f"## {labels['summary']}",
        "",
    ]
    summary_rows: list[tuple[Any, ...]] = []
    summary_rows.extend(
        (labels["issue_status"], value, count)
        for value, count in _count_rows(
            (issue.get("status") for issue in issues), ("open", "resolved")
        )
    )
    summary_rows.extend(
        (labels["issue_severity"], value, count)
        for value, count in _count_rows(
            (issue.get("severity") for issue in issues), ISSUE_SEVERITIES
        )
    )
    lines.append(
        _table(
            (labels["dimension"], labels["value"], labels["count"]),
            summary_rows,
        )
    )

    lines.extend(["", f"## {labels['sources_requiring_attention']}", ""])
    if attention_sources:
        lines.append(
            _table(
                (
                    labels["source_id"],
                    labels["name"],
                    labels["status"],
                    labels["notes"],
                ),
                (
                    (
                        source.get("id"),
                        source.get("name"),
                        source.get("status"),
                        _sequence_text(source.get("notes", [])),
                    )
                    for source in attention_sources
                ),
            )
        )
    else:
        lines.append(labels["no_attention_sources"])

    lines.extend(["", f"## {labels['requirements_requiring_attention']}", ""])
    if review_requirements:
        lines.append(
            _table(
                (
                    labels["requirement_id"],
                    labels["level"],
                    labels["quality_status"],
                    labels["disposition"],
                    labels["confidence"],
                    labels["statement"],
                ),
                (
                    (
                        requirement.get("id"),
                        requirement.get("level"),
                        requirement.get("quality_status"),
                        requirement.get("disposition"),
                        requirement.get("confidence"),
                        requirement.get("statement"),
                    )
                    for requirement in review_requirements
                ),
            )
        )
    else:
        lines.append(labels["no_attention_requirements"])

    lines.extend(["", f"## {labels['source_backed_assumptions']}", ""])
    if assumptions:
        lines.append(
            _table(
                (
                    labels["context_id"],
                    labels["assumption"],
                    labels["source_ids"],
                ),
                (
                    (
                        item.get("id"),
                        item.get("text"),
                        _sequence_text(
                            [
                                reference.get("source_id")
                                for reference in item.get("source_refs", [])
                            ]
                        ),
                    )
                    for item in assumptions
                ),
            )
        )
    else:
        lines.append(labels["no_assumptions"])

    lines.extend(["", f"## {labels['quality_findings']}", ""])
    if quality_rows:
        lines.append(
            _table(
                (
                    labels["requirement_id"],
                    labels["code"],
                    labels["severity"],
                    labels["message"],
                    labels["issue"],
                ),
                quality_rows,
            )
        )
    else:
        lines.append(labels["no_quality_findings"])

    lines.extend(["", f"## {labels['issues']}", ""])
    if issues:
        for issue in issues:
            issue_id = str(issue.get("id", ""))
            lines.extend(
                [
                    f"### {issue_id}",
                    "",
                    _table(
                        (labels["field"], labels["value"]),
                        (
                            (labels["type"], issue.get("type")),
                            (labels["severity"], issue.get("severity")),
                            (labels["status"], issue.get("status")),
                            (labels["message"], issue.get("message")),
                            (
                                labels["affected_sources"],
                                _sequence_text(issue.get("source_ids", [])),
                            ),
                            (
                                labels["requirement_ids"],
                                _sequence_text(issue.get("requirement_ids", [])),
                            ),
                            (
                                labels["affected_levels"],
                                _sequence_text(issue.get("affected_levels", [])),
                            ),
                            (labels["resolution"], issue.get("resolution")),
                        ),
                    ),
                    "",
                    f"#### {labels['source_evidence']}",
                    "",
                ]
            )
            references = issue.get("source_refs", [])
            if references:
                lines.append(_source_reference_table(references, locale))
            else:
                lines.append(labels["no_issue_refs"])
            lines.append("")
    else:
        lines.append(labels["no_issues"])

    lines.extend(["", f"## {labels['generated_warnings']}", ""])
    generated_warning_rows = [
        (labels["validator"], warning)
        for warning in sorted(validator_warnings, key=_natural_key)
    ]
    generated_warning_rows.extend(
        (labels["renderer"], warning)
        for warning in sorted(renderer_warnings, key=_natural_key)
    )
    if generated_warning_rows:
        lines.append(
            _table(
                ("#", labels["warning_source"], labels["warning"]),
                (
                    (index, source, warning)
                    for index, (source, warning) in enumerate(
                        generated_warning_rows, start=1
                    )
                ),
            )
        )
    else:
        lines.append(labels["no_generated_warnings"])
    return _finish(lines)


def _build_artifacts(
    document: Mapping[str, Any],
    validator_warnings: Sequence[str],
    renderer_warnings: Sequence[str],
    locale: str,
) -> dict[str, str]:
    canonical = _canonical_document(document)
    artifacts = {
        "requirements.json": json.dumps(
            canonical, ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
        "requirements-register.md": _render_register(canonical, locale),
        "BRS.md": _render_level(canonical, "BRS", locale),
        "StRS.md": _render_level(canonical, "StRS", locale),
        "SyRS.md": _render_level(canonical, "SyRS", locale),
        "SRS.md": _render_level(canonical, "SRS", locale),
        "traceability-matrix.md": _render_traceability(canonical, locale),
        "open-issues.md": _render_open_issues(
            canonical, validator_warnings, renderer_warnings, locale
        ),
    }
    if tuple(artifacts) != ARTIFACT_NAMES:
        raise RuntimeError("Renderer artifact set does not match its fixed contract")
    return artifacts


def _new_default_destination() -> Path:
    base = Path.cwd() / "outputs" / "iso-29148-requirements"
    base.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")
    suffix = 0
    while True:
        name = timestamp if suffix == 0 else f"{timestamp}-{suffix:02d}"
        candidate = base / name
        try:
            candidate.mkdir()
        except FileExistsError:
            suffix += 1
            continue
        return candidate


def _prepare_explicit_destination(path: Path, force: bool) -> Path:
    destination = path.expanduser().resolve()
    if destination.exists():
        if not destination.is_dir():
            raise ValueError(f"output destination is not a directory: {destination}")
        if any(destination.iterdir()) and not force:
            raise ValueError(
                f"output destination is not empty: {destination}; use --force only "
                "after an explicit replacement request"
            )
    else:
        destination.mkdir(parents=True)

    for name in ARTIFACT_NAMES:
        target = destination / name
        if target.exists() and target.is_dir():
            raise ValueError(f"artifact target is a directory: {target}")
    return destination


def _atomic_write(path: Path, content: str) -> None:
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except BaseException:
        try:
            temporary_path.unlink(missing_ok=True)
        finally:
            raise


def _write_artifacts(
    destination: Path, artifacts: Mapping[str, str], force: bool
) -> None:
    """Install the fixed artifact set as one rollback-capable transaction."""
    if tuple(artifacts) != ARTIFACT_NAMES:
        raise ValueError("artifact mapping does not match the fixed artifact set")

    staging = Path(
        tempfile.mkdtemp(prefix=".requirements-render-stage-", dir=destination)
    )
    backup: Path | None = None
    remove_backup = False
    backed_up: list[str] = []
    installed: list[str] = []
    try:
        # Fully materialize and fsync every artifact before changing any target.
        for name in ARTIFACT_NAMES:
            _atomic_write(staging / name, artifacts[name])

        if force:
            backup = Path(
                tempfile.mkdtemp(
                    prefix=".requirements-render-backup-", dir=destination
                )
            )

        for name in ARTIFACT_NAMES:
            target = destination / name
            if not target.exists():
                continue
            if target.is_dir():
                raise ValueError(f"artifact target is a directory: {target}")
            if not force or backup is None:
                raise ValueError(f"artifact target already exists: {target}")
            os.replace(target, backup / name)
            backed_up.append(name)

        for name in ARTIFACT_NAMES:
            os.replace(staging / name, destination / name)
            installed.append(name)
        remove_backup = True
    except BaseException as error:
        rollback_errors: list[str] = []
        backed_up_set = set(backed_up)

        # Remove only newly installed artifacts that had no prior counterpart.
        for name in reversed(installed):
            if name in backed_up_set:
                continue
            try:
                (destination / name).unlink(missing_ok=True)
            except OSError as rollback_error:
                rollback_errors.append(f"remove {name}: {rollback_error}")

        # Restoring with os.replace also replaces a partially installed new file.
        if backup is not None:
            for name in reversed(backed_up):
                try:
                    os.replace(backup / name, destination / name)
                except OSError as rollback_error:
                    rollback_errors.append(f"restore {name}: {rollback_error}")

        if rollback_errors:
            details = "; ".join(rollback_errors)
            raise RuntimeError(
                f"artifact transaction failed ({error}); rollback failed: {details}"
            ) from error
        remove_backup = True
        raise
    finally:
        shutil.rmtree(staging, ignore_errors=True)
        if backup is not None and remove_backup:
            shutil.rmtree(backup, ignore_errors=True)


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate object key {key!r}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _load_document(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as stream:
        return json.load(
            stream,
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_json_constant,
        )


def _configure_console_streams() -> None:
    """Prefer UTF-8 and retain an escaping fallback for unusual host streams."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="backslashreplace")
        except (OSError, TypeError, ValueError):
            pass


def _console_print(message: str, *, file: Any = None) -> None:
    target = sys.stdout if file is None else file
    try:
        print(message, file=target)
    except UnicodeEncodeError:
        encoding = getattr(target, "encoding", None) or "ascii"
        safe_message = message.encode(
            encoding, errors="backslashreplace"
        ).decode(encoding)
        print(safe_message, file=target)


def _print_diagnostics(
    errors: Sequence[str],
    validator_warnings: Sequence[str],
    renderer_warnings: Sequence[str] = (),
) -> None:
    for error in errors:
        _console_print(f"ERROR: {error}", file=sys.stderr)
    for warning in validator_warnings:
        _console_print(f"VALIDATOR WARNING: {warning}", file=sys.stderr)
    for warning in renderer_warnings:
        _console_print(f"RENDERER WARNING: {warning}", file=sys.stderr)


def _completion_report(
    document: Mapping[str, Any],
    destination: Path,
    validator_warnings: Sequence[str],
    renderer_warnings: Sequence[str],
) -> str:
    source_counts = Counter(
        str(source.get("status")) for source in document.get("sources", [])
    )
    requirements = document.get("requirements", [])
    level_counts = Counter(str(item.get("level")) for item in requirements)
    quality_counts = Counter(
        str(item.get("quality_status")) for item in requirements
    )
    disposition_counts = Counter(
        str(item.get("disposition")) for item in requirements
    )
    open_issue_counts = Counter(
        str(issue.get("severity"))
        for issue in document.get("issues", [])
        if issue.get("status") == "open"
    )
    output_directory = destination.resolve()
    canonical_path = output_directory / "requirements.json"

    lines = [
        f"Rendered {len(ARTIFACT_NAMES)} artifacts successfully.",
        f"Output directory: {output_directory}",
        f"Canonical JSON: {canonical_path}",
        "Sources: "
        + ", ".join(
            f"{status}={source_counts.get(status, 0)}"
            for status in SOURCE_STATUSES
        ),
        "Requirements by level: "
        + ", ".join(f"{level}={level_counts.get(level, 0)}" for level in LEVELS),
        "Requirements by quality status: "
        + ", ".join(
            f"{status}={quality_counts.get(status, 0)}"
            for status in QUALITY_STATUSES
        ),
        "Requirements by disposition: "
        + ", ".join(
            f"{disposition}={disposition_counts.get(disposition, 0)}"
            for disposition in DISPOSITIONS
        ),
        "Open issues: "
        + ", ".join(
            f"{severity}={open_issue_counts.get(severity, 0)}"
            for severity in ISSUE_SEVERITIES
        ),
        f"Validator warnings ({len(validator_warnings)}):",
    ]
    if validator_warnings:
        lines.extend(f"- {warning}" for warning in validator_warnings)
    else:
        lines.append("- none")
    lines.append(f"Renderer warnings ({len(renderer_warnings)}):")
    if renderer_warnings:
        lines.extend(f"- {warning}" for warning in renderer_warnings)
    else:
        lines.append("- none")
    lines.append("Artifacts:")
    lines.extend(f"- {output_directory / name}" for name in ARTIFACT_NAMES)
    return "\n".join(lines)


def _parse_arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and render an ISO 29148-inspired requirements package."
    )
    parser.add_argument("input", type=Path, metavar="INPUT", help="UTF-8 canonical JSON")
    parser.add_argument("--output", type=Path, metavar="DIR", help="output directory")
    parser.add_argument(
        "--force",
        action="store_true",
        help="replace only the eight known artifacts in a non-empty explicit destination",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console_streams()
    arguments = _parse_arguments(argv)
    try:
        document = _load_document(arguments.input)
    except (OSError, UnicodeError, ValueError) as error:
        _console_print(
            f"ERROR: unable to load UTF-8 JSON from {arguments.input}: {error}",
            file=sys.stderr,
        )
        return 1

    try:
        errors, warnings = validate_document(document)
    except Exception as error:
        _console_print(f"ERROR: validator failed: {error}", file=sys.stderr)
        return 1

    if errors:
        _print_diagnostics(errors, warnings)
        return 1

    try:
        # Validate once more after deterministic ordering so array-index diagnostics
        # in open-issues.md refer to the emitted canonical requirements.json.
        document = _canonical_document(document)
        errors, warnings = validate_document(document)
        locale, renderer_warnings = _locale_for_language(document.get("language"))
        _print_diagnostics(errors, warnings, renderer_warnings)
        if errors:
            return 1
        artifacts = _build_artifacts(
            document, warnings, renderer_warnings, locale
        )
        if arguments.output is None:
            destination = _new_default_destination()
        else:
            destination = _prepare_explicit_destination(arguments.output, arguments.force)
        _write_artifacts(destination, artifacts, arguments.force)
        missing = [
            name for name in ARTIFACT_NAMES if not (destination / name).is_file()
        ]
        if missing:
            raise RuntimeError(
                "artifact transaction completed with missing files: "
                + ", ".join(missing)
            )
    except (OSError, TypeError, ValueError, KeyError, RuntimeError) as error:
        _console_print(
            f"ERROR: unable to render requirements: {error}", file=sys.stderr
        )
        return 1

    _console_print(
        _completion_report(document, destination, warnings, renderer_warnings)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
