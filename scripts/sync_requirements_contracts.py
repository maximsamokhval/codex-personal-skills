#!/usr/bin/env python3
"""Synchronize canonical requirements-pipeline files into standalone skills."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "contracts" / "requirements-pipeline" / "v1"

COPIES = {
    "requirements.schema.json": [
        ROOT
        / "skills"
        / "requirements-extract"
        / "references"
        / "contracts"
        / "requirements.schema.json",
        ROOT
        / "skills"
        / "requirements-critic"
        / "references"
        / "contracts"
        / "requirements.schema.json",
        ROOT
        / "skills"
        / "specification-compiler"
        / "references"
        / "contracts"
        / "requirements.schema.json",
    ],
    "review.schema.json": [
        ROOT
        / "skills"
        / "requirements-critic"
        / "references"
        / "contracts"
        / "review.schema.json",
        ROOT
        / "skills"
        / "specification-compiler"
        / "references"
        / "contracts"
        / "review.schema.json",
    ],
    "baseline.schema.json": [
        ROOT
        / "skills"
        / "requirements-critic"
        / "references"
        / "contracts"
        / "baseline.schema.json",
        ROOT
        / "skills"
        / "specification-compiler"
        / "references"
        / "contracts"
        / "baseline.schema.json",
    ],
    "specification.schema.json": [
        ROOT
        / "skills"
        / "specification-compiler"
        / "references"
        / "contracts"
        / "specification.schema.json",
    ],
    "pipeline_artifacts.py": [
        ROOT / "skills" / "requirements-extract" / "scripts" / "pipeline_artifacts.py",
        ROOT / "skills" / "requirements-critic" / "scripts" / "pipeline_artifacts.py",
        ROOT
        / "skills"
        / "specification-compiler"
        / "scripts"
        / "pipeline_artifacts.py",
    ],
}


def verify_canonical_files() -> list[str]:
    errors: list[str] = []
    for name in COPIES:
        source = CANONICAL / name
        if not source.is_file():
            errors.append(f"missing canonical file: {source}")
            continue
        if source.suffix == ".json":
            try:
                json.loads(source.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid canonical JSON {source}: {exc}")
    return errors


def synchronize(check: bool) -> list[str]:
    errors = verify_canonical_files()
    if errors:
        return errors
    for name, targets in COPIES.items():
        source = CANONICAL / name
        source_bytes = source.read_bytes()
        for target in targets:
            if check:
                if not target.is_file():
                    errors.append(f"missing contract copy: {target}")
                elif target.read_bytes() != source_bytes:
                    errors.append(f"stale contract copy: {target}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    errors = synchronize(args.check)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if args.check:
        print("PASS contract copies")
    else:
        print("SYNCHRONIZED contract copies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
