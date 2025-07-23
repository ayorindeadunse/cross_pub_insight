# Cross Publication Insight Assistant

**Cross Publication Insight Assistant** is a multi-agent, LLM-powered system designed to analyze, compare, and summarize trends across AI/ML GitHub repositories or research publications.

It supports deep repository parsing, LLM-based and semantic trend extraction, fact-checking, summarization, and user-defined aggregation queries such as:
- “What % of these projects use LangGraph?”
- “How do CrewAI and LangChain projects differ?”
- “Show me projects that use vector DBs.”

---


## Features

- **Multi-Agent Architecture** using LangGraph
  - **Project Analyzer Agent**: Inspects repo content and structure.
  - **Trend Aggregator Agent**: Extracts trends via LLM or semantic embeddings (fallback).
  - **Comparison Agent**: Highlights similarities and differences.
  - **Fact Checker Agent**: Validates the accuracy of LLM outputs.
  - **Aggregate Query Agent**: Answers cross-repo questions (e.g., tool usage).
  - **Summarizer Agent**: Produces human-readable insights.

-  **LangGraph Orchestration** with HITL (Human-in-the-loop) fallback at the pre-summary step.
-  **Custom LLM Prompting** using configurable templates.
-  **Trend Extraction via Two Modes**:
  - LLM-based trend synthesis.
  - Embedding-based fallback via `SentenceTransformers`.

-  **CLI Usage** with repo URLs or local paths.
-  **Easily Extendable** for evaluation metrics, publication ingestion, or communication protocols (e.g., MCP).

---

## Quickstart

### 1. Install dependencies
```bash
pip install -r requirements.txt

```

## Run the Agent
python3 main.py <primary_repo> <comparison_repo1> [comparison_repo2 ...] --query "What % use LangGraph?"

## Options

--query: (Optional) Ask a cross-repository question.

--no-hitl: (Optional) Run without human-in-the-loop intervention.

Example: python3 main.py https://github.com/user/project-a https://github.com/user/project-b --query "Which uses vector DBs?"


## Project Structure
.
├── agents/                     # All agent definitions
│   ├── project_analyzer.py
│   ├── llm_trend_agent.py
│   ├── trend_aggregator.py
│   ├── comparison_agent.py
│   ├── fact_checker.py
│   └── summarize_agent.py
│
├── tools/                      # Supporting tools/utilities
│   ├── semantic_trend_detector.py
│   ├── repo_parser.py
│   ├── comparison_tool.py
│   └── hitl_intervention.py
│
├── orchestrator/
│   └── orchestrator.py         # LangGraph state orchestrator
│
├── config/
│   ├── config.yaml             # LLM and model settings
│   └── prompts/                # Custom prompt templates
│
├── utils/                      # Logging, config loader, HITL logic, etc.
│
├── main.py                     # CLI entrypoint
├── README.md
├── LICENSE.md
├── requirements.in
├── requirements.txt
├── .env                        # Local environment variables
└── .env-example                # Sample .env template





## Tooling Used
 - LangGraph

 - SentenceTransformers (all-MiniLM-L6-v2)

 - Local or OpenAI LLMs

 - Jinja2 + YAML prompt configs

 - HITL prompt injection for summary verification


 ## Configuration

 Edit the config/config.yaml file to set:

- LLM model and type (local, openai, etc.)

- Trend detection thresholds

- Prompt paths and overrides

- HITL toggle

