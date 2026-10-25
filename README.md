[![Orion Tests](https://github.com/Parinita-Jain/orion/actions/workflows/tests.yml/badge.svg)](https://github.com/Parinita-Jain/orion/actions/workflows/tests.yml)

# Orion â€” AI Workflow Orchestration Framework

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
                      â”‚
                      â–¼
                  Agent Node
                      â”‚
                      â–¼
                 Planner Node
                      â”‚
            â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
            â”‚                   â”‚
            â–¼                   â–¼
      Error Handler        Executor
                                 â”‚
                                 â–¼
                         Completion Node
                                 â”‚
          â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
          â”‚              â”‚               â”‚              â”‚
          â–¼              â–¼               â–¼              â–¼
     Executor       Replanner     Synthesizer    Error Handler
                                            â”‚
                                            â–¼
                                           END
```

---

# Project Structure

```
orion/

â”œâ”€â”€ app.py
â”œâ”€â”€ graph.py
â”œâ”€â”€ state.py
â”œâ”€â”€ planner.py
â”œâ”€â”€ executor.py
â”œâ”€â”€ completion.py
â”œâ”€â”€ replanner.py
â”œâ”€â”€ synthesizer.py
â”œâ”€â”€ error_handler.py
â”‚
â”œâ”€â”€ config/
â”œâ”€â”€ docs/
â”œâ”€â”€ runtime/
â”œâ”€â”€ shared_types/
â”œâ”€â”€ tools/
â”œâ”€â”€ tests/
â”‚
â”œâ”€â”€ registry.py
â”œâ”€â”€ validator.py
â”œâ”€â”€ schemas.py
â”œâ”€â”€ requirements.txt
â””â”€â”€ README.md
```

---

# Workflow

```
User Request
      â”‚
      â–¼
 Planner
      â”‚
      â–¼
 Executor
      â”‚
      â–¼
 Completion
      â”‚
 â”Œâ”€â”€â”€â”€â”¼â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”¬â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
 â”‚    â”‚               â”‚               â”‚
 â–¼    â–¼               â–¼               â–¼
CONTINUE          REPLAN          COMPLETE      FAILED
 â”‚                 â”‚                 â”‚            â”‚
 â–¼                 â–¼                 â–¼            â–¼
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
265 tests passed, 1 warning (last verified locally on October 22, 2026)
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
- SSE workflow event streaming
- Dockerized local API deployment
- Persistent ChromaDB storage using a Docker volume
- Health and LLM usage endpoints
- Quota-aware LLM fallback

## Planned

- Step supersession for failed workflow steps
- Parallel execution
- Persistent workflow execution and recovery
- Workflow visualization
- Multi-agent collaboration
- Production/cloud deployment
---

# Running Orion

```bash
pip install -r requirements.txt

python ingest.py

python app.py
```
---

# Running Orion with Docker

## Prerequisites

- Docker Desktop with the Docker engine running.
- A valid Google API key configured in a local `.env` file.

## Build the image

From the project root:

```powershell
docker build -t orion:0.2 .
```

## Start the container

Create the persistent ChromaDB volume if it does not already exist:

```powershell
docker volume create orion_chroma
```

Start Orion:

```powershell
docker run -d --name orion-api -p 8000:8000 --env-file .env -v orion_chroma:/app/chroma_db --restart unless-stopped orion:0.2
```

The container reads runtime environment variables from `.env`. Keep this file out of version control and never include real credentials in the Docker image.

The named volume `orion_chroma` stores ChromaDB data outside the container, so removing or recreating the container does not automatically delete the volume.

## Verify the API

Check container status:

```powershell
docker ps --filter "name=orion-api"
```

Check application health:

```powershell
Invoke-RestMethod http://localhost:8000/health
```

Inspect LLM usage without making a model request:

```powershell
Invoke-RestMethod http://localhost:8000/llm-usage
```

Inspect logs if the container fails to start:

```powershell
docker logs --tail 50 orion-api
```

## Stop and recreate the container

Stop and remove the container:

```powershell
docker rm -f orion-api
```

Then run the `docker run` command above again. Do not remove the `orion_chroma` volume if you want to preserve the vector database.

## Important notes

- The Docker image build installs dependencies from `requirements.txt`. Most dependencies are not pinned, so future builds may resolve different versions.
- The Hugging Face embedding model may need to download model files at startup.
- Successful health checks do not prove that live Gemini requests or SSE workflow streaming work end to end.
- Live model requests may fail if the provider quota is exhausted.
