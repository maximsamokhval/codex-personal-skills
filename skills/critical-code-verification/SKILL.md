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
4. Read [references/tool-selection.md](references/tool-selection.md), then choose the minimum set of complementary methods. Do not apply every tool by default.
5. Place checks separately by default. Use the project's existing layout when present; otherwise prefer:
   - `tests/properties/` for Hypothesis properties;
   - `tests/stateful/` for state machines;
   - `verification/crosshair/` for symbolic wrappers;
   - `verification/fuzz/` and `verification/corpus/` for fuzz targets and seeds.
6. Propose a production contract only when it is short, stable, part of the public or domain behavior, and useful at runtime or as API documentation. Show this change separately and obtain explicit approval before adding a contract dependency or modifying production code solely for verification.
7. Obtain explicit approval before installing dependencies, starting containers or WSL, enabling network access, or scheduling a long-running check. Prefer the project's existing environment and commands.
8. Run a bounded check appropriate to the risk. Record the tool version, target, budget, assumptions, and exact outcome.
9. When a counterexample is found, reduce it when the tool has not already done so, explain the violated property, and add a deterministic regression test when the user requested implementation.
10. After a check runs, report one evidence status from the list below. In design mode use execution state `planned-not-run` instead. Never collapse an inconclusive or bounded search into “proved.”

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

For each critical property, return a compact record with:

- block and risk;
- property, assumptions, and exclusions;
- tool and check location;
- execution budget;
- execution state or evidence status, plus the minimal counterexample if any;
- files changed and the exact repeat command, or a clearly marked command template when the project environment is unknown.

Distinguish completed local evidence from checks that were proposed, skipped, or left for CI.
