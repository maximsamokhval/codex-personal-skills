# Renderer input: ucd-status/v1

This is an agent-inspected snapshot, not an automated code coverage report.
All displayed strings are plain text. Never include secrets or personal data.
Keep locators relative to the inspected project or use public source URLs;
avoid local usernames in reusable artifacts.

Required top-level fields:

- `schema_version`: `ucd-status/v1`.
- `title`, `language`: project title and BCP-47 language tag.
- `snapshot`: `checked_at` (ISO-8601 with timezone), `revision`, `worktree`,
  `tracker` (tool and observed freshness, or unavailable).
- `labels`: localized `implemented`, `in_progress`, `pending`, `unknown`,
  `traceability`, `requirements`, `tasks`, `evidence`, `notes`, `no_requirements`.
- `sources`: objects with unique `id` and nonempty `locator`; optional `sha256`
  is the raw-file SHA-256, recomputed for this inspection.
- `requirements`: objects with unique `id` and registered `source` ID.
  Register only current requirements; retired IDs may occur in explanatory
  notes, not as current coverage references.
- `actors`: objects with unique `id`, `label`, and registered `source` ID.
- `views`: objects with unique `id`, `title`, `system`, nonempty `actors` (actor
  IDs), and nonempty `cases`. Keep at most 3 actors and 8 cases per view for
  legibility; split larger groups. This is a renderer limit, not a domain limit.
- `notes`: list of inspection limitations, OPEN questions, and source conflicts.

Each case has `id`, `label`, `status`, `actors`, `requirements`, `tasks`,
`evidence`, and `notes` (a string). A repeated case ID across views must carry
identical data; reuse denotes the same goal, not independent coverage.

Case `requirements` and `actors` are lists of registered IDs. Actors must also
belong to the view. With no requirement source, use an empty requirements list
and explain the missing authority; such a case is `unknown`.

Case `tasks` is a list of `{id, status, source, superseded}`. `source` is a
registered tracker snapshot source; `superseded` is boolean. Normalize active
work to `in_progress`; preserve other tracker states as strings. An active task
from another branch can justify gray, never green in this checkout.

Case `evidence` is a list of `{kind, source, locator, detail}`. `source` is
registered; `locator` points to a precise file/symbol/line or public artifact;
`detail` states the observation, inspection/execution mode, and scope.

Kinds: `code`, `wiring`, `test`, `work`, `gap`, `other`.

- `implemented` requires current requirement IDs and `code`, `wiring`, `test`
  evidence. Test source inspection and an executed passing test are different;
  state which supports the status. Do not claim production verification from
  static inspection. Failed relevant tests invalidate a green claim.
- `in_progress` requires current requirement IDs and a non-superseded
  `in_progress` task or a `work` observation of actual WIP.
- `pending` requires current requirement IDs and a concrete `gap` observation.
- `unknown` needs an explanatory note, not fabricated evidence.

Minimal synthetic example (replace all evidence after inspecting the project):

```json
{
  "schema_version": "ucd-status/v1",
  "title": "Example service", "language": "en",
  "snapshot": {
    "checked_at": "2026-01-01T12:00:00+00:00",
    "revision": "example-revision", "worktree": "clean",
    "tracker": "not available"
  },
  "labels": {
    "implemented": "Implemented", "in_progress": "In progress",
    "pending": "Pending", "unknown": "Unknown",
    "traceability": "Traceability", "requirements": "Requirements",
    "tasks": "Tasks", "evidence": "Evidence", "notes": "Notes",
    "no_requirements": "Requirement authority unavailable"
  },
  "sources": [{"id": "SRC-1", "locator": "docs/domain.md#reader"}],
  "requirements": [],
  "actors": [{"id": "ACT-1", "label": "Reader", "source": "SRC-1"}],
  "views": [{
    "id": "reader", "title": "Reader", "system": "Example service",
    "actors": ["ACT-1"],
    "cases": [{
      "id": "UC-1", "label": "Read an item", "status": "unknown",
      "actors": ["ACT-1"], "requirements": [], "tasks": [],
      "evidence": [], "notes": "No approved requirement source was supplied."
    }]
  }],
  "notes": ["Synthetic example, not implementation evidence."]
}
```
