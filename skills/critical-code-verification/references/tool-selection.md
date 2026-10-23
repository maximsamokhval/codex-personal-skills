# Tool selection for critical Python verification

Choose from the shape of the property and code. Combine methods only when they provide different evidence.

## Routing table

| Situation | Primary method | Typical location | Successful result means |
| --- | --- | --- | --- |
| Pure deterministic function with precise types and pre/postconditions | CrossHair | `verification/crosshair/` or a stable contract beside the function | No counterexample was found within the analysis budget |
| Small pure function supported by Deal's solver | `deal prove` | Separate verification command; contract may be beside the function | The translated model was proved under its stated assumptions |
| Algebraic property over many structured values | Hypothesis | `tests/properties/` | Generated examples passed |
| Stateful API with meaningful operation sequences | Hypothesis `RuleBasedStateMachine` | `tests/stateful/` | Generated sequences preserved the checked invariants |
| Parser, decoder, protocol boundary, or native extension | Atheris | `verification/fuzz/` | No crash or unexpected exception was found within the fuzzing budget |
| Public critical function needing executable pre/postconditions | Deal runtime contract plus an independent test method | Production code only after approval; tests remain separate | Concrete calls enforce the contract; other methods provide broader evidence |
| Optimized algorithm with a simple trusted implementation | Differential property test | `tests/properties/` | Tested inputs agree with the reference model |

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

Use ordinary properties for structured data and a state machine when correctness depends on sequences of operations. Prefer strategies that describe valid data directly. Keep durable failures as explicit `@example` cases or ordinary regression tests; the example database is a cache, not a correctness requirement.

Official references:

- [Quick start](https://hypothesis.readthedocs.io/en/latest/quickstart.html)
- [Stateful testing](https://hypothesis.readthedocs.io/en/latest/stateful.html)
- [Replaying failures](https://hypothesis.readthedocs.io/en/latest/tutorial/replaying-failures.html)

## Atheris

Use a dedicated fuzz entry point and seed corpus for byte-oriented or parser boundaries. Catch only exceptions that represent valid rejected input; unexpected exceptions must fail the target. Keep instrumentation out of normal application startup.

Atheris currently targets Linux and macOS. On Windows, confirm the current official support statement; otherwise use WSL, a Linux container, or Linux CI after approval.

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
