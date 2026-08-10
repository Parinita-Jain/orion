# Orion — AI Workflow Orchestration Framework

**Orion** is a modular AI workflow orchestration framework built on **LangGraph**.

It enables intelligent task planning, multi-tool execution, dynamic replanning, workflow branching, validation, and final response synthesis using Large Language Models (LLMs) and external tools.

Orion is designed as an extensible orchestration engine rather than a single AI agent.

---

# Features

## Workflow Engine

- Multi-step planning
- Dynamic replanning
- Conditional workflow branching
- Dependency-aware execution
- Completion state evaluation
- Centralized workflow state
- Human approval support
- Structured execution records

---

## Built-in Tools

- Calculator
- Retrieval-Augmented Generation (RAG)
- General LLM reasoning
- Direct conversation

The tool registry makes it easy to add new tools without modifying the planner.

---

## RAG Support

- PDF ingestion
- ChromaDB vector store
- HuggingFace embeddings
- Semantic retrieval
- Retrieval-Augmented Generation

---

## Reliability

- Centralized error model
- Plan validation
- Dependency validation
- Recoverable vs non-recoverable failures
- Dynamic replanning
- Execution history
- Structured logging
- 95+ automated tests

---

# Architecture

```
                    START
                      │
                      ▼
                  Agent Node
                      │
                      ▼
                 Planner Node
                      │
            ┌─────────┴─────────┐
            │                   │
            ▼                   ▼
      Error Handler        Executor
                                 │
                                 ▼
                         Completion Node
                                 │
          ┌──────────────┬───────────────┬──────────────┐
          │              │               │              │
          ▼              ▼               ▼              ▼
     Executor       Replanner     Synthesizer    Error Handler
                                            │
                                            ▼
                                           END
```

---

# Project Structure

```
orion/

├── app.py
├── graph.py
├── state.py
├── planner.py
├── executor.py
├── completion.py
├── replanner.py
├── synthesizer.py
├── error_handler.py
│
├── config/
├── docs/
├── runtime/
├── shared_types/
├── tools/
├── tests/
│
├── registry.py
├── validator.py
├── schemas.py
├── requirements.txt
└── README.md
```

---

# Workflow

```
User Request
      │
      ▼
 Planner
      │
      ▼
 Executor
      │
      ▼
 Completion
      │
 ┌────┼───────────────┬───────────────┐
 │    │               │               │
 ▼    ▼               ▼               ▼
CONTINUE          REPLAN          COMPLETE      FAILED
 │                 │                 │            │
 ▼                 ▼                 ▼            ▼
Executor      Replanner      Synthesizer   Error Handler
```

---

# Current Capabilities

- Multi-step planning
- Dynamic replanning
- Conditional execution
- Workflow branching
- Tool registry
- Dependency resolution
- Completion state evaluation
- Human approval
- Execution tracking
- Centralized state management
- Structured error handling
- RAG
- Calculator
- General LLM reasoning

---

# Technology Stack

- Python
- LangGraph
- LangChain
- Google Gemini
- ChromaDB
- HuggingFace Embeddings
- Pydantic
- Pytest

---

# Documentation

See the **docs/** folder for detailed architecture documentation.

- planner.md
- executor.md
- completion.md
- replanner.md
- validator.md
- graph.md
- state.md

Architecture Decision Records are available in:

```
docs/adr/
```

Sprint documentation is available in:

```
docs/sprints/
```

---

# Testing

Run the complete test suite:

```bash
pytest
```

Current status:

```
95 tests passing
```

---

# Roadmap

## Completed

- Multi-step planning
- Tool registry
- Validation
- Workflow branching
- Human approval
- Completion state evaluation
- Dynamic replanning
- Structured error handling

## Planned

- Step supersession for failed workflow steps
- Parallel execution
- Persistent workflow execution
- Workflow visualization
- Multi-agent collaboration
- FastAPI deployment
- Streaming execution
- Docker support

---

# Running Orion

```bash
pip install -r requirements.txt

python ingest.py

python app.py
```