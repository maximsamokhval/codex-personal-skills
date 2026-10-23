---
name: critical-code-verification
description: Design and implement risk-based verification for critical Python logic whose correctness depends on invariants, conservation rules, state transitions, parser robustness, or mathematically stated properties. Use for symbolic execution, contracts, property-based or stateful testing, fuzzing, formal verification, and verification plans for high-risk code; use ordinary unit testing for routine behavior.
---

# Critical Code Verification

Build the smallest useful body of evidence for critical Python logic. Start from the property that must hold, not from a preferred tool.

## Modes

Infer the mode from the request:

- **Design:** identify risks, properties, assumptions, tools, placement, and budgets. Mark checks as `planned-not-run`, stop after the user can review the plan, and do not change code or dependencies.
- **Implement:** add and run the agreed checks, then preserve useful counterexamples as regression tests.
- **Assess:** inspect existing verification and report gaps without changing it.

## Workflow

1. Inspect the relevant code, task, Python version, operating system, dependency manager, test conventions, and available tools. Limit the inspection to the requested scope; record unavailable context as unknown instead of guessing or blocking a design-only request.
2. Identify critical blocks. Prioritize money, permissions, resource allocation, identifiers and deduplication, state transitions, concurrency boundaries, parsers, serialization, and irreversible operations. If the block is ordinary application behavior without a meaningful invariant, use normal tests instead of this workflow.
3. State each property before implementing its check:
   - property and why failure matters;
   - preconditions and model assumptions;
   - observable oracle or reference model;
   - excluded behavior and side effects;
   - proposed method, location, and execution budget.
4. Read [references/tool-selection.md](references/tool-selection.md), then produce the mandatory tool coverage verdict below. Account explicitly for Hypothesis, Hypothesis State Machine, CrossHair, `deal prove`, and Atheris even when the correct verdict is that a tool does not fit the inspected code.
5. Assign exactly one primary tool and check kind to every property. Add a secondary tool only when it supplies a different kind of evidence. The coverage verdict accounts for the specialist toolkit; it does not require using every tool.
6. Produce the mandatory property selection matrix below before changing code. A list of possible tools without a recommendation is incomplete.
7. Place checks separately by default. Use the project's existing layout when present; otherwise prefer:
   - `tests/properties/` for Hypothesis properties;
   - `tests/stateful/` for state machines;
   - `verification/crosshair/` for symbolic wrappers;
   - `verification/fuzz/` and `verification/corpus/` for fuzz targets and seeds.
8. Propose a production contract only when it is short, stable, part of the public or domain behavior, and useful at runtime or as API documentation. Show this change separately and obtain explicit approval before adding a contract dependency or modifying production code solely for verification.
9. Obtain explicit approval before installing dependencies, starting containers or WSL, enabling network access, or scheduling a long-running check. Prefer the project's existing environment and commands.
10. Run a bounded check appropriate to the risk. Record the tool version, target, budget, assumptions, and exact outcome.
11. When a counterexample is found, reduce it when the tool has not already done so, explain the violated property, and add a deterministic regression test when the user requested implementation.
12. After a check runs, report one evidence status from the list below. In design mode use execution state `planned-not-run` instead. Never collapse an inconclusive or bounded search into “proved.”

## Mandatory tool coverage verdict

Every Design, Implement, and Assess result must include one row for each core specialist tool before the property matrix:

| Tool | Decision | Target property or code seam | Why | Next step |
| --- | --- | --- | --- | --- |

The core rows are:

- Hypothesis property-based testing;
- Hypothesis State Machine (`RuleBasedStateMachine`);
- CrossHair;
- `deal prove`;
- Atheris.

Use exactly one decision per row:

- `use-now`: selected as a primary or secondary tool for at least one property in the property matrix;
- `conditional`: useful only if a named condition is true, such as the presence of a pure typed seam;
- `not-applicable`: no inspected property or boundary matches the tool;
- `blocked`: the tool matches a property but cannot be run within the current platform, dependency, permission, or execution budget.

Make every verdict specific to the inspected code. For `conditional`, name the missing fact or seam and the check it would enable. For `not-applicable`, state why the current risks do not match the tool. For `blocked`, name the blocker and the approval or environment needed. Add rows for other specialist tools actually considered, such as a model checker, while keeping the five core rows visible.

The verdict is an accounting step, not a quota. Never select or install a tool merely to avoid `not-applicable`. Every `use-now` row must map to at least one property-matrix row, and every specialist tool selected in the property matrix must appear in the verdict.

## Mandatory property selection matrix

Every Design, Implement, and Assess result must include one row per critical property:

| Block and risk | Property and assumptions | Check kind | Primary tool | Why this tool | Secondary tool | Why not the alternatives | Location | Repeat command | Budget | Success means | State |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Apply these rules:

- Name a concrete check kind: example unit, property-based, differential, stateful, symbolic, proof, runtime contract, or fuzz.
- Select exactly one primary tool, including the project's ordinary test runner when it is sufficient.
- Use `none` for the secondary tool unless it adds independent evidence; explain that evidence when selected.
- Briefly reject the plausible alternatives for that property. Use the coverage verdict, rather than repeating all five core tools in every property row, to account for tools that were not credible candidates.
- Give an exact file and command when the project is known. In design-only work with missing context, mark them as proposed templates.
- Explain the strength of success: examples passed, no counterexample within a budget, runtime enforcement, or proof within a model.
- When a missing fact changes the choice, name that fact and create a separate condition-labelled row for each branch instead of combining recommendations or saying only “it depends.”

## Production-code boundary

- Keep ordinary input validation and security checks in production code with explicit exceptions or result types.
- Use `assert` only for internal assumptions that may disappear under Python optimization; never rely on it for untrusted input or security.
- Keep Hypothesis tests, state machines, CrossHair-only wrappers, reference models, and fuzz harnesses outside production modules.
- A Deal contract in production is an explicit design choice. Measure hot paths and document whether contracts remain enabled in production.
- Do not symbolically execute code with disk, network, process, or native side effects unless it is isolated and the user approved the execution boundary.

## Evidence statuses

Use exactly one primary status per property:

- `counterexample-found`: a reproducible violation was found;
- `passed-sampled-tests`: generated or enumerated test examples passed;
- `no-counterexample-within-budget`: bounded symbolic analysis or fuzzing found no violation;
- `proved-within-model`: a supported formal model was proved and its assumptions are recorded;
- `inconclusive`: the tool timed out, skipped unsupported code, was flaky, or could not model the property.

Only use `proved-within-model` for an actual successful proof result, such as a supported `deal prove` model. CrossHair, Hypothesis, runtime contracts, and Atheris do not establish a general mathematical proof.

## Result

After the matrix, summarize:

1. checks required now;
2. checks deferred to a longer run or CI;
3. the explicit decision for each core specialist tool and any other specialist tool considered;
4. approvals needed for production contracts, dependencies, WSL or containers, network access, or long runs;
5. files changed and minimal counterexamples converted into regression tests.

In Design mode, report changed files and converted counterexamples as `not applicable`. Distinguish completed local evidence from checks that were proposed, skipped, or left for CI.
