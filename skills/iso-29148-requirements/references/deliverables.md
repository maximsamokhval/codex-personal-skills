# Deliverables and rendering

Use the renderer only after canonical JSON passes structural validation. In the commands below, `<skill-dir>` is the directory containing the loaded `SKILL.md`.

## Commands

```text
python "<skill-dir>/scripts/validate_requirements.py" "<requirements.json>"
python "<skill-dir>/scripts/render_requirements.py" "<requirements.json>"
```

Optional rendering arguments:

```text
--output <directory>  Use the user's chosen destination.
--force               Replace only the eight known artifact files in a non-empty destination.
```

Use `--force` only after an explicit replacement request. It preserves unrelated files in the destination.

## Default destination

Without `--output`, write beneath the current workspace:

```text
outputs/iso-29148-requirements/YYYYMMDD-HHMMSSZ/
```

The timestamp is UTC. If that path exists, append `-01`, `-02`, and the next available numeric suffix. Re-rendering an existing canonical JSON still creates a fresh timestamped destination. Rendering never changes IDs.

## Artifact set

Produce exactly these eight files:

1. `requirements.json`
2. `requirements-register.md`
3. `BRS.md`
4. `StRS.md`
5. `SyRS.md`
6. `SRS.md`
7. `traceability-matrix.md`
8. `open-issues.md`

Write UTF-8 as one transactional artifact set. Under explicit `--force`, back up and restore the eight known prior artifacts if replacement fails; preserve unrelated files. Render records in a total natural ID order with a lexical tie-breaker so repeated rendering is deterministic. The emitted canonical JSON may sort top-level ID-bearing record collections, but it preserves the order of nested arrays. Formatting it with indentation is allowed.

Escape source-controlled Markdown table content, including pipes, backslashes, and raw HTML characters. Renderer-owned line breaks may use `<br>` after source text has been escaped.

## Language

The renderer localizes its structural headings, labels, boilerplate, and notice for English and Russian. Treat `ru`, tags beginning with `ru-`, `Russian`, and `Русский` as Russian; treat `en`, tags beginning with `en-`, and `English` as English. For another language, preserve normalized statements and evidence in that language, fall back to English structural labels, and emit a visible validator/renderer warning in both the CLI report and `open-issues.md`.

Every Markdown artifact carries this notice near the top:

> Structured using a practical method informed by publicly described principles of ISO/IEC/IEEE 29148:2018; this is not a certification or normative conformity assessment.

## Requirements register

Include:

- title, language, profile, and optional generation timestamp;
- counts by level, quality status, disposition, provenance, and source-processing status;
- source inventory with locator schemes and partial/skipped notes;
- one detailed record per requirement, including evidence, locators, provenance, confidence, rationale, stakeholders, priority, verification, quality findings, and decision data;
- source-backed context items;
- relationship summary;
- direct links or IDs for related issues.

Keep rejected and superseded records visible in the register for history. Label them clearly.

## Level specifications

Create one file for each level. Include coverage status and basis.

- Put active (`proposed` or `accepted`) requirements with `quality_status: normalized` in the main requirements section.
- Put active requirements with `quality_status: needs-review` in a clearly labelled review appendix with blocking findings and issue IDs.
- Keep requirements whose `disposition` is `rejected` or `superseded` in the consolidated register rather than the active level specification.
- For `gap`, link to the coverage issue ID and state that evidence is missing.
- For `not-applicable`, state the evidence-backed scope basis without creating a gap.
- For a `supported` level containing only active `needs-review` records, keep the main section empty and make the review appendix prominent.

## Traceability matrix

Include a requirement-to-source table with one row per source reference: requirement ID, level, quality status, disposition, source ID, source-processing status, locator, provenance, and OCR flag. Then include the canonical relationship table with relationship ID, type, endpoints, basis, and issue ID.

The matrix exposes missing or partial coverage; it never invents parent-child links.

## Open issues

Render all issues with severity, status, affected sources from `source_ids`, available evidence details from `source_refs`, requirements, and levels. Add a flattened quality-findings table containing requirement ID, code, severity, message, and issue link; show an explicit unlinked marker when `issue_id` is null. List every assumption context item separately, alongside any related open assumption issue. Include structural-validator and renderer warnings in a separate generated-warnings section. Make skipped/partial sources, gaps, conflicts, plausible duplicates, assumptions, low-confidence interpretations, and blocking quality findings easy to scan.

## Completion report

After rendering, report:

- the canonical JSON path and output directory;
- processed, partial, and skipped source counts;
- requirement counts by level, quality status, and disposition;
- open blocking and warning issue counts;
- validator warnings;
- the eight artifact paths.

Never report success if structural validation failed or any artifact is missing.
