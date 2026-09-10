---
name: specification-compiler
description: Compile approved, traceable requirements into invariants, observable acceptance criteria, and failure scenarios. Use only after unresolved requirements and blocking review findings have been explicitly resolved or accepted.
---

# Specification Compiler

Convert an approved requirements model into verification-ready artifacts while preserving traceability.

This is a compiler, not a requirements author. It must not invent behavior, resolve business ambiguity, or silently expand scope.

## Output language

- Produce all natural-language output in Ukrainian.
- Do not switch to the language of the source material.
- Preserve exact source quotations in their original language when required for traceability.
- Do not translate requirement IDs, code, API names, file names, commands, protocol names, or machine-readable values.

## Entry gate

Before compiling, locate the requirements baseline defined by the project instructions.

If no project-specific location is defined, use:

`docs/requirements/baseline.yaml`

The baseline must contain:

- `version`;
- `status`;
- `approved_by`;
- `approved_at`;
- `requirements_file`;
- `requirements_sha256`;
- `open_blockers`.

The gate passes only when:

- `status` is exactly `approved`;
- `approved_by` is present;
- `approved_at` is present;
- the requirements file exists;
- the current SHA-256 of the requirements file equals `requirements_sha256`;
- `open_blockers` equals `0`;
- relevant requirements have source provenance;
- no unresolved `OPEN-*` or critic blocker affects the compilation scope.

If any condition fails, stop compilation and report the exact failed gate.

Do not infer approval from:

- the absence of comments;
- a file name;
- a completed task;
- a previous conversation;
- an agent statement;
- the existence of requirements alone.

## Compilation rules

- Generate `INV-*` only for properties that must always hold according to the approved requirements.
- For every invariant state its scope, lifecycle/state boundary, checkable condition, and violation condition.
- Generate `AC-*` for observable behavior.
- Prefer `WHEN <event or condition>, THE SYSTEM SHALL <observable outcome>`.
- Use Given/When/Then when preconditions, action, and result require clearer separation.
- Generate `FAIL-*` for expected handling of invalid input, unavailable dependencies, rejected authorization, timeout, capacity or boundary breach, conflict, concurrency, or recovery paths only when supported by approved requirements.
- Every output item must trace to one or more approved `BG-*`, `BR-*`, `FR-*`, `NFR-*`, or `CON-*` IDs. If the input does not specify behavior, emit a compilation gap instead of fabricating an invariant, criterion, or failure scenario.
- Preserve quantifiers, values, actors, authorization, timing, ownership, states, and transitions.
- A testable restatement may clarify syntax but may not expand semantic scope.
- Do not turn a business goal alone into detailed system behavior unless an approved requirement or business rule provides that behavior.

## Output

Return four sections.

### 1. Compilation gate

Report:

- baseline version;
- approved by;
- approved at;
- requirements file;
- hash verification result;
- compilation scope;
- gate result: `PASS` or `FAIL`.

### 2. Invariants

Produce `INV-*` entries containing:

- statement;
- scope;
- checkable condition;
- violation condition;
- source requirement IDs.

### 3. Acceptance criteria

Produce `AC-*` entries in observable form with source requirement IDs.

### 4. Failure scenarios and gaps

Produce:

- `FAIL-*` entries for supported failure/recovery behavior;
- `GAP-*` entries wherever approved requirements are insufficient for safe compilation.

Finish with the traceability matrix:

| Approved requirement | INV | AC | FAIL | Gaps |
|---|---|---|---|---|
| FR-012 | INV-004 | AC-021, AC-022 | FAIL-006 | — |

The output supports QA and test design.

Do not select test frameworks.
Do not write tests.
Do not design architecture.
Do not implement production code.
