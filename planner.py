import re


from validator import validate_plan
from registry import (list_tools,
                      get_tool_descriptions,)
from errors import OrionError, ErrorType
from config import logger
from planner_llm import get_structured_llm
from planner_repair import repair_plan
from runtime.approval_request import ApprovalRequest
from schemas import (
    PlannerOutput,
    PlanStep as PlannerStep,
)

from models.plan import (
    PlanStep as RuntimePlanStep,
)

MAX_REPAIR_ATTEMPTS = 3

# ===========================
# Planner
# ===========================


GREETINGS = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening"
}

CALCULATOR_PATTERN = re.compile(
    r"^[0-9+\-*/().%\s]+$"
)



def planner_node(state):

    question = state["messages"][-1].content
    question_lower = question.lower().strip()

    logger.info("Planning started")
    logger.debug("User question: %s", question)

    # -------------------------
    # Rule 1 : Greetings
    # -------------------------

    if question_lower in GREETINGS:

        logger.info("Planner selected 'direct' tool using greeting rule")

        return {
            "steps": [
                PlannerStep(
                    id=1,
                    tool="direct",
                    tool_input="",
                    depends_on=[],
                    replaces_step_id=None,
                )
            ],
            "error": None,
        }


    # -------------------------
    # Rule 2 : Calculator
    # -------------------------

    if CALCULATOR_PATTERN.fullmatch(question):

        logger.info("Planner selected 'calculator' tool using calculator rule")

        return {
            "steps": [
                PlannerStep(
                    id=1,
                    tool="calculator",
                    tool_input=question,
                    depends_on=[],
                    replaces_step_id=None,
                )
            ],
            "error": None,
        }

    # -------------------------
    # Rule 3 : Ask Gemini
    # -------------------------
    
    tool_descriptions = get_tool_descriptions()

    prompt = f"""
    You are an AI planning assistant.

    Your job is to create an execution plan.

    Available tools:
    IMPORTANT

    The value of the tool field MUST exactly match one
    of the tool names shown above.

    Do NOT invent tool names.

    Do NOT rename tools.

    Examples

    Correct:

    tool = rag
    tool = calculator
    tool = llm
    tool = direct

    Incorrect:

    tool = Retrieval
    tool = Search
    tool = LLM
    tool = Calculator
    tool = Weather

    {tool_descriptions}


    Rules:

    1. You may use ONE OR MORE tools.

    2. If multiple independent tasks are requested,
    Return a workflow plan.

    Each step must contain:

        - id
        - tool
        - tool_input

    Return a list called steps.
    For every step, also return depends_on.

    If the step has no dependencies,
    return an empty list.

    3. Keep the original order of execution.

    4. Generate a precise and self-contained tool_input for every tool.

    Each tool_input should contain only the information needed by that tool.

    Do not include parts of the request that belong to another tool.
    5. If a step depends on the output of a previous step, reference the required output field.

        Use this format:

        #<step_id>.<field>

        Examples:

        #1.value
        #2.answer

        Do NOT use only #1 or #2.

        For calculator outputs use:
        #<step>.value

        For llm/rag/direct outputs use:
        #<step>.answer

        Example 1

        User:
        Calculate 15% of ₹800.
        Then multiply the result by 5.

        Steps:

        1.
        tool = calculator
        tool_input = 0.15 * 800

        2.
        tool = calculator
        tool_input = #1.value * 5
        depends_on = [1]

        Example 2

        User:
        Explain RAG.
        Summarize the explanation.

        Steps:

        1.
        tool = rag
        tool_input = Explain RAG

        2.
        tool = llm
        tool_input = Summarize #1.answer
        depends_on = [1]
    If a later step needs a previous result,
    refer to its output variable name.

    Example

    Step1

    calculator

    0.15 * 800

    output=tax

    Step2

    calculator

    salary-tax

    depends_on=[1]

    6. If a step requires human approval,
    return:

    approval = {{
        "required": true,
        "reason": "Brief explanation of why approval is needed."
    }}

    Otherwise return:

    approval = null

    7. If a step should execute only when a previous step satisfies a condition,
    return a condition.

        Format:

        condition = "#<step_id>.<field> <operator> <value>"

        Supported operators:

        ==
        !=
        >
        <
        >=
        <=

        Examples:

        condition = "#1.answer == \"yes\""

        condition = "#2.value > 10"

        condition = "#3.success == true"

        If the step should always execute,
        return:

        condition = null

        Example 3

        User:

        Check the customer's account balance.
        If the balance is greater than ₹10,000,
        invest in the mutual fund.

        Steps:

        1.

        tool = bank_balance

        tool_input = Customer account

        depends_on = []

        condition = null

        2.

        tool = invest

        tool_input = Invest in mutual fund

        depends_on = [1]

        condition = "#1.balance > 10000"

    8. When the user's request contains alternatives such as:

        - if ... otherwise ...
        - if ... else ...
        - when ... otherwise ...
        - based on the result ...

        generate separate workflow steps.

        Each branch should:

        - depend on the same previous step
        - have its own condition
        - use mutually exclusive conditions whenever appropriate

        Example

        User:

        If the customer is eligible,
        approve the loan.
        Otherwise reject it.

        Steps

        1.

        tool = eligibility_check

        depends_on = []

        condition = null

        2.

        tool = approve_loan

        depends_on = [1]

        condition = "#1.eligible == true"

        3.

        tool = reject_loan

        depends_on = [1]

        condition = "#1.eligible == false"


    Question:

    {question}
"""


    structured_llm=get_structured_llm()
    try:
        result = structured_llm.invoke(prompt)

    except Exception as e:

        logger.exception("Planner invocation failed")

        planner_error = OrionError(
            source="planner",
            error_type=ErrorType.INFRASTRUCTURE,
            message=str(e),
            recoverable=True,
            original_exception=e
        )
        
        
        
        return {
            "steps": [],
            "error": planner_error
        }
        

    logger.debug("Planner output: %s", result)

   
    for attempt in range(MAX_REPAIR_ATTEMPTS):
        
        errors = validate_plan(result.steps)
        logger.debug("Validation attempt %d", attempt + 1)
        
        if not errors:
            break

        logger.warning(
                            "Planner validation failed with %d errors",
                            len(errors),
                        )
        repaired = repair_plan(
            question,
            result.steps,
            errors
        )
        repair_errors = validate_plan(repaired.steps)

        if repair_errors:
            logger.warning("Planner repair produced an invalid plan")
        else:
            result = repaired
            logger.info("Planner repaired execution plan")
        
    else:
        
        logger.debug("Registered tools: %s", list_tools())
        errors = validate_plan(result.steps)

        if errors:

            logger.error(
                "Planner failed after %d repair attempts",
                MAX_REPAIR_ATTEMPTS,
            )

            raise ValueError(
                "Planner could not repair the plan.\n\n"
                + "\n".join(errors)
            )
    runtime_steps = [
        RuntimePlanStep(
            id=step.id,
            tool=step.tool,
            tool_input=step.tool_input,
            depends_on=step.depends_on,
            output=step.output,
            timeout=None,
            condition=step.condition,
            replaces_step_id=step.replaces_step_id,
            approval=(
            ApprovalRequest(
                step_id=step.id,
                tool=step.tool,
                reason=step.approval.reason
                    or "Planner requested approval.",
            )
            if (
                step.approval is not None
                and step.approval.required
            )
            else None
            ),
        )
        for step in result.steps
    ]

    logger.info(
        "Planner generated %d execution steps",
        len(runtime_steps),
    )
    logger.debug("Execution plan: %s", runtime_steps)

    return {
        "steps": runtime_steps,
        "error": None,
    }

#-------------
