# ADR-010

## Title

Workflow Persistence

## Status

Accepted

## Context

Currently Orion stores workflow state only in memory.

If execution stops, the workflow cannot be resumed.

Long-running workflows require persistence.

## Decision

Introduce persistent workflow storage.

Each workflow receives a unique workflow_id.

Workflow state will include:

- messages
- steps
- tool_results
- execution_records
- completion_status
- iteration

Persistence will initially use JSON files.

A database-backed implementation may be introduced later.

## Consequences

Advantages

- Resume interrupted workflows
- Execution history
- Easier debugging
- Foundation for REST APIs

Disadvantages

- Additional serialization logic