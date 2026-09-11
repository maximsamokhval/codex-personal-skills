# Canonical requirements data model

`requirements.json` is the single source of truth. Encode it as UTF-8 JSON with a top-level object. Scripts may preserve unknown harmless metadata, but producers should use only the fields defined here.

## Root object

Required fields:

| Field | Contract |
| --- | --- |
| `schema_version` | String `1.1`. |
| `profile` | String `public-principles/29148:2018`. |
| `title` | Non-empty project or package title. |
| `language` | Non-empty BCP 47 tag or clear language name. |
| `sources` | Array of source objects. |
| `level_coverage` | Object with exactly `BRS`, `StRS`, `SyRS`, and `SRS`. |
| `context_items` | Array of non-requirement context objects. |
| `requirements` | Array of requirement objects. |
| `relationships` | Array of canonical requirement relationships. |
| `issues` | Array of issues. |

`generated_at` is an optional ISO 8601 timestamp. A renderer must not change it or manufacture one inside the canonical JSON.

## Source

```json
{
  "id": "SRC-001",
  "name": "Product brief.docx",
  "media_type": "docx",
  "path": "docs/Product brief.docx",
  "digest_sha256": null,
  "status": "processed",
  "locator_scheme": "heading path + paragraph/table row",
  "notes": []
}
```

- ID pattern: `SRC-` plus at least three digits.
- `name`, `media_type`, and `locator_scheme` are non-empty strings.
- `status`: `processed`, `partial`, or `skipped`.
- `path` and `digest_sha256` are optional nullable strings; a populated digest uses 64 hexadecimal characters.
- `notes` is an optional array of strings.

## Source reference

```json
{
  "source_id": "SRC-001",
  "locator": "Overview > Availability, paragraph 3",
  "evidence": "The service must remain available during regional maintenance.",
  "ocr": false
}
```

`source_id`, `locator`, and `evidence` are required non-empty strings. `source_id` must exist in `sources` and must not name a source whose status is `skipped`. `ocr` is an optional boolean, defaulting to false.

## Level coverage

Each root `level_coverage` entry has this shape:

```json
{
  "status": "supported",
  "basis": "The sources contain business outcomes.",
  "issue_id": null
}
```

- `status`: `supported`, `gap`, or `not-applicable`.
- `basis`: non-empty explanation grounded in processed sources or declared scope.
- `issue_id`: required string for `gap`, otherwise null. A gap issue must exist and include the same level in `affected_levels`.
- `supported` requires at least one requirement of the level whose `disposition` is neither `rejected` nor `superseded`.
- `gap` and `not-applicable` require no active requirement of the level.

## Context item

```json
{
  "id": "CTX-0001",
  "type": "goal",
  "text": "Reduce manual review effort.",
  "source_refs": [
    {
      "source_id": "SRC-001",
      "locator": "Executive summary, paragraph 2",
      "evidence": "Reduce manual review effort by the operations team.",
      "ocr": false
    }
  ]
}
```

ID pattern: `CTX-` plus at least four digits. `type` is one of `goal`, `assumption`, `decision`, `definition`, or `out-of-scope`. `text` is non-empty and `source_refs` contains at least one valid reference.

## Requirement

```json
{
  "id": "REQ-000001",
  "level": "SyRS",
  "category": "quality",
  "statement": "The service shall remain available during planned maintenance of one region.",
  "source_refs": [
    {
      "source_id": "SRC-001",
      "locator": "Overview > Availability, paragraph 3",
      "evidence": "The service must remain available during regional maintenance.",
      "ocr": false
    }
  ],
  "provenance": "explicit",
  "confidence": "high",
  "rationale": null,
  "stakeholders": ["Operations"],
  "priority": {
    "value": null,
    "basis": null
  },
  "verification": {
    "method": "test",
    "acceptance_criteria": "During planned maintenance of one region, health checks in another region remain successful."
  },
  "quality_status": "normalized",
  "disposition": "proposed",
  "quality_findings": [],
  "decision_basis": null,
  "superseded_by": null
}
```

Rules:

- ID pattern: `REQ-` plus at least six digits. It is opaque and does not encode the current level.
- `level`: `BRS`, `StRS`, `SyRS`, or `SRS`.
- `category`: `functional`, `quality`, `interface`, `data`, `constraint`, `business-rule`, `regulatory`, `transition`, or `other`.
- `statement` is non-empty; `source_refs` contains at least one valid reference.
- `provenance`: `explicit`, `derived`, or `inferred`.
- `confidence`: `high`, `medium`, or `low`.
- `rationale`: string or null. `stakeholders`: array of strings.
- `priority` always contains nullable `value` and `basis`. A value requires a non-empty basis; preserve the source's priority scheme rather than remapping it silently.
- `verification` always contains nullable `method` and `acceptance_criteria`.
- `quality_status`: `normalized` or `needs-review`. This records wording and evidence quality independently of a decision.
- `disposition`: `proposed`, `accepted`, `rejected`, or `superseded`. This records an explicit lifecycle decision independently of quality.
- `quality_findings` is an array defined below.
- `decision_basis`: non-empty for `accepted`, `rejected`, or `superseded`; null for `proposed`.
- `superseded_by`: valid requirement ID when `disposition` is `superseded`; otherwise null.
- An `inferred` requirement always uses `quality_status: needs-review`; capture new evidence or an explicit user statement as a source before reclassifying its provenance.
- A disposition decision does not erase a quality defect. An accepted requirement may still be `needs-review`.
- Requirement objects never store parent, dependency, conflict, or duplicate fields; use `relationships`.

### Quality finding

```json
{
  "code": "ambiguity",
  "severity": "blocking",
  "message": "The phrase 'quickly' has no measurable threshold.",
  "issue_id": "ISS-0001"
}
```

`code` is `ambiguity`, `compound`, `unverifiable`, `conflicting`, `unclear-level`, `unsupported-inference`, `feasibility-unknown`, or `other`. `severity` is `blocking` or `warning`; `message` is non-empty; `issue_id` is a valid issue ID or null. A blocking finding cannot appear when `quality_status` is `normalized`. `quality_status: needs-review` requires at least one blocking finding.

## Relationship

```json
{
  "id": "REL-0001",
  "type": "parent-of",
  "from_id": "REQ-000001",
  "to_id": "REQ-000002",
  "basis": "REQ-000002 allocates the availability behavior to software.",
  "issue_id": null
}
```

- ID pattern: `REL-` plus at least four digits.
- `type`: `parent-of`, `depends-on`, `conflicts-with`, or `duplicates`.
- Endpoints are distinct existing requirement IDs.
- `basis` is non-empty; `issue_id` is a valid issue ID or null.
- Repeated directed edges are invalid. Reverse duplicates are also invalid for symmetric `conflicts-with` and `duplicates` relationships.
- `duplicates` represents a confirmed decision, not mere similarity.
- `conflicts-with` requires a non-null `issue_id`. The linked issue has type `conflict`, names both endpoints in `requirement_ids`, and, while open, both endpoints carry a blocking `conflicting` quality finding.

## Issue

```json
{
  "id": "ISS-0001",
  "type": "ambiguity",
  "severity": "blocking",
  "status": "open",
  "message": "Define a measurable response-time threshold.",
  "source_ids": ["SRC-001"],
  "source_refs": [],
  "requirement_ids": ["REQ-000001"],
  "affected_levels": ["SyRS"],
  "resolution": null
}
```

- ID pattern: `ISS-` plus at least four digits.
- `type`: `gap`, `ambiguity`, `conflict`, `duplicate`, `unreadable-source`, `assumption`, `low-confidence`, `quality`, `decision-required`, or `other`.
- `severity`: `warning` or `blocking`. `status`: `open` or `resolved`.
- `message` is non-empty.
- `source_ids`, `source_refs`, `requirement_ids`, and `affected_levels` are required arrays whose references must exist. Values in `source_ids`, `requirement_ids`, and `affected_levels` do not repeat. `source_ids` may name processed, partial, or skipped sources; use it to identify affected inputs even when no evidence could be read. `source_refs` contains optional evidence detail and cannot refer to a skipped source. Every source named by a `source_ref` must also appear in `source_ids`.
- An `unreadable-source` issue names at least one `partial` or `skipped` source in `source_ids`.
- `resolution` is non-empty when status is `resolved`; otherwise null.
- Every source-stated assumption is a context item. An `assumption` issue is additional and is used only when the assumption is unverified and affects a requirement or pending decision.

## Minimal empty package

Use an empty package when readable evidence yields no requirements. It remains honest by inventorying the processed input and declaring four gaps:

```json
{
  "schema_version": "1.1",
  "profile": "public-principles/29148:2018",
  "title": "Empty evidence result",
  "language": "en",
  "sources": [
    {
      "id": "SRC-001",
      "name": "input.txt",
      "media_type": "txt",
      "path": "input.txt",
      "digest_sha256": null,
      "status": "processed",
      "locator_scheme": "line range",
      "notes": ["Readable source processed; no evidence-backed requirements found."]
    }
  ],
  "level_coverage": {
    "BRS": {"status": "gap", "basis": "No evidence-backed BRS requirement was identified.", "issue_id": "ISS-0001"},
    "StRS": {"status": "gap", "basis": "No evidence-backed StRS requirement was identified.", "issue_id": "ISS-0002"},
    "SyRS": {"status": "gap", "basis": "No evidence-backed SyRS requirement was identified.", "issue_id": "ISS-0003"},
    "SRS": {"status": "gap", "basis": "No evidence-backed SRS requirement was identified.", "issue_id": "ISS-0004"}
  },
  "context_items": [],
  "requirements": [],
  "relationships": [],
  "issues": [
    {"id": "ISS-0001", "type": "gap", "severity": "blocking", "status": "open", "message": "Provide evidence for business requirements.", "source_ids": ["SRC-001"], "source_refs": [], "requirement_ids": [], "affected_levels": ["BRS"], "resolution": null},
    {"id": "ISS-0002", "type": "gap", "severity": "blocking", "status": "open", "message": "Provide evidence for stakeholder requirements.", "source_ids": ["SRC-001"], "source_refs": [], "requirement_ids": [], "affected_levels": ["StRS"], "resolution": null},
    {"id": "ISS-0003", "type": "gap", "severity": "blocking", "status": "open", "message": "Provide evidence for system requirements.", "source_ids": ["SRC-001"], "source_refs": [], "requirement_ids": [], "affected_levels": ["SyRS"], "resolution": null},
    {"id": "ISS-0004", "type": "gap", "severity": "blocking", "status": "open", "message": "Provide evidence for software requirements.", "source_ids": ["SRC-001"], "source_refs": [], "requirement_ids": [], "affected_levels": ["SRS"], "resolution": null}
  ]
}
```
