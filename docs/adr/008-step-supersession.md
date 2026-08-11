# ADR-008

## Title

Step Supersession

## Status

Accepted

## Context

Dynamic replanning currently appends new steps.

Recoverable failed steps remain active.

Completion therefore never reaches COMPLETE.

## Problem

A recoverable failure should remain visible for auditing.

However, it should not prevent workflow completion once an alternative execution path succeeds.

## Decision

Introduce Step Supersession.

A recoverable failed step that has been replaced by a replanned step will be marked SUPERSEDED.

Completion will ignore superseded failures.

Execution history remains intact.

## Consequences

Advantages

- Full audit trail
- True dynamic replanning
- Cleaner execution model

Trade-offs

- Additional execution state
- Slightly more complex completion logic

## Implementation

Implemented in Sprint 10.

- Added StepStatus.SUPERSEDED
- Added replaces_step_id to PlanStep
- Executor marks replaced failed steps as SUPERSEDED after successful execution.
- Completion ignores superseded failures through status evaluation.