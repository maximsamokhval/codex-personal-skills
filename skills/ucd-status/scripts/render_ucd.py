#!/usr/bin/env python3
"""Validate an inspected UCD snapshot and render a local, offline HTML view."""

import argparse
import hashlib
import json
import re
from datetime import datetime
from html import escape
from pathlib import Path

STATUSES = {"implemented", "in_progress", "pending", "unknown"}
KINDS = {"code", "wiring", "test", "work", "gap", "other"}
LABELS = STATUSES | {
    "traceability",
    "requirements",
    "tasks",
    "evidence",
    "notes",
    "no_requirements",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def text(value, location):
    require(
        isinstance(value, str) and bool(value.strip()), f"{location}: expected text"
    )


def rows(value, location, nonempty=False):
    require(isinstance(value, list), f"{location}: expected list")
    require(not nonempty or bool(value), f"{location}: empty list")
    return value


def registry(value, location):
    result = {}
    for row in rows(value, location):
        require(isinstance(row, dict), f"{location}: expected object")
        text(row.get("id"), f"{location}.id")
        require(row["id"] not in result, f"{location}: duplicate ID {row['id']}")
        result[row["id"]] = row
    return result


def links(value, available, location, nonempty=False):
    values = rows(value, location, nonempty)
    require(all(isinstance(v, str) for v in values), f"{location}: expected ID strings")
    require(len(set(values)) == len(values), f"{location}: repeated ID")
    require(all(v in available for v in values), f"{location}: unknown reference")


def source_ref(row, sources):
    require(
        isinstance(row.get("source"), str) and row["source"] in sources,
        "unregistered evidence/requirement/actor/task source",
    )


def validate(data):
    require(isinstance(data, dict), "manifest: expected object")
    require(data.get("schema_version") == "ucd-status/v1", "unsupported schema_version")
    for name in ("title", "language"):
        text(data.get(name), name)
    snapshot = data.get("snapshot")
    require(isinstance(snapshot, dict), "snapshot: expected object")
    for name in ("checked_at", "revision", "worktree", "tracker"):
        text(snapshot.get(name), f"snapshot.{name}")
    moment = datetime.fromisoformat(snapshot["checked_at"].replace("Z", "+00:00"))
    require(moment.tzinfo is not None, "checked_at: timezone required")
    labels = data.get("labels")
    require(isinstance(labels, dict), "labels: expected object")
    for name in LABELS:
        text(labels.get(name), f"labels.{name}")
    for note in rows(data.get("notes"), "notes"):
        text(note, "notes[]")
    sources = registry(data.get("sources"), "sources")
    for row in sources.values():
        text(row.get("locator"), "sources.locator")
        if "sha256" in row:
            require(
                isinstance(row["sha256"], str)
                and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]),
                "invalid sha256",
            )
    requirements = registry(data.get("requirements"), "requirements")
    actors = registry(data.get("actors"), "actors")
    for row in [*requirements.values(), *actors.values()]:
        source_ref(row, sources)
    for actor in actors.values():
        text(actor.get("label"), "actor.label")
    views = registry(data.get("views"), "views")
    require(bool(views), "views: empty list")
    seen_cases = {}
    for view in views.values():
        for name in ("title", "system"):
            text(view.get(name), f"view.{name}")
        links(view.get("actors"), actors, "view.actors", True)
        require(len(view["actors"]) <= 3, "split view: at most 3 actors")
        cases = registry(view.get("cases"), "cases")
        require(0 < len(cases) <= 8, "split view: require 1..8 cases")
        for case in cases.values():
            text(case.get("label"), "case.label")
            status = case.get("status")
            require(
                isinstance(status, str) and status in STATUSES, "invalid case status"
            )
            links(case.get("actors"), view["actors"], "case.actors", True)
            links(case.get("requirements"), requirements, "case.requirements")
            require(isinstance(case.get("notes"), str), "case.notes: expected string")
            tasks = registry(case.get("tasks"), "case.tasks")
            for task in tasks.values():
                text(task.get("status"), "task.status")
                require(
                    type(task.get("superseded")) is bool,
                    "task.superseded: boolean required",
                )
                source_ref(task, sources)
            kinds = set()
            for proof in rows(case.get("evidence"), "case.evidence"):
                require(isinstance(proof, dict), "evidence: expected object")
                kind = proof.get("kind")
                require(
                    isinstance(kind, str) and kind in KINDS, "invalid evidence kind"
                )
                kinds.add(kind)
                source_ref(proof, sources)
                text(proof.get("locator"), "evidence.locator")
                text(proof.get("detail"), "evidence.detail")
            if status != "unknown":
                require(
                    bool(case["requirements"]),
                    "colored status requires requirement authority",
                )
            if status == "implemented":
                require(
                    {"code", "wiring", "test"} <= kinds,
                    "implemented requires code, wiring and test evidence",
                )
            elif status == "in_progress":
                active = any(
                    t["status"] == "in_progress" and not t["superseded"]
                    for t in tasks.values()
                )
                require(active or "work" in kinds, "in_progress requires active work")
            elif status == "pending":
                require("gap" in kinds, "pending requires an inspected gap")
            else:
                text(case["notes"], "unknown explanation")
            previous = seen_cases.setdefault(case["id"], case)
            require(previous == case, f"conflicting repeated case {case['id']}")
    return data


def render(data, standalone=False):
    validate(data)
    # Escape < so even a malicious plain-text label cannot end this script element.
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    root = "ucd-" + hashlib.sha256(payload.encode()).hexdigest()[:12]
    template = (Path(__file__).resolve().parents[1] / "assets" / "view.html").read_text(
        encoding="utf-8"
    )
    fragment = template.replace("__ROOT__", root).replace("__PAYLOAD__", payload)
    if not standalone:
        return fragment
    return (
        '<!doctype html><html lang="'
        + escape(data["language"], quote=True)
        + '"><head><meta charset="utf-8"><meta name="viewport" '
        'content="width=device-width, initial-scale=1"><title>'
        + escape(data["title"])
        + "</title><style>"
        ":root{color-scheme:light dark;--background:light-dark(#fff,#171717);"
        "--foreground:light-dark(#202020,#eee);--border:light-dark(#888,#999);"
        "--muted-foreground:light-dark(#626262,#aaa);--green:light-dark(#157d3b,#56c980);"
        "--red:light-dark(#bd2424,#f07878);--primary:light-dark(#e5e5e5,#363636)}"
        "body{font:14px system-ui;background:var(--background);color:var(--foreground);"
        "max-width:900px;margin:auto;padding:16px}button{font:inherit}"
        "[role=tablist]{display:flex;flex-wrap:wrap;gap:8px}"
        "[role=tab]{padding:8px;border:1px solid var(--border);background:transparent;"
        "color:var(--foreground)}[aria-selected=true]{background:var(--primary)}"
        "</style></head><body>" + fragment + "</body></html>"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--format", choices=("fragment", "standalone"), default="fragment"
    )
    parser.add_argument(
        "--overwrite", action="store_true", help="explicitly replace an existing output"
    )
    args = parser.parse_args()
    try:
        data = validate(json.loads(args.manifest.read_text(encoding="utf-8-sig")))
        if args.check:
            print(
                "Valid ucd-status/v1 snapshot (evidence structure, not claim verification)."
            )
            return
        require(args.output is not None, "output path required unless --check")
        require(
            args.output.resolve() != args.manifest.resolve(),
            "output cannot replace manifest",
        )
        output = render(data, args.format == "standalone")
        require(
            len(output.encode("utf-8")) < 1_000_000, "view exceeds 1 MB: split snapshot"
        )
        with args.output.open(
            "w" if args.overwrite else "x", encoding="utf-8", newline="\n"
        ) as stream:
            stream.write(output)
        print(args.output.resolve())
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"UCD error: {exc}\n")


if __name__ == "__main__":
    main()
