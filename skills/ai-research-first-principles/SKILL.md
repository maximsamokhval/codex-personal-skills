---
name: ai-research-first-principles
description: Deconstruct AI research papers, LLM agent frameworks, ML architectures, and technical trends using First Principles, Cynefin domain classification, and Popperian falsification. Use when the user asks to analyze an AI paper, evaluate a new LLM method, agent pattern, or framework, separate real algorithmic breakthroughs from marketing hype, or assess production readiness.
---
# AI Research First Principles

Deconstruct AI/ML papers, agent architectures, and emerging technical frameworks down to their mathematical, computational, and systems engineering fundamentals, stripping away marketing hype and benchmark cherry-picking.

## When to Use

- The user shares or asks about an AI research paper, LLM architecture, prompting framework, or agentic workflow.
- The user wants to evaluate whether a new AI tool, model technique, or framework is applicable to production engineering.
- The user wants to understand the actual mechanism, algorithmic complexity, and failure boundaries of a technical trend.

## Steps

Execute the deconstruction strictly across these four phases. Never open with a promotional summary of the abstract or uncritically repeat the authors' benchmark claims.

### Phase 1: First Principles Deconstruction (Mechanism over Metaphor)

Strip away anthropomorphic terms ("reasoning", "reflection", "autonomous memory") and expose the underlying mechanics:

1. **Core Mathematical/Algorithmic Primitive**: State what actually happens at the tensor, token probability, context window, or control-flow graph level in 2-3 precise sentences.
2. **Computational & Physical Cost**: Quantify the scaling behavior:
   - Token multiplier (how many extra input/output tokens per user query?).
   - Latency profile (sequential round-trips vs. parallelizable calls).
   - Memory/storage footprint and state synchronization overhead.
3. **Delta from Prior Art**: Identify what is genuinely new versus a repackaging of classic computer science or control theory (e.g. beam search, MCTS, FSM, blackboard architecture, RAG).

### Phase 2: Cynefin Domain & Causal Mapping

Classify where the method actually works based on the nature of cause-and-effect in the target task:

1. **Domain Fit (Clear / Complicated / Complex / Chaotic)**: Identify which Cynefin domain this method belongs to and where it breaks if misapplied (e.g. applying stochastic multi-agent debate to a deterministic Complicated task that requires an exact compiler or solver).
2. **Error Propagation Dynamics**: Analyze how probability errors compound across steps (e.g. if single-step accuracy is $p = 0.9$, a 10-step sequential chain without an external deterministic verifier drops to $0.9^{10} \approx 0.35$).
3. **Feedback Loop Audit**: Determine whether the system has a grounded external verifier (compiler, test suite, database constraint) or relies on ungrounded LLM self-critique (which amplifies sycophancy and mode collapse).

### Phase 3: Inversion & Popperian Falsification (Stress-Testing)

Actively seek the boundaries where the method fails:

1. **Hidden Assumptions**: List the 3 unstated assumptions the authors or creators rely on for their demos/benchmarks to succeed (e.g. clean synthetic context, short horizon, zero tool latency, static schema).
2. **Adversarial Failure Mode**: Construct a concrete production scenario (e.g. noisy retrieval, long-tail edge case, partial API timeout, context pollution) that causes this architecture to degrade or enter an infinite loop.
3. **Simpler Baseline Challenge**: State the simplest deterministic or single-call baseline (e.g. structured output + deterministic state machine) that achieves 80% of the result at 10% of the cost and latency.

### Phase 4: Production Verdict & Integration Protocol

Deliver an actionable engineering assessment:

1. **Adopt / Trial / Hold / Reject**: Give a clear verdict with specific engineering justification.
2. **Guardrail Specification**: If adopting or trialing, specify the exact deterministic circuit breakers, budget caps, and validation gates required to wrap the stochastic component safely in production.

### Metacognitive Circuit Breaker

If you find yourself praising a framework's flexibility or summarizing its README features, stop immediately. Re-anchor on token economics, $O(N)$ scaling limits, and compounding error probabilities ($p^k$).

## Gotchas

- Never treat LLM self-evaluation ("LLM-as-a-Judge" or ungrounded "Reflection") as a reliable verification gate without highlighting correlated blind spots.
- Always distinguish between benchmark improvements on static datasets and robustness in open-ended, stateful production environments.
