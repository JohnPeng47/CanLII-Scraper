# From Single LLM Invocation to Agent-First Architecture: An Evolution in Thinking

*Tracing the intellectual progression across the UC Berkeley EPIC Data Lab papers (2023–2026)*

---

## Stage 0: The Naive Starting Point — LLM-as-UDF

The implicit baseline that every paper in this body of work reacts against is what we might call the **LLM-as-UDF paradigm**: you have a table of unstructured documents, you write a natural-language prompt, and the system invokes an LLM on every row. One prompt, one model, one call per document. This is the paradigm now shipping in production SQL engines — Databricks AI Functions, Snowflake Cortex AI SQL, Google AlloyDB AI, DuckDB.

The appeal is obvious: it's the simplest possible abstraction. The LLM is a black-box function. The data system doesn't need to understand what the LLM is doing any more than it understands what a traditional UDF computes. You write `SELECT llm_extract(document, 'What is the settlement amount?') FROM cases` and the system dutifully sends each document to GPT-4o.

The problems are equally obvious, and they define the entire research agenda:

1. **Cost**: GPT-4o costs $2.50/1M input tokens. At 10K tokens per legal document, processing 1M documents costs $25,000 — for a single column. A pipeline with 5 operators costs $125,000. This is not viable.
2. **Accuracy**: Asking an LLM to extract 20 fields simultaneously from a 50-page document in a single prompt degrades accuracy catastrophically. The "lost in the middle" problem means the LLM ignores content in the document's interior. Complex reasoning tasks (e.g., "does this opinion overturn a lower court?") require decomposition that a single prompt cannot express.
3. **Brittleness**: The user's prompt is treated as gospel. If they ask for "John Smith," the system will miss "J. Smith." If they ask for a severity score on a 1-10 scale, the LLM returns non-discriminative scores clustered around 7. There's no mechanism for the system to recognize or correct these problems.

The evolution from this starting point proceeds through five distinct conceptual shifts, each building on and generalizing the previous one.

---

## Stage 1: The Model is a Variable — Model Cascades (BARGAIN, 2024–2025)

The first optimization insight is the simplest: **not every document needs the expensive model**.

BARGAIN (arXiv 2509.02896) formalizes this as a statistical decision problem. For each document, run the cheap proxy model (GPT-4o-mini, ~17x cheaper) first. If its confidence exceeds a threshold, accept the prediction. Otherwise, escalate to the expensive oracle (GPT-4o). The key contribution over prior cascade work (FrugalGPT, SUPG) is providing **finite-sample statistical guarantees** that overall quality stays within a user-specified tolerance — not just asymptotic guarantees that break at realistic sample sizes.

**What changed conceptually**: The model is no longer fixed. The system makes a per-record routing decision. But the operation itself — the prompt, the document, the task — is still identical at every cascade stage. You're still running the same question on the same data; you're just choosing who answers it.

**What stayed the same**: The prompt is still treated as a fixed, user-specified black box. The document is still processed in its entirety. The system has no understanding of what the operation *means*.

This is the mildest possible departure from the UDF abstraction. The LLM is still a black box; you're just choosing between a cheap black box and an expensive one.

---

## Stage 2: The Operation is a Variable — Task Cascades (2025–2026)

Task Cascades (arXiv 2601.05536) make the critical conceptual leap: **you can change what you're asking, not just who you're asking**.

Instead of running the same operation at every cascade stage with different models, the system generates **surrogate operations** — simpler, correlated tasks that can cheaply resolve easy documents. For a task like "does this Wikipedia talk page discuss a reversion?", the surrogate might be "does this page contain the phrase 'WP:3RR' or 'three-revert rule'?" — a keyword check that resolves 60% of documents instantly without any LLM call at all.

Three axes now vary simultaneously per cascade stage:
- **The model** (cheap proxy vs. expensive oracle)
- **The operation** (original user prompt vs. LLM-generated surrogate)
- **The document fraction** (10%, 25%, 50%, or 100% of the document, reordered so relevant content appears first)

An LLM agent generates the surrogate operations by examining failure cases — documents that weren't resolved by earlier stages. This is **the first appearance of an LLM reasoning about operations rather than just executing them**. The agent sees what the pipeline is struggling with and proposes simpler formulations that might resolve the easy cases.

**What changed conceptually**: The operation itself is now an optimization variable. The system is no longer faithfully executing the user's exact specification on every document — it's reasoning about *what question to ask* and *how much of the document to read* to achieve the same end result more cheaply. The formal proof that optimal cascade construction is NP-Hard (via reduction from Minimum Sum Set Cover) reveals the richness of this new optimization space.

Result: **41–48.5% cheaper than model cascades** on average, with the same statistical accuracy guarantees.

---

## Stage 3: The Pipeline Structure is a Variable — DocETL & MOAR (2024–2026)

While cascades optimize a single operator, DocETL (arXiv 2410.12189) and its successor MOAR (arXiv 2512.02289) optimize the **entire pipeline**.

DocETL introduces the foundational insight: a single complex LLM operation can be **decomposed into a sequence of simpler operations** that collectively achieve higher accuracy. "Extract all entities and their relationships from this document" becomes:
1. Split document into chunks
2. Extract entities per chunk
3. Resolve duplicate entities across chunks
4. Synthesize relationships

An LLM agent performs this decomposition. It generates candidate rewrites, evaluates them on a sample using an LLM-as-judge, and selects the highest-accuracy plan. This is the "agentic optimizer" — the first system where an LLM is used not to process data but to **redesign how data is processed**.

MOAR generalizes this dramatically with 30+ rewrite directives spanning four categories:
- **Rule-based, data-independent**: operator fusion (merge consecutive maps into one LLM call), filter-map reordering
- **Rule-based, data-dependent**: code substitution (replace an LLM operator with synthesized Python when the task is deterministic enough), document compression (regex/keyword extraction to shrink token count)
- **Agentic, data-independent**: model substitution, prompt clarification, few-shot injection
- **Agentic, data-dependent**: chunk sampling, cascade filtering, arbitrary free-form pipeline edits

MOAR's UCT (Upper Confidence Bound for Trees) search explores the space of complete pipeline rewrites, returning a Pareto frontier of cost-accuracy tradeoffs. The key theoretical insight is that **optimal substructure fails** — you cannot optimize operators independently because upstream changes affect downstream accuracy unpredictably. A map that extracts smaller text spans may look better in isolation but break the downstream reduce that needs richer context for deduplication.

**What changed conceptually**: The unit of optimization expanded from a single operator to the entire pipeline. The system now reasons about pipeline *topology* — not just what model runs an operation, or what the operation is, but how many operations there are, what order they run in, and whether some should be replaced with code entirely. The LLM agent is now an optimizer that transforms program structure, not just a function that processes data.

Result: **27% higher accuracy than the next-best optimizer at 55% of the cost**.

---

## Stage 4: The Data Representation is a Variable — ZenDB & FDJ (2024–2025)

Parallel to the operation-optimization track, another line of work recognized that **how the data is represented to the LLM is itself an optimization target**.

ZenDB (arXiv 2405.04674) exploits **semantic hierarchical trees (SHTs)** — document structure extracted from visual formatting metadata (font size, bold, indentation). Instead of feeding an entire 50-page document to the LLM, or using naive RAG chunking, ZenDB identifies the specific section of the document that contains the answer (e.g., routing a question about medical impacts to the medical examiner's report subsection). Result: **+61% precision, +80% recall** over RAG baselines.

FDJ (arXiv 2512.05399) applies the same principle to semantic joins. Instead of comparing every pair of documents with an LLM (O(n²) cost), FDJ **decomposes the join predicate into a CNF expression over extracted features** (dates, names, locations). Feature extraction is linear; CNF evaluation is cheap arithmetic. The LLM is used to *design* the decomposition, not to execute the join. Result: **up to 10x cheaper than cascades** on semantic joins.

**What changed conceptually**: The system now understands document *structure*. It doesn't treat unstructured data as an opaque blob to be fed to the LLM in its entirety. It reasons about *which part* of a document is relevant, *what features* can be cheaply extracted, and *how* to represent data to minimize LLM cost while maximizing accuracy. The consistent empirical finding: for complex, multi-page documents, structure-aware approaches dominate embedding-similarity approaches.

---

## Stage 5: The System Has Agency — Proactive Data Systems (2025)

The Proactive Data Systems vision paper (arXiv 2502.13016) synthesizes Stages 1–4 into a unified framework and makes the philosophical shift explicit: **treating LLMs as black-box UDFs is the wrong abstraction**.

The paper identifies three axes of proactivity:

**Proactive operation understanding.** The system doesn't just execute the user's prompt — it understands what the prompt is trying to achieve, decomposes it into sub-operations, decides which sub-operations need an LLM and which can use SQL, calibrates few-shot examples, and evaluates alternative formulations. This subsumes DocETL and MOAR.

**Proactive data understanding.** The system doesn't just feed documents to the LLM — it identifies semantic structure (ZenDB), extracts embedded tables and forms (TWIX), clusters related documents across a collection, and identifies shared templates. It decides what to pre-compute vs. what to evaluate lazily based on anticipated query patterns.

**Proactive user understanding.** The system doesn't just execute the literal query — it considers multiple interpretations ("John Smith" → "J. Smith", "John M. Smith"), relaxes predicates when results are empty, summarizes when results are overwhelming, and asks targeted clarifying questions at key decision points.

**What changed conceptually**: The system is no longer a passive executor of user-specified operations on user-provided data. It has *initiative*. It can decide that the user's query is underspecified, that the document should be restructured, that the operation should be decomposed, and that a clarifying question is worth asking. The LLM isn't just processing data — it's reasoning about *how to process data*, *what data to process*, and *what the user actually needs*.

But — and this is the critical limitation — the Proactive Data Systems paper still assumes a **query-answer interaction pattern**. The user issues a query; the system proactively optimizes and executes it; the user gets results. The proactivity is *within* a single query's lifecycle.

---

## Stage 6: The Database Itself is an Agent — Agent-First Data Systems (2025)

The Agent-First Data Systems paper (arXiv 2509.00997) makes the final leap. It doesn't ask "how should a database serve LLM-powered queries better?" It asks: **"what should a database look like when agents — not humans — are the primary users?"**

The key empirical observation motivating everything is **agentic speculation**: when an LLM agent is tasked with a data problem, it doesn't issue a single well-formed query. It issues *hundreds or thousands* of exploratory requests — probing schemas, sampling data, trying partial solutions, validating results, backing up and trying different approaches. Their case studies on BIRD (text-to-SQL) show:

- Success rate increases 14–70% as the number of parallel attempts increases
- The number of distinct sub-plans is often <10–20% of total sub-plans across attempts (massive redundancy)
- Agents follow heterogeneous phases: metadata exploration → column statistics → partial query attempts → full query formulation
- Providing grounding hints reduces total query volume by **18.1%**

This is fundamentally different from the query-answer paradigm. The "user" (agent) doesn't know what it wants. It's *searching* for what it wants through high-throughput exploratory interaction with the data system. The database's job is no longer to answer queries — it's to **help agents find the right queries to ask**.

### The New Architecture

The paper proposes four interlocking innovations:

**1. Probes replace queries.** A probe is a query plus a **brief** — natural language context about the agent's goals, current phase (exploration vs. solution formulation), accuracy requirements, and priorities. The database doesn't just execute the SQL; it interprets the brief to decide *how* to execute (approximate? exact? skip entirely because a related probe already answered this?).

**2. Sleeper agents replace indexes.** In-database LLM agents that activate when a probe arrives, proactively surfacing relevant auxiliary information: related tables the agent hasn't discovered yet, why-not provenance explaining empty results ("you assumed states are two-letter codes, but they're spelled out"), cost estimates for expensive operations, and suggestions to batch or rewrite probes.

**3. A satisficing probe optimizer replaces the query optimizer.** The objective function changes: instead of minimizing per-query latency, minimize *total agent interaction time* across the entire speculative session. This means the optimizer might deliberately run one expensive query to completion (rather than approximating it) if that prevents 50 follow-up probes. It balances exploration vs. exploitation across the agent's session, not just within a single query.

**4. An agentic memory store replaces the buffer pool.** A persistent, semantic cache of prior probe results, partial solutions, and metadata annotations — queryable by semantic similarity. When a new agent arrives with a similar task, the memory store provides grounding so it doesn't repeat the same exploratory sequence from scratch. This introduces novel consistency challenges: stale cached results can actively mislead new agents.

**5. Branched transactions replace ACID isolation.** Agents explore "what-if" hypotheses in parallel, each requiring a logical fork of database state. Neon (Postgres) reports agents create **20x more branches and 50x more rollbacks** than humans. The paper calls for "MVCC on steroids" — massively parallel copy-on-write forking with ultra-fast rollback, where most branches are discarded and only one is committed.

### What Changed Conceptually

This is the most radical departure from the starting point. Let's trace the full arc:

| Stage | What the system optimizes | Who has agency | Interaction pattern |
|-------|--------------------------|----------------|-------------------|
| 0. LLM-as-UDF | Nothing | The user | One query → one result |
| 1. Model cascades | Which model answers | The system (per-record routing) | One query → one result |
| 2. Task cascades | What question is asked | The system (operation generation) | One query → one result |
| 3. Pipeline optimization | The pipeline structure | An LLM agent (optimizer) | One pipeline → one result set |
| 4. Data representation | How data is shown to the LLM | The system (structure extraction) | One query → one result |
| 5. Proactive systems | Operations + data + user intent | The system (proactive reasoning) | One query → enriched result |
| 6. Agent-first | The entire interaction protocol | Both database and agent | Thousands of probes → eventual solution |

At Stage 0, the LLM is a dumb function and the database is a dumb executor. At Stage 6, both the database and its primary user are autonomous reasoning agents engaged in a cooperative, multi-turn, high-throughput negotiation where neither party knows the answer in advance.

---

## The Deepest Shift: From Answering to Steering

The single most important intellectual thread across these six stages is a shift in what the data system's *job* is:

**Stage 0–2**: The system's job is to **answer the user's query** as specified, as cheaply as possible.

**Stage 3–4**: The system's job is to **find a better way to answer** the user's query than the user specified.

**Stage 5**: The system's job is to **understand what the user actually needs** and answer that instead.

**Stage 6**: The system's job is to **help the agent figure out what to ask**, recognizing that the agent itself doesn't know yet.

This progression mirrors a broader trend in how we think about LLMs in systems. Early work bolts LLMs onto existing abstractions (UDF, API endpoint, chatbot). The mature vision recognizes that LLMs change what the abstraction should be. You don't add natural language to SQL — you redesign the database because its primary user now thinks in natural language, explores through speculation rather than precise queries, and benefits from a system that has its own understanding of the data, the task, and the user's goals.

---

## What Remains Unsolved

The Agent-First paper is explicitly a vision with no implementation. The open problems it surfaces are genuinely hard:

1. **Probe semantics are undefined.** How do you formally specify what a "brief" means? How does the optimizer reason about natural language goals?
2. **Satisficing is underspecified.** What's the objective function for "good enough"? How do you balance exploration vs. exploitation across an agent session without knowing the session length?
3. **Memory store consistency.** Stale cached results actively mislead agents. When should cached results be invalidated? How do you handle the fact that "relevance" is task-dependent?
4. **Multi-agent coordination.** When thousands of agents share a database, how do you share useful grounding across agents without leaking private context? The paper cites CryptDB but has no solution.
5. **Cost of proactivity.** Every sleeper agent, every probe interpretation, every auxiliary information lookup is an LLM call. The cost of the meta-reasoning layer could exceed the cost of the speculative queries it's trying to reduce.

The research agenda is clear. The implementation is years away. But the intellectual trajectory — from "LLM as dumb function" to "database and agent as cooperative reasoning partners" — is one of the most coherent and ambitious arcs in contemporary systems research.
