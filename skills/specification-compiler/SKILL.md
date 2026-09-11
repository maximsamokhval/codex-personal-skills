---
name: specification-compiler
description: Compile an explicitly approved requirements/v1 baseline into editable specification.json and generated specification.md with traceable invariants, acceptance criteria, failure scenarios, and gaps. Use as the third stage after requirements criticism and human approval.
---

# Specification Compiler

Compile an approved requirements model into verification-ready `requirements-specification/v1` artifacts. This is a compiler, not a requirements author: insufficient input becomes a `GAP-*`, never invented behavior.

## Output language

- Produce all natural-language output in Ukrainian.
- Preserve source quotations when required for traceability.
- Preserve IDs, code, API names, file names, commands, protocols, and machine-readable values.

## Inputs and artifacts

Use project-defined locations. Otherwise use:

- `docs/requirements/requirements.json`;
- `docs/requirements/review.json`;
- `docs/requirements/baseline.json`;
- `docs/requirements/specification.json` — editable source of truth;
- `docs/requirements/specification.md` — generated view.

Read all bundled contracts before compiling:

- [requirements.schema.json](references/contracts/requirements.schema.json);
- [review.schema.json](references/contracts/review.schema.json);
- [baseline.schema.json](references/contracts/baseline.schema.json);
- [specification.schema.json](references/contracts/specification.schema.json).

## Entry gate

Run the deterministic gate before drafting output:

```text
python "<skill-dir>/scripts/pipeline_artifacts.py" gate --requirements "<requirements.json>" --review "<review.json>" --baseline "<baseline.json>"
```

The gate must pass. It verifies supported contracts, structural and referential integrity, explicit approval, zero open blockers, no unresolved open items, matching versions, and current SHA-256 values. If it fails, stop and report every failed condition. Do not infer approval from file names, previous conversations, task completion, or the existence of artifacts.

## Compilation workflow

1. Run the entry gate.
2. Calculate the requirements and baseline digests with the `digest` command.
3. Build a staged `requirements-specification/v1` JSON containing those exact hashes.
4. Validate structure, hashes, and source requirement references:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" validate specification "<staged-specification.json>" --requirements "<requirements.json>" --baseline "<baseline.json>"
   ```

5. Write it safely. An existing primary produces `specification.candidate.json` or the next numbered candidate.

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" safe-write specification "<staged-specification.json>" "<output-dir>/specification.json"
   ```

6. Validate and render the actual written file to the matching Markdown name:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" render specification "<written-specification.json>" --requirements "<requirements.json>" --baseline "<baseline.json>" --output "<matching-specification.md>"
   ```

7. Report the gate result, input hashes, actual output paths, counts of `INV-*`, `AC-*`, `FAIL-*`, and `GAP-*`, and uncovered approved requirements.

## Compilation rules

- Generate `INV-*` only for properties that approved requirements say must always hold. Include scope, checkable condition, and violation condition.
- Generate observable `AC-*`; prefer `WHEN <event or condition>, THE SYSTEM SHALL <outcome>` or Given/When/Then when clearer.
- Generate `FAIL-*` only for failure or recovery behavior supported by approved requirements.
- Create `GAP-*` when approved requirements do not support safe compilation.
- Every output item must reference one or more approved `BG-*`, `BR-*`, `FR-*`, `NFR-*`, or `CON-*` IDs.
- Preserve quantifiers, values, actors, authorization, timing, ownership, states, and transitions.
- Include one traceability row for every requirement in the compilation scope, even when its only result is a gap.

Do not select test frameworks, write tests, design architecture, resolve business ambiguity, or implement production code.

Finish only when the JSON validates, Markdown is regenerated from it, all output references resolve, and the approved scope is covered by traceability rows.
