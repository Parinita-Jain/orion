# Sprint 15 — External Tool Integration

## Objective

Enable Orion to identify when a user request requires external information, select an appropriate registered tool, execute it, and make the result available to the workflow.

Target example:

```text
Natural-language request
        ↓
Supervisor
        ↓
Identify need for external information
        ↓
Delegate to appropriate agent
        ↓
Use external tool/API
        ↓
Interpret returned data
        ↓
Make practical decision
        ↓
Natural-language answer
```

## Implementation

### Weather Tool

Added a new `weather` tool using Open-Meteo.

The tool:

- accepts a natural-language location through `state["tool_input"]`
- resolves the location through Open-Meteo geocoding
- retrieves current weather and today's hourly precipitation probability
- requires no API key
- returns structured output
- handles location-not-found and HTTP/data errors

Registered tool:

```text
weather
- Get current weather and today's precipitation probability for a specified location.
Outputs: location, current, precipitation_probability
```

## Tool Registry

The existing generic `Tool` registry was used without architectural changes.

Registered tools now include:

```text
calculator
rag
llm
direct
weather
```

The planner receives dynamically generated descriptions of the registered tools.

## Planner Improvements

The planner schema naming was clarified:

- `schemas.PlannerStep` — Pydantic structured planner output
- `models.plan.PlanStep` — runtime executable plan step

The rename removed ambiguity and prevented a Pydantic planner step from being passed into runtime plan operations.

The planner continues to support:

- multiple tools
- dependencies
- output references
- conditions
- branches
- approval
- plan validation and repair

## Executor Integration

The existing executor was used to execute the registered weather tool.

Tool execution continues to support:

- registry lookup
- retries
- timeouts
- structured success/failure results
- execution records
- dependency handling
- checkpointing
- failure events

No new execution architecture was required.

## Tests

Added:

`tests/test_weather.py`

Coverage includes:

- successful weather-tool execution with mocked API responses
- location-not-found handling

Added an end-to-end compiled workflow test covering the weather tool.

The test verifies:

- weather tool registration
- tool execution through the compiled graph
- successful weather result
- Mumbai location resolution
- returned precipitation probability
- execution record creation
- final natural-language workflow response

## Validation

Focused and full regression testing was performed during the sprint.

Final Sprint 15 regression:

```text
240 passed
```

## Outcome

Sprint 15 successfully integrated an external API-backed tool into Orion's existing registry, planning, execution, and workflow architecture.

The weather example demonstrates the complete external-tool execution path without introducing asynchronous parallel logic or Human-in-the-Loop functionality, which were already implemented separately.
