---
name: requirements-extract
description: Extract a source-grounded requirements model from raw briefs, specifications, meeting notes, or process descriptions. Use before design or implementation when the requested scope is not yet a controlled specification.
---

# Requirements Extract

Turn the supplied source material into a traceable model of what is stated, without silently filling gaps.

## Output language

- Produce all natural-language output in Ukrainian.
- Do not switch to the language of the source material.
- Preserve exact source quotations in their original language when needed for provenance.
- Do not translate code, identifiers, API names, protocol names, file names, commands, or machine-readable values.

## Extraction rules

- Preserve the source's meaning. Separate an explicit statement from a derived requirement or interpretation.
- Every entry must include its stable ID, concise normative statement, source location, and `explicit` or `derived` provenance.
- Identify the source using the document/file name and the narrowest available location: section, heading, paragraph, use case, or quoted fragment.
- Use only these categories: `BG-*` business goals, `BR-*` business rules, `FR-*` functional requirements, `NFR-*` non-functional requirements, `CON-*` constraints, and `OPEN-*` unresolved questions.
- `UNKNOWN -> OPEN`: missing facts, undefined terms, conflicting statements, and assumptions that would change behavior become `OPEN-*`; never turn them into a "reasonable assumption".
- Preserve meaningful qualifiers, actors, conditions, thresholds, time limits, data ownership, permissions, lifecycle states, and constraints.
- Do not collapse distinct requirements into one vague summary.
- Distinguish requirements from background, examples, rationale, and proposed solutions.
- Record a proposed solution as a constraint only when the source makes it mandatory.

## Derived requirements

A `derived` requirement is allowed only when it logically follows from explicit source statements without introducing an unstated business premise.

For every derived requirement include:

- supporting source fragments or requirement IDs;
- a concise `Derivation` explaining the logical step;
- why the derived behavior is necessary to preserve the source meaning.

If the derivation requires an unstated premise, business choice, threshold, policy, priority, exception, or interpretation that could change observable behavior, do not create the derived requirement. Create an `OPEN-*` item instead.

## Output

Begin with a short scope-and-source note.

Then produce a requirements register:

| ID | Statement | Provenance | Source |
|---|---|---|---|
| FR-001 | ... | explicit | Brief, section ... |

For every `derived` item, immediately include:

**Derivation:** supporting IDs/source → logical inference.

List `OPEN-*` prominently. For every open item include:

- what is unknown or ambiguous;
- why the answer matters;
- the minimal question needed to resolve it;
- which requirements or process areas it affects.

Finish with traceability observations:

- uncovered source sections;
- conflicting statements;
- derived requirements requiring human review;
- items that must be resolved before design.

Do not declare a requirements set approved.
Do not choose an architecture.
Do not create acceptance criteria.
Do not resolve `OPEN-*` items yourself.
