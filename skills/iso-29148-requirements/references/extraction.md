# Source extraction

Use this reference when turning pasted text or local files into source-backed candidates.

## Inventory first

Create the complete source inventory before extracting requirements. Allocate `SRC-001`, `SRC-002`, and so on in the order supplied. Record the original display name, media type, optional path and SHA-256 digest, processing status, and locator scheme. A digest identifies a source version; it does not replace a human-readable locator.

Use these locator conventions:

| Input | Locator |
| --- | --- |
| Pasted text | `block <n>, lines <start>-<end>` |
| PDF | `page <n>` plus heading/table/figure when available |
| DOCX | heading path plus paragraph or table/row |
| XLSX | quoted sheet name plus cell or range, such as `'Scope'!B7:D7` |
| Markdown/TXT | heading path when available plus line range |

The locator must let a reviewer return to the evidence. Never use a bare filename as the only locator.

## Reader contract

Use the Codex host's appropriate text, document, PDF, spreadsheet, or OCR reader. Record:

- `processed` when the relevant content and structure were read;
- `partial` when some content, pages, sheets, or structure could not be recovered;
- `skipped` when usable content could not be read.

Mark OCR-derived source references with `ocr: true`. State which source was partial or skipped and why. Ask for text or CSV export when the host lacks a reader. Continue with readable sources, but do not imply full-set coverage.

Apply the rights boundary in `SKILL.md` before sending content to any reader. Project plans, contracts, meeting notes, product documents, and backlogs are eligible project sources. Publisher copies of ISO, IEC, or IEEE standards are outside this skill's default input scope.

## Two-pass extraction

First preserve what the source says; then decide what it is.

### Pass 1: evidence capture

Capture concise evidence spans with their source ID and locator. Keep qualifiers, numbers, units, conditions, exceptions, modal verbs, actors, objects, and cross-references. Preserve the source language. Tables require row/column context, not isolated cell values.

### Pass 2: candidate classification

Classify each captured item before normalization:

- requirement candidate;
- goal or desired outcome;
- assumption;
- decision;
- definition;
- out-of-scope statement;
- ambiguity, conflict, or missing information.

Store non-requirement facts as `context_items` or `issues`; do not force them into requirement grammar. Store every source-stated assumption as an `assumption` context item. Also create an `assumption` issue only when an unverified assumption affects a requirement or pending decision. A stakeholder need that constrains the solution may become an StRS candidate. A business goal may become BRS only when the source expresses an expected outcome or constraint strongly enough to verify.

## Evidence discipline

- Every requirement keeps at least one `source_ref` with `source_id`, `locator`, and concise `evidence`.
- A rewritten statement never becomes evidence for itself.
- `explicit` means directly stated by the source.
- `derived` means a traceable decomposition or consequence of source-backed material.
- `inferred` means a plausible interpretation requiring confirmation; always set `quality_status` to `needs-review`.
- An idea with no source basis becomes an issue or question, never a requirement.
- Preserve all evidence when exact duplicates are consolidated.

## Duplicates and conflicts

Before stable requirement IDs exist, combine only verbatim repeats or trivially equivalent candidates whose actor, behavior, object, qualifiers, and conditions agree. Keep plausible duplicates separate and create a `duplicate` issue. Keep conflicting candidates separate, create a `conflict` issue, and add a `conflicts-with` relationship after IDs are assigned. The relationship must point to that issue, and the issue must name both requirements. While the conflict is open, both requirements carry a blocking `conflicting` quality finding.

## Large source sets

Assign all source IDs and locator schemes before batching. Each batch emits candidates with source references but no final requirement IDs. After all batches finish, perform one global pass for exact repeats, plausible duplicates, conflicts, terminology drift, and cross-source omissions. Assign stable IDs only after that pass.

When revising an existing register, match records by existing ID first. Preserve IDs for unchanged meanings; represent user-approved replacements through decision basis and supersession rather than silently renumbering.
