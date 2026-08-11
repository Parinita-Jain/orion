from shared import llm
from schemas import PlannerOutput


def get_structured_llm():
    return llm.with_structured_output(
        PlannerOutput
    )