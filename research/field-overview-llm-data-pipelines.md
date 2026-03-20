# LLM-Powered Unstructured Data Pipelines at Scale: Field Overview

*Synthesized from 16 papers by Shankar, S et al. (UC Berkeley EPIC Data Lab and collaborators), 2023–2026.*

---

## 1. What This Field Is About

A new class of data system has emerged: **semantic data processing pipelines** where LLM calls replace traditional code in relational operators (map, filter, reduce, join, group-by) applied to large collections of unstructured documents. Instead of writing Python functions, users express operations in natural language ("Does this court opinion overturn a lower court decision?"), and the system invokes an LLM on every row.

This paradigm is now supported by industrial systems (Databricks AI Functions, Snowflake Cortex AISQL, Google AlloyDB AI, DuckDB) and open-source frameworks (DocETL, LOTUS, Palimpzest). The research challenge is making these pipelines **accurate, affordable, and production-ready** — because naive LLM invocation per row is simultaneously too expensive and too error-prone for real workloads.

---

## 2. The Core Systems Stack

The papers collectively define a layered architecture for LLM data pipelines:

### Layer 1: Pipeline Specification (What to compute)

**DocETL** (2410.12189) introduces a declarative DSL where users define pipelines as YAML sequences of semantic operators (map, filter, reduce, resolve, unnest, split, gather). Each operator's logic is specified in natural language with a Jinja prompt template and a typed output schema. This is the lingua franca that other systems in this group build upon.

**ZenDB** (2405.04674) extends this to SQL-like queries over document collections. Users write `CREATE TABLE ... WITH DESCRIPTION` and standard SQL queries; the system lazily materializes attributes from documents at query time. ZenDB's key insight is exploiting **semantic hierarchical trees (SHTs)** — document structure extracted from visual formatting metadata (font size, bold, indentation) — to route queries to the right granularity within a document rather than feeding entire documents to the LLM.

### Layer 2: Pipeline Optimization (How to compute it efficiently)

This is the most active research area, with four complementary optimization strategies:

**a) Agentic query rewriting (accuracy-focused).** DocETL's original optimizer (V1) decomposes complex operations into sequences of simpler ones using LLM agents. For example, a single "extract all entities and their relationships" operation might be rewritten into: split document into chunks → extract entities per chunk → resolve duplicates across chunks → synthesize relationships. An LLM-as-judge evaluates candidate rewrites on a sample to select the highest-accuracy plan.

**b) Multi-objective optimization (cost + accuracy).** MOAR (2512.02289) extends DocETL with 30+ rewrite directives spanning four quadrants: rule-based vs. agentic, data-independent vs. data-dependent. New cost-reduction directives include operator fusion (merging consecutive maps into one LLM call), code synthesis (replacing LLM operators with generated Python when possible), and document compression (regex/keyword extraction to shrink token count before the LLM). MOAR uses UCT (Upper Confidence Bound for Trees) search over the space of complete pipeline rewrites, returning a Pareto frontier of cost-accuracy tradeoffs. Key result: **27% higher accuracy than the next-best optimizer (ABACUS) at 55% of the cost** across six real workloads.

**c) Model cascades (cost-focused, per-record routing).** BARGAIN (2509.02896) decides per-record whether to use a cheap proxy model (GPT-4o-mini, ~17x cheaper) or an expensive oracle (GPT-4o), with **finite-sample statistical guarantees** that overall quality stays within a user-specified tolerance. Its innovations over prior cascade work (SUPG, FrugalGPT) are: adaptive sampling that concentrates on informative score regions, variance-aware estimation using Waudby-Smith-Ramdas betting tests (much tighter than Hoeffding when true precision is high), and data-aware threshold selection that avoids union-bound penalties. Result: **up to 86% more oracle calls avoided** than state-of-the-art, with guarantees that hold at finite sample sizes (not just asymptotically).

**d) Task cascades (cost-focused, operation decomposition).** Task Cascades (2601.05536) generalize model cascades by varying not just the model but also the *operation* and *document fraction* at each cascade stage. An LLM agent generates simpler "surrogate operations" (e.g., keyword checks instead of full semantic analysis) that can cheaply resolve easy documents. Documents are reordered so relevant content appears first, enabling fractional processing. Result: **41–48.5% cheaper than model cascades** on average across 8 workloads, with statistical accuracy guarantees.

### Layer 3: Semantic Join Optimization

**FDJ** (2512.05399) addresses the O(n²) problem of semantic joins — matching records across two tables based on a natural-language predicate. Rather than relying on embedding cosine similarity (which fails for long, complex documents), FDJ rewrites the join condition as a **CNF (Conjunctive Normal Form) expression over extracted features** (dates, names, locations). Feature extraction runs linearly; CNF evaluation is cheap arithmetic. Result: **up to 10x cheaper than BARGAIN cascades** on semantic joins, with formal recall guarantees.

### Layer 4: Data Quality and Validation

**SPADE** (2401.03038) automatically synthesizes runtime data quality assertions for LLM pipeline outputs by analyzing prompt version history. Each historical prompt edit implicitly encodes a quality requirement (e.g., adding "don't reference race" implies an exclusion assertion). SPADE uses ILP (Integer Linear Programming) to select a minimal assertion set that covers observed failures with bounded false-positive rates. Deployed in production within LangSmith at tens of thousands of daily LLM calls.

**PROMPTEVALS** (2504.14738) contributes a dataset of 2,087 production prompts with 12,623 assertion criteria, enabling fine-tuned 7B models to **outperform GPT-4o by 21% on assertion generation** while being faster and cheaper — infrastructure for assertion-driven reliability.

**EvalGen** (2404.12272) addresses the meta-problem of validating LLM evaluators themselves. Its key empirical finding is **criteria drift**: evaluation criteria change as developers observe outputs, creating a catch-22 where you need criteria to grade outputs but need to grade outputs to know your criteria. EvalGen converts developer waiting time into a grading signal via mixed-initiative interaction.

**Moving Fast With Broken Data** (2303.06094) tackles upstream data validation at Meta/Instagram scale (petabyte partitions, tens of thousands of features). Its `gate` system uses spectral clustering on partition summaries + k-NN anomaly detection to achieve **2.1x precision improvement** over baselines while reducing the alert fatigue that causes engineers to silence validation systems.

### Layer 5: Developer Tooling

**DocWrangler** (2504.14764) is a mixed-initiative IDE for semantic data processing, built on DocETL. Its key contribution is characterizing the "outer loop" problem: users don't know what they want to compute until they see LLM outputs. Three novel features — in-situ annotation, LLM-assisted prompt refinement from notes, and automated decomposition suggestions — support an iterative Initialize→Inspect→Improve workflow. Key behavioral finding: users instinctively convert open-ended LLM tasks into classification problems for debuggability.

**RAGGY** (2504.13587) eliminates the dominant bottleneck in RAG pipeline development: re-indexing latency. Pre-materialized indexes across a grid of chunking configurations + process checkpointing enable instant parameter changes. Key finding: **71.3% of retrieval parameter changes** in practice would have required re-indexing, validating the tool's core value proposition. All 12 study participants exhibited a universal "retriever-first" debugging pattern.

### Layer 6: Architecture and Vision

**Proactive Data Systems** (2502.13016) argues that treating LLMs as black-box UDFs is the wrong abstraction. LLM-powered systems should proactively understand and rework operations, data, and user intent — decomposing operations, exploiting document structure, expanding imprecise queries, and seeking clarifying user feedback. This vision paper synthesizes the group's prior systems (DocETL, ZenDB, SPADE) into a coherent framework.

**Agent-First Data Systems** (2509.00997) proposes redesigning database internals for agentic workloads. Key concepts: **probes** (queries + natural language briefs about intent and phase), **sleeper agents** (in-database agents that proactively return grounding information), a **satisficing probe optimizer** (minimizing total agent interaction time, not per-query latency), and an **agentic memory store** (semantic cache of prior results). Empirical finding: injecting grounding hints reduces agent query volume by 18.1%.

### Layer 7: Knowledge Extraction at Scale

**ODKE+** (2509.04696) is a production system at Apple extracting **19 million facts at 98.8% precision** across 195 predicates from Wikipedia. Its architecture — ontology snippet injection + extractor LLM + grounder LLM + AutoML corroborator — lifts raw LLM extraction precision from 91% to 98.8%. Processes 100,000+ facts per minute in streaming mode with end-to-end latency under 2 hours.

### Layer 8: Production Operations

**"We Have No Idea How Models Will Behave in Production"** (2403.16795) is an ethnographic study of 18 ML engineers identifying the **3Vs of MLOps: velocity, visibility, versioning** and their inherent tensions. Key practical insight for LLM pipelines: the biggest gains come from data-centric experimentation (better prompts, better retrieval, better fine-tuning data), not model changes — which is precisely the mode available to LLM practitioners using foundation models.

---

## 3. Key Quantitative Results Summary

| System | Key Metric | Value |
|--------|-----------|-------|
| MOAR | Accuracy gain over next-best optimizer | +27% at 55% cost |
| BARGAIN | Oracle calls avoided vs. SOTA | Up to 86% more |
| Task Cascades | Cost savings vs. model cascades | 41–48.5% cheaper |
| FDJ | Cost vs. BARGAIN on semantic joins | Up to 10x cheaper |
| ZenDB | Accuracy vs. RAG baselines | +61% precision, +80% recall |
| ZenDB-light | Queries per $1 | 3,500–8,000 |
| ODKE+ | Facts extracted / precision | 19M / 98.8% |
| PROMPTEVALS | Fine-tuned 7B vs. GPT-4o | +21% Semantic F1 |
| gate | Precision improvement | 2.1x over baseline |
| RAGGY | Parameter changes needing re-indexing | 71.3% |

---

## 4. Cross-Cutting Themes

### Theme 1: The operation itself is an optimization variable

The central intellectual contribution of this body of work is recognizing that in LLM pipelines, you can optimize not just *which model* runs an operation but *what the operation is*. Task Cascades introduce surrogate operations. MOAR rewrites entire pipeline structures. FDJ decomposes join predicates into extracted features. DocETL decomposes complex operations into simpler sub-operations. This is a fundamentally richer optimization space than traditional query optimization, where the logical plan is fixed and only physical implementation varies.

### Theme 2: Statistical guarantees are essential and achievable

BARGAIN, Task Cascades, and FDJ all provide **finite-sample, non-asymptotic** guarantees on output quality (accuracy, precision, recall) — not just empirical averages. The key enabling technique is the Waudby-Smith-Ramdas betting-based hypothesis test, which provides tight confidence bounds when variance is low. This is a meaningful advance over prior work (SUPG) whose CLT-based guarantees break at realistic sample sizes.

### Theme 3: Document structure matters more than embeddings

ZenDB shows that exploiting visual formatting hierarchy outperforms both full-document LLM calls and RAG chunking. FDJ shows that extracted features outperform embedding cosine similarity for semantic joins. Task Cascades show that relevance-reordered document prefixes outperform naive RAG retrieval for cascade filtering. The consistent finding: for complex, multi-page documents, structure-aware approaches dominate embedding-similarity approaches.

### Theme 4: Evaluation is the hardest unsolved problem

EvalGen's criteria drift finding — that you need to observe outputs to know your criteria, but need criteria to evaluate outputs — is fundamental. SPADE partially addresses this by mining prompt history. PROMPTEVALS provides training data for assertion generators. But the papers collectively acknowledge that LLM pipeline evaluation remains largely manual, subjective, and fragile. The MLOps ethnography confirms this in practice: engineers rely on "gut feeling" and dynamic validation sets rather than fixed benchmarks.

### Theme 5: The reactive-to-proactive shift

The field is moving from reactive systems (execute the user's query as specified) to proactive systems that understand intent, decompose operations, exploit data structure, and seek clarifying feedback. Proactive Data Systems is the vision paper; DocETL, ZenDB, MOAR, and the Agent-First architecture are concrete instantiations. ODKE+'s ontology snippet injection is another form of proactivity — constraining the LLM with domain knowledge rather than letting it extract freely.

### Theme 6: Cost optimization is the production bottleneck

Every systems paper in this collection addresses cost. The numbers tell the story: GPT-4o costs $2.50/1M input tokens; processing 1M legal documents at full cost would run to millions of dollars. BARGAIN saves up to 86% of oracle calls. Task Cascades save 41–48.5% over model cascades. MOAR matches baseline accuracy at 3–74% of baseline cost. FDJ achieves 10x cost reduction on semantic joins. ZenDB-light runs 3,500–8,000 queries per dollar. Without these optimizations, LLM data pipelines are academic curiosities; with them, they become production-viable.

---

## 5. Open Problems

1. **Open-ended generation evaluation.** Most optimization work assumes classification or extraction tasks with measurable accuracy. Extending guarantees to summarization, QA, and free-form generation requires reliable LLM-as-judge evaluators — which EvalGen shows are themselves unreliable.

2. **Multi-step pipeline optimization.** MOAR shows that optimal substructure breaks in LLM pipelines (optimizing operators independently yields globally suboptimal plans). Scaling global search over complete pipelines to longer pipeline chains and larger optimization budgets remains expensive.

3. **Cross-document reasoning.** ZenDB and FDJ handle within-document structure and pairwise joins. Reasoning across large document collections (e.g., "find all incidents involving the same officer across 10,000 reports") requires scalable entity resolution and graph-structured inference.

4. **Streaming and real-time pipelines.** ODKE+ demonstrates streaming KG construction. Extending the full optimization stack (cascades, query rewriting, quality assertions) to streaming settings with sub-second latency is unexplored.

5. **Multimodal data.** All papers focus on text. Documents containing images, tables, charts, and scanned handwriting require fundamentally different extraction and structure-detection approaches.

6. **Agent-database co-design.** The Agent-First paper identifies the research agenda but has no implementation. Building satisficing probe optimizers, sleeper agents, and multi-branch transaction managers is years of systems work.

7. **Alert fatigue and human-in-the-loop scaling.** Moving Fast With Broken Data and the MLOps ethnography both identify alert fatigue as a critical operational problem. Auto-tuning thresholds and surfacing only actionable alerts at scale remains unsolved.

---

## 6. Reading Order Recommendation

For someone entering this field:

1. **Start with the vision:** Proactive Data Systems (2502.13016) — 2-page vision paper framing the entire research agenda.
2. **Core system:** DocETL (2410.12189) — the foundational system with declarative operators and agentic optimization.
3. **Cost optimization deep-dive:** Task Cascades (2601.05536) → BARGAIN (2509.02896) → FDJ (2512.05399) — progressively more sophisticated cost reduction with guarantees.
4. **Multi-objective optimization:** MOAR (2512.02289) — the state-of-the-art optimizer combining accuracy and cost.
5. **Document structure:** ZenDB (2405.04674) — the case for exploiting semantic hierarchy.
6. **Quality assurance:** SPADE (2401.03038) → EvalGen (2404.12272) → PROMPTEVALS (2504.14738) — the evaluation/assertion stack.
7. **Developer experience:** DocWrangler (2504.14764) → RAGGY (2504.13587) — how humans actually build these pipelines.
8. **Production reality:** "We Have No Idea..." (2403.16795) → Moving Fast With Broken Data (2303.06094) — operational insights.
9. **Scale:** ODKE+ (2509.04696) — production knowledge extraction at 19M facts.
10. **Future directions:** Agent-First Data Systems (2509.00997) — the database redesign agenda.
