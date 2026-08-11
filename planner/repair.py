"""
Planner repair module.

This module provides hooks for repairing invalid execution plans.
The initial implementation is a no-op that simply returns the
original planner output unchanged.
"""

from config import logger
from registry import (
    get_tool_descriptions,
    list_tools,
)

from .llm import get_structured_llm

def format_plan(steps):
    return "\n".join(
        f"""
Step {step.id}
Tool:
{step.tool}

Input:
{step.tool_input}

Depends On:
{step.depends_on}
--------------------
"""
        for step in steps
    ) 

def repair_plan(question, previous_plan, errors):

    logger.info("Repairing invalid execution plan")

    plan = format_plan(previous_plan)

    tool_descriptions = get_tool_descriptions()
    logger.debug("Available tools: %s", list_tools())
    prompt = f"""
    The following execution plan is INVALID.

    Original User Question:

    {question}

    Current Plan:

    {plan}

    Validation Errors:

    {chr(10).join(errors)}

    Fix ALL validation errors.

    Available Tools:

    {tool_descriptions} 

    Rules:

    1. Keep as much of the original plan as possible.

    2. Do NOT change correct steps.

    3. Fix ONLY the invalid parts.

    4. Return ONLY the corrected execution plan.
    Do not include explanations.

    5. Output must match PlannerOutput exactly.

    6. Use ONLY the available tools listed below.

    7. Preserve existing step IDs whenever possible.

    8. Preserve output variables unless they must change.

    9. Preserve existing conditions whenever they are valid.

       Do not remove or rewrite conditions unless required to fix a validation error.
    """

    structured_llm = get_structured_llm()
    
    return structured_llm.invoke(prompt)


