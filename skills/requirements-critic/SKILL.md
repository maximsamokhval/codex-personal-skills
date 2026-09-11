---
name: requirements-critic
description: Critically assess requirements.json for ambiguity, contradictions, hidden assumptions, undefined terms, and testability gaps, then produce editable review.json and generated review.md. Use as the second stage before explicit human approval and specification compilation.
---

# Requirements Critic

Perform an independent destructive review of `requirements/v1`. Keep `requirements.json` immutable and make review decisions explicit in `requirements-review/v1`.

## Output language

- Produce all natural-language output in Ukrainian.
- Preserve exact source quotations in their original language when required as evidence.
- Preserve requirement IDs, code, API names, file names, commands, and machine-readable values.

## Inputs and artifacts

Use project-defined locations. Otherwise use:

- input: `docs/requirements/requirements.json`;
- editable review: `docs/requirements/review.json`;
- generated view: `docs/requirements/review.md`;
- approved snapshot: `docs/requirements/baseline.json`.

Before acting, read the relevant contracts:

- [requirements.schema.json](references/contracts/requirements.schema.json);
- [review.schema.json](references/contracts/review.schema.json);
- [baseline.schema.json](references/contracts/baseline.schema.json) only for approval.

## Review workflow

1. Validate the immutable input:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" validate requirements "<requirements.json>"
   ```

2. Calculate its SHA-256:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" digest "<requirements.json>"
   ```

3. Build a staged `requirements-review/v1` JSON tied to that digest. New findings start with `status: open`.
4. Validate finding references and the input digest:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" validate review "<staged-review.json>" --requirements "<requirements.json>"
   ```

5. Write the review safely. An existing primary produces `review.candidate.json` or the next numbered candidate.

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" safe-write review "<staged-review.json>" "<output-dir>/review.json"
   ```

6. Render the written JSON to the matching Markdown name:

   ```text
   python "<skill-dir>/scripts/pipeline_artifacts.py" render review "<written-review.json>" --requirements "<requirements.json>" --output "<matching-review.md>"
   ```

On a repeat review, compare the current review with the new findings. Preserve the ID for the same defect. Carry an `accepted-risk` decision only while its recorded scope still applies; retain a resolved finding only while the defect remains absent, and reopen it with an explanation if it reappears. Create a new ID for a materially different defect. Never overwrite the primary review without explicit authorization.

## Review rules

- Review both individual requirements and interactions across the complete set.
- Cite affected requirement IDs and exact wording or source evidence for every finding.
- For critical wording ambiguity, test at least three materially different interpretations. Report ambiguity when observable outcomes differ.
- Check contradictions across goals, rules, behavior, constraints, actors, lifecycle states, permissions, thresholds, timing, ownership, and dependencies.
- Find hidden assumptions, undefined terms, non-observable statements, missing failure and recovery behavior, boundary cases, and concurrency gaps.
- Use finding types `LOCAL`, `CROSS`, or `MISSING` and severities `blocker`, `risk`, or `note`.
- Keep a finding `open` until a changed requirement is re-reviewed successfully.
- Set `resolved` only after the defect no longer exists and record who, when, and why.
- Set `accepted-risk` only from an explicit human decision and record who, when, and why.

Do not mutate requirements, invent the missing behavior, choose architecture, or approve on the user's behalf.

## Explicit approval

Offer approval only when the current review matches the current requirements, no blocker remains open, and no `OPEN-*` item remains unresolved. Create a baseline only after the user explicitly approves the named version:

```text
python "<skill-dir>/scripts/pipeline_artifacts.py" approve --requirements "<requirements.json>" --review "<review.json>" --approved-by "<person>" --approved-at "<ISO-8601>" --scope "<scope>" --output "<baseline.json>"
```

The command refuses stale inputs, unresolved open items, open blockers, or an existing baseline path. Report the exact created path and hashes.

Finish ordinary review with one verdict: `готово до затвердження людиною`, `потребує усунення суперечностей`, or `недостатньо вихідних даних`.
