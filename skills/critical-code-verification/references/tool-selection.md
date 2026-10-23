# Tool selection for critical Python verification

Choose from the shape of the property and code. Make a decision for every property; do not return a menu. Combine methods only when they provide different evidence.

The tool coverage verdict and the property matrix answer different questions. The verdict accounts explicitly for the whole core specialist toolkit; the matrix selects only the checks that fit actual properties. A specific `not-applicable` verdict is a valid decision, while omitting a core tool is incomplete.

## Decision procedure

Use the first specific branch that matches the evidence the property needs:

1. A known example or regression needs no quantified claim: use the project's ordinary test runner, usually pytest.
2. A small pure typed function is inside Deal's supported solver subset and the user needs proof: use `deal prove`.
3. A pure deterministic typed function has precise pre/postconditions but is not a reliable `deal prove` target: use CrossHair.
4. A property ranges over many structured inputs: use Hypothesis; use a differential property when a simple independent reference model exists.
5. Correctness depends on sequences of operations: use Hypothesis `RuleBasedStateMachine`.
6. The boundary consumes bytes or complex untrusted syntax: use Atheris.
7. A stable public or domain promise must be enforced on concrete runtime calls: propose a Deal runtime contract and pair it with an independent test method when broader evidence is required.
8. The code is dominated by external state, concurrency, time, network, or storage: isolate a pure model or choose ordinary integration tests. Do not simulate a formal result.

If more than one branch matches, select the method that directly tests the stated property as primary. Add another method only when its success means something materially different.

## Routing table

| Situation | Check kind | Primary tool | Typical location | Successful result means |
| --- | --- | --- | --- | --- |
| Known behavior or reproduced bug | Example unit or regression | Existing runner, usually pytest | Existing project test layout | Named examples passed |
| Pure deterministic function with precise types and pre/postconditions | Symbolic | CrossHair | `verification/crosshair/` or a stable contract beside the function | No counterexample was found within the analysis budget |
| Small pure function supported by Deal's solver | Proof | `deal prove` | Separate verification command; contract may be beside the function | The translated model was proved under its stated assumptions |
| Algebraic property over many structured values | Property-based | Hypothesis | `tests/properties/` | Generated examples passed |
| Optimized algorithm with a simple trusted implementation | Differential property | Hypothesis | `tests/properties/` | Tested inputs agree with the reference model |
| Stateful API with meaningful operation sequences | Stateful | Hypothesis `RuleBasedStateMachine` | `tests/stateful/` | Generated sequences preserved the checked invariants |
| Parser, decoder, protocol boundary, or native extension | Fuzz | Atheris | `verification/fuzz/` | No crash or unexpected exception was found within the fuzzing budget |
| Public critical function needing executable pre/postconditions | Runtime contract | Deal plus an independent test method when needed | Production code only after approval; tests remain separate | Concrete calls enforce the contract; other methods provide broader evidence |

## CrossHair

Use for deterministic, side-effect-free functions with complete type annotations and precise contracts. A separate top-level wrapper may import production code and express verification-only assumptions with supported contracts or assertions.

CrossHair executes the target with symbolic proxy values and searches for counterexamples. Its own documentation states that failure to find one does not prove the property. Avoid targets that can reach disk, network, processes, clocks, randomness, or unsafe native side effects.

Official references:

- [Contracts and targeting](https://crosshair.readthedocs.io/en/latest/contracts.html)
- [Limitations](https://crosshair.readthedocs.io/en/latest/limitations.html)

## Deal

Use runtime contracts only for stable domain or API promises. Contracts can be disabled, but wrappers may still have overhead; benchmark hot paths. Keep normal validation for untrusted input.

Use `deal prove` only for small, pure, fully typed functions. Treat skipped functions, unsupported constructs, and timeouts as `inconclusive`. The verifier is experimental and supports a limited subset of Python.

Official references:

- [Runtime contracts](https://deal.readthedocs.io/basic/runtime.html)
- [Formal verification and limitations](https://deal.readthedocs.io/basic/verification.html)

## Hypothesis

Use ordinary properties for structured data and a state machine when correctness depends on sequences of operations. Prefer strategies that describe valid data directly. For differential tests, derive the reference model independently and keep it simpler than the implementation; do not copy the same algorithm into both paths. Keep durable failures as explicit `@example` cases or ordinary regression tests; the example database is a cache, not a correctness requirement.

Official references:

- [Quick start](https://hypothesis.readthedocs.io/en/latest/quickstart.html)
- [Stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
- [Replaying failures](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html)

## Atheris

Use a dedicated fuzz entry point and seed corpus for byte-oriented or parser boundaries. Catch only exceptions that represent valid rejected input; unexpected exceptions must fail the target. Keep instrumentation out of normal application startup.

Before implementation, verify the current supported platforms in the official Atheris documentation. When the current release does not support native Windows, use WSL, a Linux container, or Linux CI after approval.

Official reference: [Atheris repository and usage](https://github.com/google/atheris)

## Property patterns

Look for properties stronger than a list of examples:

- conservation: totals, balances, counts, or ownership do not disappear;
- bounds: values remain inside permitted limits;
- idempotence: repeating an operation has no further effect;
- round trip: encode/decode or serialize/parse restores the value;
- monotonicity: progress, versions, or permissions move only in allowed directions;
- equivalence: optimized and reference implementations agree;
- invariant preservation: every valid transition leaves the model valid;
- determinism: the same modeled input produces the same result;
- rejection safety: malformed input cannot escape the documented failure boundary.

Write the mathematical or logical statement before selecting examples. If the property cannot be stated precisely, report the ambiguity instead of manufacturing a proof target.
