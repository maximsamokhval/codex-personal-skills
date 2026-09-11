---
name: iso-29148-requirements
description: Extract, normalize, and trace a set of requirements from provided text or local PDF, DOCX, XLSX, Markdown, and TXT materials, then produce a requirements register and BRS/StRS/SyRS/SRS package. Use when mining multiple passages or existing project materials into a traceable register or specification package informed by public ISO/IEC/IEEE 29148:2018 principles. Excludes isolated sentence editing, blank-project interview elicitation, and clause-level compliance certification.
---

# ISO 29148 Requirements

Turn existing project evidence into a traceable requirements package without inventing missing facts.

## Rights boundary

Use the independently written profile in this skill and public standards metadata only. Treat publisher copies of ISO, IEC, or IEEE standards as excluded sources. If such a publication appears among project inputs, skip it, identify it in the source inventory in `requirements-register.md`, record the reason in `open-issues.md`, and continue with eligible project materials. Never claim certification, normative conformity, or clause-level coverage.

Describe the result as:

> Structured using a practical method informed by publicly described principles of ISO/IEC/IEEE 29148:2018; this is not a certification or normative conformity assessment.

## Route the task

- For pasted text or local source files, read [references/extraction.md](references/extraction.md), [references/normalization-profile.md](references/normalization-profile.md), [references/data-model.md](references/data-model.md), and [references/deliverables.md](references/deliverables.md).
- For an existing `requirements.json`, read [references/data-model.md](references/data-model.md) and [references/deliverables.md](references/deliverables.md). Read the extraction or normalization references only when the user also asks to revisit source evidence or wording.
- For a review-only request, analyze the existing register against the normalization profile and return a read-only report without writing files. Preserve IDs and evidence. Produce a new versioned package only when the user explicitly asks for files; replace an existing package only when the user explicitly requests replacement.

## Process source materials

1. Inventory every input before extraction. Assign source IDs and record the locator scheme appropriate to each format.
2. Confirm that the host can read each format. Use the host's text, document, PDF, spreadsheet, or OCR capability. Mark unavailable, encrypted, empty, or damaged inputs as skipped and request text or CSV export; never imply they were analyzed.
3. Extract source-backed candidates before rewriting them. Keep requirements separate from goals, assumptions, decisions, definitions, and out-of-scope statements.
4. Normalize and classify candidates using the quality profile. Combine only exact or trivially equivalent repeats before assigning stable requirement IDs. Keep plausible duplicates and all conflicts separate for human review.
5. Build one canonical UTF-8 `requirements.json` exactly as defined in the data-model reference. Every requirement needs source evidence and a precise locator. Unsupported ideas become issues, not requirements.
6. Treat `<skill-dir>` below as the directory containing this loaded `SKILL.md`. Run structural validation:

   ```text
   python "<skill-dir>/scripts/validate_requirements.py" "<requirements.json>"
   ```

7. Correct structural errors in the JSON and validate again. Preserve semantic uncertainty as coded findings and issues rather than filling gaps.
8. Render the complete package only after validation succeeds:

   ```text
   python "<skill-dir>/scripts/render_requirements.py" "<requirements.json>"
   ```

   Pass `--output <directory>` only when the user selected a destination. Pass `--force` only after an explicit request to replace existing artifacts.

## Quality gate

Track quality separately from the decision disposition. Set `quality_status` to `needs-review` when a requirement has a blocking ambiguity, unresolved compound behavior, unverifiability, source conflict, unclear level, unsupported inference, or unknown feasibility. Keep it in the consolidated register and the relevant specification's review appendix; exclude it from the main requirements section. Use `quality_status: normalized` only when no blocking finding remains.

Set `disposition` to `proposed` by default. Set it to `accepted`, `rejected`, or `superseded` only from an explicit source or user decision. A decision does not erase a quality defect: for example, an accepted but ambiguous requirement remains `quality_status: needs-review` until the defect is resolved.

## Output behavior

- Produce all eight artifacts defined in the deliverables reference for a full source-processing run.
- Default normalized content to the user's requested language; otherwise use the conversation language. Preserve evidence excerpts in their source language. The renderer localizes structural text for English and Russian and reports an explicit English-label fallback for other languages.
- Use a fresh timestamped output directory by default. Never overwrite a non-empty destination implicitly.
- Report processed, partial, and skipped sources; counts by level, quality status, and disposition; open gaps, conflicts, plausible duplicates, assumptions, and every output path.

## Completion criteria

For a full source-processing or package-producing request, finish only when validation succeeds, all eight artifacts exist, every requirement traces to valid source evidence, blocking semantic findings are visibly gated, and skipped inputs and unresolved issues are reported. If usable evidence yields no requirements, produce an empty validated package with explicit coverage gaps instead of fabricating content.

For a review-only request that does not ask for files, finish when the read-only report identifies quality findings, traceability gaps, conflicts, and recommended corrections without mutating the input or writing a package.
