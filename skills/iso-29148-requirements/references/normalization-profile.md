# Practical normalization profile

This is an independently written engineering method informed by public descriptions of ISO/IEC/IEEE 29148:2018. It is not the standard, a clause checklist, or a conformity assessment.

## Level classification

Assign the highest-confidence level supported by the source:

- `BRS`: business or mission outcome, success condition, policy, or enterprise constraint.
- `StRS`: stakeholder need, externally observable capability, operating condition, or stakeholder constraint.
- `SyRS`: behavior, quality, interface, or constraint allocated to the system as a whole.
- `SRS`: behavior, quality, data rule, interface, or constraint allocated specifically to software.

Do not infer a lower-level design merely to fill all four documents. Connect decomposed levels with canonical `parent-of` relationships. When the scope explicitly makes a level irrelevant, mark it `not-applicable` with an evidence-backed basis. When evidence is simply missing, mark it `gap` and link an open issue.

## Requirement form

Prefer one testable obligation per record:

```text
<responsible subject> shall <observable behavior> [object] [condition] [measurable qualifier].
```

Use the equivalent natural construction in the output language, for example `Система должна ...` in Russian. Preserve domain terminology from defined source terms. Keep rationale, examples, implementation suggestions, and commentary outside the normative statement.

Split a compound statement when its obligations could be implemented, prioritized, accepted, changed, or verified independently. Preserve a parent relationship or shared rationale when splitting would otherwise lose context.

## Quality review

Review each record for the following practical properties:

- **Supported:** evidence justifies the obligation and its level.
- **Atomic:** one independently manageable obligation.
- **Clear:** one reasonable interpretation of actor, behavior, object, and condition.
- **Complete enough:** required conditions, units, thresholds, and exceptions are present or explicitly unresolved.
- **Feasible:** no known technical, legal, schedule, or resource impossibility.
- **Objectively verifiable:** a reviewer can identify observable evidence of satisfaction.
- **Consistent:** no unresolved contradiction with another requirement or source.
- **Traceable:** source evidence and any inter-requirement derivation are explicit.

This review is semantic. Record defects rather than polishing them away with invented detail.

## Provenance and confidence

- `explicit`: a direct source obligation or constraint.
- `derived`: a justified decomposition or consequence. State the derivation basis through sources and relationships.
- `inferred`: a plausible interpretation not yet confirmed. Always use `quality_status: needs-review`.

Use `high`, `medium`, or `low` confidence to communicate interpretation risk. Confidence does not substitute for provenance.

## Categories

Choose one: `functional`, `quality`, `interface`, `data`, `constraint`, `business-rule`, `regulatory`, `transition`, or `other`. The category is organizational; it does not change the requirement level.

## Quality gate

Use these coded findings:

| Code | Blocking condition |
| --- | --- |
| `ambiguity` | Actor, behavior, object, qualifier, or condition has competing interpretations. |
| `compound` | Independently manageable obligations remain joined. |
| `unverifiable` | No objective verification can be defined without inventing facts. |
| `conflicting` | Source-backed statements remain mutually incompatible. |
| `unclear-level` | Allocation to BRS/StRS/SyRS/SRS is not supported. |
| `unsupported-inference` | The proposed obligation goes beyond its evidence. |
| `feasibility-unknown` | Available material cannot support a feasibility judgment that matters to use. |
| `other` | A specific defect is explained in the finding message. |

A blocking finding requires `quality_status: needs-review`. Put active records with this quality status in the relevant specification's review appendix, not its main requirements section. Use `quality_status: normalized` when no blocking finding remains. Track the independent `disposition` as `proposed` by default; use `accepted`, `rejected`, or `superseded` only when an explicit source or user decision supplies `decision_basis`. An acceptance decision does not remove a blocking quality finding.

Missing rationale, stakeholder, priority, verification method, or acceptance criteria may remain a warning when the requirement is still unambiguous and objectively verifiable. Never manufacture values to clear a warning.

## Verification information

State a verification method and measurable acceptance criteria when supported. A method may be a test, inspection, analysis, demonstration, review, or domain-specific procedure. The criterion must describe observable evidence, threshold, state transition, or expected result. If it cannot be written without new facts, leave it null, add the appropriate finding or issue, and preserve the uncertainty.

## Relationships

Store requirement-to-requirement relationships only in the top-level `relationships` array:

- `parent-of`: the source record is decomposed or allocated into the target record;
- `depends-on`: the source record requires the target to be satisfied or meaningful;
- `conflicts-with`: both source-backed records cannot simultaneously hold;
- `duplicates`: an explicit decision confirms semantic duplication.

Plausible duplication is an issue, not a `duplicates` relationship. Supply a concise evidence or decision basis for every relationship.
