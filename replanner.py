from schemas import ReplannerOutput
from shared import llm
from registry import get_tool_descriptions
from errors import OrionError, ErrorType
from config.settings import MAX_REPLANS

from shared_types.failure_classifier import (
    is_recoverable_failure,
)

from shared_types.step_status import StepStatus

def replanner_node(state):

    print("\n===== REPLANNER NODE =====")

    

    iteration = state.get("iteration", 0)

    if iteration >= MAX_REPLANS:

        return {
            "error": OrionError(
                source="replanner",
                error_type=ErrorType.PLANNER,
                message="Maximum replanning attempts exceeded.",
                recoverable=False
            ),
            "done": True,
            "iteration": iteration
        }

    question = state["messages"][-1].content

    completed_steps = ""

    recoverable_failed_steps = ""

    nonrecoverable_failed_steps = ""

    pending_steps = ""

    for step in state["steps"]:

        tool_result = state["tool_results"].get(step.id)

        if tool_result is None:

            pending_steps += f"""
    Step {step.id}

    Tool:
    {step.tool}

    -------------------------
    """

            continue

        if tool_result["status"] == StepStatus.SUCCESS:

            completed_steps += f"""
    Step {step.id}

    Tool:
    {step.tool}

    Output:
    {tool_result["output"]}

    -------------------------
    """

            continue

        recoverable = is_recoverable_failure(
            tool_result.get("failure_reason")
        )

        entry = f"""
        Step {step.id}

        Tool:
        {step.tool}

        Error:
        {tool_result["error"]}

        Failure Reason:
        {tool_result.get("failure_reason")}

        -------------------------
        """

        if recoverable:
            recoverable_failed_steps += entry
        else:
            nonrecoverable_failed_steps += entry
    tool_descriptions = get_tool_descriptions()
    prompt = f"""
    You are an AI Replanner.

    Your job is to inspect the work completed so far.

    Original User Request:

    {question}

    Workflow Status

    Completed Steps

    {completed_steps}

    Recoverable Failed Steps

    {recoverable_failed_steps}

    Non-Recoverable Failed Steps

    {nonrecoverable_failed_steps}

    Pending Steps

    {pending_steps}

    Available tools:

    {tool_descriptions}

    IMPORTANT

    The value of the tool field MUST exactly match one of the tool names shown above.

    Do NOT invent tool names.

    Do NOT rename tools.

    Examples

    Correct:

    tool = rag
    tool = calculator
    tool = llm
    tool = direct

    Incorrect:

    tool = search
    tool = Search
    tool = Calculator
    tool = Retrieval
    tool = Weather

    Determine whether the user's request has been fully satisfied.

    Rules:

    1. If ALL parts of the user's request have been completed:

        done = true

        steps = []

    2. If more work is required:

        done = false

        Return ONLY the additional steps required.

    3. Do NOT recreate completed steps.

    4. New step ids must continue from the previous highest id.

    5. If a new step depends on a previous step,
    use depends_on.

    6. If a previous output is required,
    reference it using

    #<step>.<field>

    Examples:

    #1.value
    #2.answer

    7. ONLY use the tools listed above.

    8. If an existing tool can complete the task, use it.

    9. Never create a tool that is not registered.

    10. Never recreate completed steps.

    11. Retry only recoverable failed steps.

    12. Never retry non-recoverable failed steps.

    13. When retrying a recoverable failed step,
        populate:

        replaces = <failed_step_id>

    14. Pending steps may be reused if they are still required.

    15. Replacement Steps

        If you retry a recoverable failed step,
        the newly created step MUST include:

        replaces = <failed_step_id>

        Example

        Step 2 failed due to timeout.

        Replacement:

        id = 5

        tool = rag

        tool_input = ...

        replaces = 2

        If the step is not replacing another step,
        set:

        replaces = null

    """
    structured_llm = llm.with_structured_output(
        ReplannerOutput
    )

    try:
        result = structured_llm.invoke(prompt)

    except Exception as e:

        return {
            "error": OrionError(
                source="replanner",
                error_type=ErrorType.INFRASTRUCTURE,
                message=str(e),
                recoverable=True,
                original_exception=e,
            ),
            "done": True,
            "iteration": iteration,
        }

    print("Done:", result.done)

    if not result.done:

        print("\n===== NEW STEPS =====")

        for step in result.steps:

            print(
                f"Step {step.id}: "
                f"{step.tool} "
                f"(depends_on={step.depends_on})"
            )
    return {
    "done": result.done,
    "steps": state["steps"] + result.steps,
    "iteration": iteration + 1,
    "error": None,
    }