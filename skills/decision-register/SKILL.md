---
name: decision-register
description: Create or update a digest-bound decision-register.json from requirements/v1 and requirements-review/v1, tracking source-clause dispositions and ownership without treating proposals as approvals.
---

# Decision Register

Use this skill when a project needs a reviewable decision inventory between requirements criticism and human ratification. `requirements.json` remains the requirements source of truth; this register records decisions and assignments separately. Read the [decision register contract](references/decision-register.schema.json), plus the [requirements](references/contracts/requirements.schema.json) and [review](references/contracts/review.schema.json) contracts before creating or editing an artifact.

## Workflow

1. Validate current `requirements.json` and `review.json` with the bundled pipeline tool. A review whose `requirements_sha256` differs from the raw SHA-256 of the requirements file needs a fresh critic pass before this register is drafted.
2. Choose an explicit scope of requirement IDs and `OPEN-*` IDs. Use `draft` to create one row for every selected requirement, every selected open item, and every source clause named by selected requirements' `attributes.source_id` or `attributes.source_ids`. The draft marks every clause `pending`, copies each `OPEN` status from `requirements.json`, and leaves owners unassigned.
3. Read the cited source and actual human decisions. Change a clause to `provisional`, `adopted`, `accepted-risk`, `rejected`, or `deferred` only when a cited decision supports that exact scope and authority. Record a review trigger for provisional, accepted-risk, and deferred decisions. An `OPEN` with `status: resolved` in the requirements still needs an explicit ownership assignment if the register's scope includes it.
4. Validate the JSON against both inputs, then render its Markdown view. The validator enforces raw-byte digests, exact scope coverage, known IDs, source-clause mapping, and evidence for non-pending dispositions and assignments. `render` validates first and writes only the requested output path.
5. Report unresolved rows, the people or authorities whose action is needed, and the exact input digests. A proposed or provisional rule does not close an `OPEN`, a critic finding, or a business approval gate.

```text
python <skill-dir>/scripts/pipeline_artifacts.py validate requirements <requirements.json>
python <skill-dir>/scripts/pipeline_artifacts.py validate review <review.json> --requirements <requirements.json>
python <skill-dir>/scripts/decision_register.py draft --requirements <requirements.json> --review <review.json> --requirement-pattern <regex> --open-pattern <regex> --output <decision-register.json>
python <skill-dir>/scripts/decision_register.py validate --requirements <requirements.json> --review <review.json> --register <decision-register.json>
python <skill-dir>/scripts/decision_register.py render --requirements <requirements.json> --review <review.json> --register <decision-register.json> --output <decision-register.md>
```

Use Ukrainian for natural-language field values and generated explanations when the project requires it. Preserve source IDs, exact quotations, and machine values. Keep the register portable: project-specific authority names, source-clause IDs, and candidate feature mappings belong in the generated project artifact, not in this skill.
