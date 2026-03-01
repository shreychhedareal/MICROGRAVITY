# The Nanobot Swarm: A Sophisticated Memory & Intelligence Architecture

This document explains the complete, comprehensive architecture of the advanced memory and intelligence system powering the nanobot swarm. It details how the swarm achieves high-throughput operation, self-awareness, incremental learning, and autonomous task execution.

---

## 1. The 6-Tier Memory Taxonomy

The swarm operates on a multi-tiered memory taxonomy, allowing it to process information at different scales of time and relevance. All persistent tiers are backed by LMDB (Lightning Memory-Mapped Database) for zero-copy, high-speed read operations.

### Tier 0: Volatile Context (RAM)
*   **What it is:** The immediate "working memory" of a single agent loop iteration.
*   **Contents:** Unsummarised LLM message arrays, active tool call state, and streaming string buffers.
*   **Lifetime:** Microseconds to minutes (flushed when the loop completes).

### Tier 1: Session Memory
*   **What it is:** The sequential narrative of a specific interaction or conversation channel.
*   **Contents:** The raw chronological transcript of what was said and which tools were called.
*   **Lifetime:** Per-session (e.g., a specific chat thread).
*   **Mechanism:** Written sequentially to disk via the `SessionManager`.

### Tier 2: Working Memory (LMDB Key-Value)
*   **What it is:** Fast, exact-match retrieval for structural agent state.
*   **Contents:** The core `HISTORY` ledger, the `PROFILE` (user preferences), and the `LONG_TERM` facts ledger.
*   **Mechanism:** Managed by `MemoryStore`. Provides the baseline context injected into the agent's prompt every time.

### Tier 3: Semantic Vector Index (LMDB + Gemini/TF-IDF)
*   **What it is:** The "fuzzy recall" layer. Maps semantic meaning to historical facts and outcomes.
*   **Contents:** Paragraph-chunked embeddings of all historical and long-term data.
*   **Mechanism:** Managed by `VectorMemory`. Uses exact categorical label filtering (e.g., `["backend", "python"]`) *before* applying compute-heavy cosine similarity. This hybrid "hard-filter + soft-match" approach guarantees both relevance and high throughput.

### Tier 4: Operational Ledgers
*   **What it is:** Structured JSON stores for swarm coordination.
*   **Contents:**
    1.  **Task Tree (DAG):** Directed Acyclic Graph of tasks, tracking dependencies, blockers, and checkpoints.
    2.  **Scheduler Triggers:** Event-driven watchdogs and cron schedules.

### Tier 5: Skill Knowledge
*   **What it is:** The immutable "instincts" and "training" of the swarm.
*   **Contents:** Markdown/YAML capability files defining *how* to do things (e.g., how to search the web, how to parse a PDF).
*   **Lifetime:** Permanent (until explicitly updated by the developer or an evolution agent).

---

## 2. The Advanced Processor Layer

To provide ultimate degrees of freedom without overwhelming the core LLM, the swarm uses 7 specialised middleware processors. These intercept, batch, and optimise data before it costs tokens or time.

### 1. Intelligent Cache
*   **The Problem:** LLM calls are expensive and slow. Subagents often ask the exact same questions.
*   **The Solution:** An LRU (Least Recently Used) cache with a two-tier lookup: O(1) exact hash match, falling back to a >92% cosine similarity "fuzzy" match. Avoids redundant reasoning entirely.

### 2. Bulk I/O Processor
*   **The Problem:** Writing to LMDB requires a single-writer lock. Concurrent subagents writing individually will bottleneck the system.
*   **The Solution:** Accumulates write operations in memory and flushes them in a single massive transaction (either when the buffer hits 50 items or 2 seconds pass). Yields a 10-50x throughput increase.

### 3. Speculative Action Planner
*   **The Problem:** Agent loops are stubbornly sequential (think -> wait for tool -> think -> wait for tool).
*   **The Solution:** A Markov-chain transition model watches the sequence of tools used. If it predicts the next tool with >70% confidence, it *pre-fetches* the data in the background while the LLM is still finishing its current thought.

### 4. Routing Mapper
*   **The Problem:** As the swarm gets hundreds of skills, the LLM wastes tokens just figuring out which skill to use.
*   **The Solution:** A learned routing table maps request patterns directly to the optimal subagent or tool. If confidence is >80%, the query is auto-dispatched, bypassing the routing LLM entirely.

### 5. Incremental Learner
*   **The function:** The swarm's telemetry engine.
*   **What it tracks:** Which tools fail often? How long do they take? Which agent persona (e.g., 'researcher' vs 'coder') has the highest success rate for a given task?
*   **Outcome:** Continuously profiles the swarm's capabilities and feeds this data back to the Routing Mapper.

### 6. Agent Awareness Projector
*   **The function:** Gives the swarm "Theory of Mind" regarding its own state.
*   **Mechanism:** Generates a lightweight snapshot of (a) the agent's current error rates and loaded skills, and (b) the precise status and progress of all active subagents.
*   **Seeker-Controller Pipeline:** If a subagent gets stuck, it projects a "need" into the awareness matrix. The Controller agent sees this and fulfills the request, preventing infinite loops of failure.

### 7. Architecture Knowledge Base
*   **The function:** The architecture explains itself.
*   **Mechanism:** A structured, queryable rationale graph. It documents *why* the Intelligent Cache exists, *what* breaks if the Bulk I/O processor is removed, and *how* the Task Tree depends on the Memory Store.

---

## 3. The Cognitive Pipeline

When a user submits a request, the swarm processes it through a 5-stage cognitive pipeline:

1.  **Intent Analysis & Routing:** The `RoutingMapper` attempts instant dispatch. If it fails, the `IntentAnalyzer` uses the LLM to classify the request (Memory Storage, Task Dispatch, Capability Expansion, or Direct Action).
2.  **Context Assembly (The "Spark"):** `ContextBuilder` gathers the Volatile Context, Tier 3 Semantic matches, and the Tier 6 Awareness Snapshot to build the precise prompt.
3.  **Agent Loop Execution:** The `AgentLoop` executes the task. The `SpeculativePlanner` watches and pre-fetches; the `IntelligentCache` deduplicates.
4.  **Consequence Archival:** Upon task completion, the outcome is stored using `store_consequence()`. It is indexed into the Tier 3 Vector Index with a specific `["consequence"]` label so it can be instantly cited in future, similar situations.
5.  **Introspection & Evolution:** In the background, the `IntrospectionManager` audits the `IncrementalLearner`'s stats. If a tool repeatedly fails, it flags the `EvolutionAgent` to rewrite the tool's code.

---

## Summary of System Dynamics

This architecture solves the fundamental scaling problems of AI agents:
*   **Context Window Exhaustion** is solved by Semantic Vector Filtering.
*   **Token & Latency Waste** is solved by the Intelligent Cache and Speculative Planner.
*   **Infinite Loops & Hallucinations** are mitigated by the Awareness Projector and DAG Task Tree dependencies.
*   **I/O Bottlenecks** are solved by the Bulk I/O Processor.
*   **Static Inflexibility** is solved by the Incremental Learner and the Consequence Archival system.

The result is a swarm that is not just a loop of LLM calls, but a robust, asynchronous, self-monitoring, and self-optimising operating system.
