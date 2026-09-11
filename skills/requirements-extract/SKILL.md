---
name: requirements-extract
description: Extract a source-grounded requirements model from raw briefs, specifications, meeting notes, or process descriptions into editable requirements.json and generated requirements.md. Use as the first stage of a controlled requirements pipeline before critique, approval, design, or implementation.
---

# Requirements Extract

Turn supplied source material into a traceable `requirements/v1` JSON model without silently filling gaps. JSON is the source of truth; Markdown is generated from it.

## Output language

- Produce all natural-language output in Ukrainian.
- Preserve exact source quotations in their original language when needed for provenance.
- Preserve code, identifiers, API names, file names, commands, and machine-readable values.

## Artifacts

Use the project-defined location. Otherwise use:

- `docs/requirements/requirements.json` — editable source of truth;
- `docs/requirements/requirements.md` — generated view.

Read [references/contracts/requirements.schema.json](references/contracts/requirements.schema.json) before creating or editing the JSON. Treat `schema_version: requirements/v1` as an exact compatibility boundary.

## Workflow

1. Inventory every supplied source and choose the narrowest available locator: file, section, heading, paragraph, use case, cell range, or quoted fragment.
2. Extract requirements separately from background, examples, rationale, and optional solutions.
3. Build a staged UTF-8 JSON file that conforms to `requirements/v1`.
4. Validate the staged file:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" validate requirements "<staged-json>"
   ```

5. Write it safely:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" safe-write requirements "<staged-json>" "<output-dir>/requirements.json"
   ```

   When the primary JSON exists, the command creates `requirements.candidate.json` or the next numbered candidate. Replace the primary file only after an explicit user request, using `--replace`.

6. Render the JSON path reported by `safe-write`. Use the matching Markdown name; a candidate JSON produces a candidate Markdown view and leaves the primary view unchanged.

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" render requirements "<written-json>" --output "<matching-markdown>"
   ```

7. Report processed and skipped sources, the actual written paths, requirement and open-item counts, and whether the result is primary or candidate.

For an existing `requirements.json` supplied for manual maintenance, validate it first. Regenerate `requirements.md` from the validated JSON; never parse Markdown back into JSON.

## Extraction rules

- Preserve source meaning. Mark each requirement as `explicit` or `derived`.
- Use stable IDs: `BG-*`, `BR-*`, `FR-*`, `NFR-*`, and `CON-*`. Use `OPEN-*` for unresolved questions.
- Every requirement needs a concise normative statement and at least one valid source locator.
- `UNKNOWN -> OPEN`: missing facts, undefined terms, conflicts, and behavior-changing assumptions become open items.
- Preserve actors, conditions, thresholds, time limits, ownership, permissions, states, and constraints.
- Keep distinct requirements separate. Record a proposed solution as a constraint only when the source makes it mandatory.
- A derived requirement must list its supporting references and explain the necessary logical inference. If the inference needs an unstated business premise, create an open item instead.
- Give every open item a severity, status, reason, minimal resolution question, and affected requirement IDs.

## Completion criteria

Finish only when the written JSON validates, every requirement traces to a known source, unresolved uncertainty is visible as `OPEN-*`, and the matching Markdown view exists.

Do not approve requirements, close open items, create acceptance criteria, choose architecture, or implement the system.
