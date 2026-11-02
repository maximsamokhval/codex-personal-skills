---
name: architectural-deconstruction-audit
description: Conduct deep architectural audits of codebases, repositories, and system designs to uncover conceptual inconsistencies, state collisions, and accidental complexity. Use when the user asks to review architecture, audit code or a project, find critical flaws or race conditions, simplify an over-engineered system, or separate essential business invariants from accidental infrastructure complexity.
---
# Architectural Deconstruction Audit

Perform a rigorous, deterministic architectural audit of a project, codebase, or system specification by separating essential domain invariants from accidental implementation complexity and identifying hidden failure modes.

## When to Use

- The user asks to audit, review, or inspect a project, repository, codebase, or system architecture for critical flaws, edge cases, or over-engineering.
- A distributed or multi-component system suffers from phantom bugs, race conditions, stuck states, or excessive operational overhead.
- The user wants to simplify or de-engineer a complex architecture down to a minimal reliable core.

## Steps

Execute the audit strictly across these four sequential phase gates. Do not offer cosmetic code style suggestions or jump to refactoring advice before completing Phases 1 through 3.

### Phase 1: Essential Complexity & Invariant Mapping

Define the physical and domain reality of the problem independent of the current implementation:

1. **Single Source of Truth (SSoT)**: Identify which exact record or storage engine holds the authoritative state for each core entity.
2. **State Transition Invariants**: List the strict rules that must hold under all conditions (including network partitions, process crashes, and retries).
3. **Forbidden States**: Explicitly define invalid state combinations (e.g. double spending, orphaned reservations, split-brain ownership, stuck intermediate statuses).

### Phase 2: Semantic Drift & Inconsistency Audit

Cross-examine API contracts, database schemas, background workers, and message handlers to find hidden contradictions:

1. **Assumption Mismatches**: Pinpoint where a producer and consumer make conflicting assumptions about delivery guarantees (e.g. assuming `exactly-once` delivery without an idempotency key or unique constraint).
2. **Dual State Ownership**: Identify entities whose state can be mutated concurrently by multiple independent actors (e.g. a synchronous webhook handler racing with a background cron job or queue worker) without pessimistic locking or compare-and-swap (CAS).
3. **Illusory Fault Tolerance**: Expose retry loops, sagas, or compensation steps that assume prior partial operations succeeded or failed cleanly when they may have timed out mid-flight.

### Phase 3: Accidental Complexity Probe (Occam's Razor & Gall's Law)

Challenge every infrastructure layer, abstraction, and asynchronous boundary:

1. **Boundary Stress-Test**: For each queue, broker, cache, or microservice boundary, state the exact domain invariant from Phase 1 it protects. If it only exists to serve infrastructure complexity, flag it as accidental complexity.
2. **Synchronous Baseline Comparison**: Evaluate what happens if an asynchronous chain or distributed saga is replaced with a single ACID transaction, row-level lock, or monolithic module.
3. **Gall's Law Check**: Identify components that were designed as complex distributed abstractions before a simple deterministic core was proven to work.

### Phase 4: Radical De-engineering Plan

Synthesize a concrete reduction strategy:

1. **Minimal Skeleton Architecture**: Describe the simplest architecture that guarantees 100% of the Phase 1 invariants.
2. **Kill List**: Rank the top 3 components, abstractions, or intermediaries to eliminate first, explaining how removing each one reduces failure surfaces and operational cognitive load.
3. **Verification Probe**: Specify one concrete test or chaos scenario (e.g. concurrent duplicate webhook + DB timeout) that proves the flaw in the current design and validates the simplified target design.

### Metacognitive Circuit Breaker

If you notice your analysis drifting into generic best practices (e.g. "add more logging", "add another retry queue", "write unit tests"), stop immediately. Step into an external observer meta-position, identify which hidden assumption of the current architecture you accidentally accepted as fixed, and re-run Phase 3 from physical constraints (I/O, locks, network latency, atomicity).

## Gotchas

- Never recommend adding a new compensating service, cache, or message queue to fix a synchronization bug caused by existing unnecessary distribution.
- Avoid surface-level lint or syntax commentary; focus strictly on state invariants, concurrency, data integrity, and structural complexity.
