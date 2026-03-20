# LLM-Powered Unstructured Data Pipelines at Scale — Paper Survey

Source: arXiv author search for Shankar, S (CS) — https://arxiv.org/search/cs?searchtype=author&query=Shankar,+S

## Core Pipeline Systems

### 1. DocETL: Agentic Query Rewriting and Evaluation for Complex Document Processing
- **Authors:** Shreya Shankar, Tristan Chambers, Tarak Shah, Aditya G. Parameswaran, Eugene Wu
- **arXiv:** [2410.12189](https://arxiv.org/abs/2410.12189) (October 2024)
- **Summary:** A system that optimizes complex document processing pipelines using agent-based query rewrites. Introduces declarative operators for LLM-powered data transformations and an optimizer that automatically rewrites plans to improve output quality.

### 2. Task Cascades for Efficient Unstructured Data Processing
- **Authors:** Shreya Shankar, Sepanta Zeighami, Aditya Parameswaran
- **arXiv:** [2601.05536](https://arxiv.org/abs/2601.05536) (January 2026)
- **Summary:** Proposes task cascades — decomposing expensive LLM operations into cheaper sub-tasks — for cost-efficient unstructured data processing while maintaining accuracy.

### 3. Steering Semantic Data Processing With DocWrangler
- **Authors:** Shreya Shankar, Bhavya Chopra, Mawil Hasan, Stephen Lee, Björn Hartmann, Joseph M. Hellerstein, Aditya G. Parameswaran, Eugene Wu
- **arXiv:** [2504.14764](https://arxiv.org/abs/2504.14764) (April 2025)
- **Summary:** An IDE for building and debugging LLM-powered semantic data processing pipelines, with mixed-initiative features for iteratively refining operations on unstructured data.

### 4. Multi-Objective Agentic Rewrites for Unstructured Data Processing (MOAR)
- **Authors:** Lindsey Linxi Wei, Shreya Shankar, Sepanta Zeighami, Yeounoh Chung, Fatma Ozcan, Aditya G. Parameswaran
- **arXiv:** [2512.02289](https://arxiv.org/abs/2512.02289) (December 2025)
- **Summary:** An optimizer that handles cost-accuracy tradeoffs in LLM data pipelines via multi-objective agentic rewrites of pipeline operators.

## Cost Optimization & Efficiency

### 5. BARGAIN: Cut Costs, Not Accuracy — LLM-Powered Data Processing with Guarantees
- **Authors:** Sepanta Zeighami, Shreya Shankar, Aditya Parameswaran
- **arXiv:** [2509.02896](https://arxiv.org/abs/2509.02896) (September 2025)
- **Summary:** Reduces LLM data processing costs by up to 86% over state-of-the-art while maintaining accuracy guarantees through intelligent query routing and caching strategies.

### 6. LLM-Powered Proactive Data Systems
- **Authors:** Sepanta Zeighami, Yiming Lin, Shreya Shankar, Aditya Parameswaran
- **arXiv:** [2502.13016](https://arxiv.org/abs/2502.13016) (February 2025)
- **Summary:** Framework for data systems that proactively rewrite and optimize LLM operations, anticipating queries and pre-computing results to reduce latency and cost.

### 7. Featurized-Decomposition Join (FDJ): Low-Cost Semantic Joins with Guarantees
- **Authors:** Sepanta Zeighami, Shreya Shankar, Aditya Parameswaran
- **arXiv:** [2512.05399](https://arxiv.org/abs/2512.05399) (December 2025)
- **Summary:** Reduces LLM invocations for semantic join operations by decomposing them into feature extraction steps, enabling low-cost joins with accuracy guarantees.

## Document Analytics

### 8. ZenDB: Towards Accurate and Efficient Document Analytics with LLMs
- **Authors:** Yiming Lin, Madelon Hulsebos, Ruiying Ma, Shreya Shankar, Sepanta Zeighami, Aditya G. Parameswaran, Eugene Wu
- **arXiv:** [2405.04674](https://arxiv.org/abs/2405.04674) (May 2024)
- **Summary:** A document analytics system that leverages semantic structure to enable SQL-like queries over document collections using LLMs.

## Data Quality & Validation

### 9. SPADE: Synthesizing Data Quality Assertions for LLM Pipelines
- **Authors:** Shreya Shankar, Haotian Li, Parth Asawa, Madelon Hulsebos, Yiming Lin, J. D. Zamfirescu-Pereira, Harrison Chase, Will Fu-Hinthorn, Aditya G. Parameswaran, Eugene Wu
- **arXiv:** [2401.03038](https://arxiv.org/abs/2401.03038) (January 2024)
- **Summary:** Automatically synthesizes data quality assertions for LLM pipeline outputs, addressing the challenge of validating non-deterministic LLM results in production.

### 10. PROMPTEVALS: A Dataset of Assertions and Guardrails for Custom Production LLM Pipelines
- **Authors:** Reya Vir, Shreya Shankar, Harrison Chase, Will Fu-Hinthorn, Aditya Parameswaran
- **arXiv:** [2504.14738](https://arxiv.org/abs/2504.14738) (April 2025)
- **Summary:** Dataset of 2,087 prompts with 12,623 assertion criteria for evaluating and guarding LLM pipeline reliability in production.

### 11. EvalGen: Who Validates the Validators? Aligning LLM-Assisted Evaluation with Human Preferences
- **Authors:** Shreya Shankar, J. D. Zamfirescu-Pereira, Björn Hartmann, Aditya G. Parameswaran, Ian Arawjo
- **arXiv:** [2404.12272](https://arxiv.org/abs/2404.12272) (April 2024)
- **Summary:** Mixed-initiative approach for aligning LLM-generated evaluation functions with human preferences — critical for validating outputs in data pipelines.

## RAG & Retrieval Pipelines

### 12. RAGGY: RAG Without the Lag — Interactive Debugging for RAG Pipelines
- **Authors:** Quentin Romero Lauro, Shreya Shankar, Sepanta Zeighami, Aditya Parameswaran
- **arXiv:** [2504.13587](https://arxiv.org/abs/2504.13587) (April 2025)
- **Summary:** Developer tool for real-time debugging of complex RAG pipeline components, addressing observability challenges in retrieval-augmented generation systems.

## Knowledge Extraction at Scale

### 13. ODKE+: Ontology-Guided Open-Domain Knowledge Extraction with LLMs
- **Authors:** Samira Khorshidi, Azadeh Nikfarjam, Suprita Shankar, et al.
- **arXiv:** [2509.04696](https://arxiv.org/abs/2509.04696) (September 2025)
- **Summary:** Production-scale system extracting 19 million high-confidence facts with 98.8% precision from web sources using ontology-guided LLM extraction.

## Infrastructure & Architecture

### 14. Supporting Our AI Overlords: Redesigning Data Systems to be Agent-First
- **Authors:** Shu Liu, Soujanya Ponnapalli, Shreya Shankar, Sepanta Zeighami, et al.
- **arXiv:** [2509.00997](https://arxiv.org/abs/2509.00997) (September 2025)
- **Summary:** Proposes agent-first data system architecture for handling agentic speculation workloads — foundational for scaling LLM-powered data pipelines.

## MLOps & Production Insights

### 15. "We Have No Idea How Models will Behave in Production until Production"
- **Authors:** Shreya Shankar, Rolando Garcia, Joseph M Hellerstein, Aditya G Parameswaran
- **arXiv:** [2403.16795](https://arxiv.org/abs/2403.16795) (March 2024)
- **Summary:** Ethnographic study identifying the "3Vs of MLOps: velocity, visibility, versioning" — practical insights for operationalizing LLM pipelines in production.

### 16. Moving Fast With Broken Data
- **Authors:** Shreya Shankar, Labib Fawaz, Karl Gyllstrom, Aditya G. Parameswaran
- **arXiv:** [2303.06094](https://arxiv.org/abs/2303.06094) (March 2023)
- **Summary:** Automatic validation system for ML pipelines using partition summarization, addressing data quality drift in production systems.

---

## Key Themes

1. **Declarative pipeline abstractions** — DocETL, ZenDB, and the prompt-engineering-as-crowdsourcing work all push toward declarative interfaces for LLM data processing.
2. **Cost optimization** — BARGAIN, Task Cascades, FDJ, and MOAR address the critical challenge of reducing LLM API costs (up to 86% savings) while maintaining accuracy guarantees.
3. **Quality assurance** — SPADE, PROMPTEVALS, and EvalGen tackle the hard problem of validating non-deterministic LLM outputs in data pipelines.
4. **Developer tooling** — DocWrangler and RAGGY provide interactive debugging and steering for pipeline development.
5. **Production readiness** — The MLOps ethnography and Moving Fast With Broken Data provide empirical grounding for taking these systems to production.
