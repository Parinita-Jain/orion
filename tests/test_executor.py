import pytest
import models.plan

from langchain_core.messages import AIMessage

from models.plan import PlanStep

print(PlanStep)
print(PlanStep.__module__)
print(models.plan.PlanStep)


import time

from registry import (
    Tool,
    register_tool,
    clear_registry,
)

from executor import (
    execute_step,
    executor_node,
)

from shared_types.step_status import StepStatus
from runtime.event_bus import EventBus
from shared_types.workflow_event_type import WorkflowEventType

from shared_types.failure_reason import FailureReason

from runtime.runtime_config import RuntimeConfig
from runtime.approval_request import ApprovalRequest
from runtime.approval_decision import ApprovalDecision


def make_state(**overrides):

    state = {
        "steps": [],
        "context": {},
        "tool_results": {},
        "execution_records": [],
        "runtime_config": RuntimeConfig(),
        "event_bus": EventBus(),
    }

    state.update(overrides)

    return state

class FakeListener:
    def __init__(self):
        self.events = []

    def __call__(self, event):
        self.events.append(event)

def dummy_tool(state):
    return {
        "messages": [AIMessage(content="Done")],
        "output": {
            "answer": "Orion Test Response",
        },
        "success": True,
        "error": None,
    }

def echo_tool(state):
    return {
        "messages": [],
        "output": {
            "received": state["tool_input"],
        },
        "success": True,
        "error": None,
    }

def failing_tool(state):
    raise RuntimeError("Boom!")

def setup_function():
    clear_registry()


def teardown_function():
    clear_registry()


def test_execute_step_success():

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    step = PlanStep(
        id=1,
        tool="dummy",
        tool_input="Hello",
        depends_on=[],
    )

    state = make_state()

    result = execute_step(
        step,
        state,
        {},
    )

    assert result["result"]["success"] is True
    assert result["result"]["output"]["answer"] == "Orion Test Response"

    record = result["record"]

    assert record.step_id == 1
    assert record.tool == "dummy"
    assert record.success is True

def test_execute_step_unknown_tool():

    clear_registry()

    step = PlanStep(
        id=1,
        tool="unknown",
        tool_input="Hello",
        depends_on=[],
    )

    state = make_state()

    with pytest.raises(ValueError) as exc:
        execute_step(
            step,
            state,
            {},
        )

    assert "not registered" in str(exc.value)

def test_execute_step_tool_without_function():

    register_tool(
        Tool(
            name="dummy",
            function=None,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    step = PlanStep(
        id=1,
        tool="dummy",
        tool_input="Hello",
        depends_on=[],
    )

    state = make_state()

    with pytest.raises(ValueError) as exc:
        execute_step(
            step,
            state,
            {},
        )

    assert "has no registered function" in str(exc.value)

def test_execute_step_resolves_context_variables():

    register_tool(
        Tool(
            name="echo",
            function=echo_tool,
            description="Echo tool",
            outputs=["received"],
        )
    )

    step = PlanStep(
        id=1,
        tool="echo",
        tool_input="Weather in {city}",
        depends_on=[],
    )

    state = make_state(
        context= {"city": "Mumbai"},)

    result = execute_step(
        step,
        state,
        {},
    )

    assert (
        result["result"]["output"]["received"]
        == "Weather in Mumbai"
    )


def test_execute_step_tool_failure():

    register_tool(
        Tool(
            name="failing",
            function=failing_tool,
            description="Always fails",
            outputs=["answer"],
        )
    )

    step = PlanStep(
        id=1,
        tool="failing",
        tool_input="Hello",
        depends_on=[],
    )

    state =make_state() 

    result = execute_step(
        step,
        state,
        {},
    )

    assert result["result"]["success"] is False
    assert result["result"]["output"] == {}
    assert result["result"]["error"] == "Boom!"

    record = result["record"]

    assert record.step_id == 1
    assert record.tool == "failing"
    assert record.success is False
    assert record.error == "Boom!"


def test_execute_step_resolves_step_references(): 



    register_tool(

        Tool(

            name="echo",

            function=echo_tool,

            description="Echo tool",

            outputs=["received"],

        )

    )



    tool_results = {

        1: {

            "output": {

                "answer": "OpenAI",

            }

        }

    }



    step = PlanStep(

        id=2,

        tool="echo",

        tool_input="Who is #1.answer?",

        depends_on=[1],

    )



    state = make_state()



    result = execute_step(

        step,

        state,

        tool_results,

    )



    assert (

        result["result"]["output"]["received"]

        == "Who is OpenAI?"

    )



def test_executor_node_empty_plan():


    
    state = make_state()



    result = executor_node(state)



    assert result["tool_results"] == {}

    assert result["execution_records"] == []

    assert result["context"] == {}



def test_executor_node_single_step():



    register_tool(

        Tool(

            name="dummy",

            function=dummy_tool,

            description="Dummy tool",

            outputs=["answer"],

        )

    )



    step = PlanStep(

        id=1,

        tool="dummy",

        tool_input="Hello",

        depends_on=[],

        output="result",

    )


    
    state = make_state(
                steps=[step],
            )



    result = executor_node(state)



    assert 1 in result["tool_results"]



    assert (

        result["tool_results"][1]["output"]["answer"]

        == "Orion Test Response"

    )



    assert len(result["execution_records"]) == 1



    record = result["execution_records"][0]



    assert record.step_id == 1

    assert record.success is True



    assert result["context"]["step_1"] == {

        "answer": "Orion Test Response"

    }



    assert result["context"]["result"] == "Orion Test Response"   

def test_executor_node_sequential_steps():

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    register_tool(
        Tool(
            name="echo",
            function=echo_tool,
            description="Echo tool",
            outputs=["received"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="dummy",
        tool_input="Hello",
        depends_on=[],
    )

    step2 = PlanStep(
        id=2,
        tool="echo",
        tool_input="Answer is #1.answer",
        depends_on=[1],
    )

    state = make_state(steps=[step1, step2])

    result = executor_node(state)

    assert len(result["tool_results"]) == 2

    assert (
        result["tool_results"][1]["output"]["answer"]
        == "Orion Test Response"
    )

    assert (
        result["tool_results"][2]["output"]["received"]
        == "Answer is Orion Test Response"
    )

    assert len(result["execution_records"]) == 2


def test_executor_node_parallel_steps():

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="dummy",
        tool_input="First",
        depends_on=[],
    )

    step2 = PlanStep(
        id=2,
        tool="dummy",
        tool_input="Second",
        depends_on=[],
    )

    state = make_state(
        steps = [step1, step2],
        )
        

    result = executor_node(state)

    assert len(result["tool_results"]) == 2
    assert 1 in result["tool_results"]
    assert 2 in result["tool_results"]

    assert len(result["execution_records"]) == 2


def test_executor_node_skips_completed_steps():

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="dummy",
        tool_input="Already done",
        depends_on=[],
    )

    step2 = PlanStep(
        id=2,
        tool="dummy",
        tool_input="Execute me",
        depends_on=[1],
    )

    state = make_state(
        steps= [step1, step2],
        
        tool_results= {
            1: {
                "messages": [],
                "output": {
                    "answer": "Orion Test Response"
                },
                "success": True,
                "error": None,
            }
        },
    )
    

    result = executor_node(state)

    assert len(result["tool_results"]) == 2
    assert 2 in result["tool_results"]
    assert len(result["execution_records"]) == 1

def test_executor_node_dependency_not_executed_after_failure():

    register_tool(
        Tool(
            name="fail",
            function=failing_tool,
            description="Always fails",
            outputs=["answer"],
        )
    )

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="fail",
        tool_input="Fail",
        depends_on=[],
    )

    step2 = PlanStep(
        id=2,
        tool="dummy",
        tool_input="Should not run",
        depends_on=[1],
    )

    state = make_state(
        steps= [step1, step2],
        )

    result = executor_node(state)

    assert result["tool_results"][1]["success"] is False

    assert result["tool_results"][2]["status"] == StepStatus.SKIPPED

def test_execution_summary_present():
    register_tool(
        Tool(
            name="direct",
            function=dummy_tool,
            description="Direct tool",
            outputs=["answer"],
        )
    )
    state = make_state(
        steps= [
            PlanStep(
                id=1,
                tool="direct",
                tool_input="Hello",
                depends_on=[],
            )
        ],
        
    )

    result = executor_node(state)

    summary = result["execution_summary"]

    assert summary.total_steps == 1
    assert summary.succeeded == 1
    assert summary.failed == 0
    assert summary.skipped == 0

def test_executor_emits_success_events():

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    listener = FakeListener()

    bus = EventBus()
    bus.subscribe(listener)

    step = PlanStep(
        id=1,
        tool="dummy",
        tool_input="Hello",
        depends_on=[],
    )

    state = make_state(
        steps= [step],        
        event_bus= bus,
    )

    executor_node(state)

    event_types = [
        event.type
        for event in listener.events
    ]

    assert event_types == [
        WorkflowEventType.WORKFLOW_STARTED,
        WorkflowEventType.STEP_STARTED,
        WorkflowEventType.STEP_COMPLETED,
        WorkflowEventType.WORKFLOW_COMPLETED,
    ]

def test_executor_emits_failed_event():

    register_tool(
        Tool(
            name="fail",
            function=failing_tool,
            description="Always fails",
            outputs=["answer"],
        )
    )

    listener = FakeListener()

    bus = EventBus()
    bus.subscribe(listener)

    step = PlanStep(
        id=1,
        tool="fail",
        tool_input="Hello",
        depends_on=[],
    )

    state = make_state(
        steps= [step],
        
        event_bus= bus,
    )

    executor_node(state)

    event_types = [
        event.type
        for event in listener.events
    ]

    assert event_types == [
        WorkflowEventType.WORKFLOW_STARTED,
        WorkflowEventType.STEP_STARTED,
        WorkflowEventType.STEP_FAILED,
        WorkflowEventType.WORKFLOW_COMPLETED,
    ]

    failed_event = listener.events[2]

    assert failed_event.payload["reason"] == FailureReason.EXCEPTION

def test_executor_emits_skipped_event():

    register_tool(
        Tool(
            name="fail",
            function=failing_tool,
            description="Always fails",
            outputs=["answer"],
        )
    )

    register_tool(
        Tool(
            name="dummy",
            function=dummy_tool,
            description="Dummy tool",
            outputs=["answer"],
        )
    )

    listener = FakeListener()

    bus = EventBus()
    bus.subscribe(listener)

    state = make_state(
        steps= [
            PlanStep(
                id=1,
                tool="fail",
                tool_input="Fail",
                depends_on=[],
            ),
            PlanStep(
                id=2,
                tool="dummy",
                tool_input="Should not execute",
                depends_on=[1],
            ),
        ],
        
        event_bus= bus,
    )

    executor_node(state)

    event_types = [
        event.type
        for event in listener.events
    ]

    assert WorkflowEventType.STEP_SKIPPED in event_types

def slow_tool(state):
    time.sleep(2)

    return {
        "messages": [],
        "output": {
            "value": 123,
        },
        "success": True,
    }


def test_executor_timeout():

    register_tool(
            Tool(
                name="slow_tool",
                function=slow_tool,
                description="Slow tool",
                outputs=["value"],
                timeout=0.1,
            )
        )

    state = make_state(
        steps= [
            PlanStep(
                id=1,
                tool="slow_tool",
                tool_input="",
                depends_on=[],
                output="result",
            )
        ],
        
    )

    result = executor_node(state)

    tool_result = result["tool_results"][1]
    
    assert tool_result["success"] is False
    assert tool_result["status"] == StepStatus.FAILED
    assert "timed out" in tool_result["error"].lower() \
        or "exceeded timeout" in tool_result["error"].lower()

def test_executor_emits_timeout_reason():

    register_tool(
        Tool(
            name="slow_tool",
            function=slow_tool,
            description="Slow tool",
            outputs=["value"],
            timeout=0.1,
        )
    )

    listener = FakeListener()

    bus = EventBus()
    bus.subscribe(listener)

    state = make_state(
        steps= [
            PlanStep(
                id=1,
                tool="slow_tool",
                tool_input="",
                depends_on=[],
            )
        ],
        
        event_bus= bus,
    )

    executor_node(state)

    failed_event = listener.events[2]

    assert failed_event.type == WorkflowEventType.STEP_FAILED
    assert failed_event.payload["reason"] == FailureReason.TIMEOUT

def fast_tool(state):

    return {
        "messages": [],
        "output": {
            "value": 123,
        },
        "success": True,
    }


def test_executor_timeout_success():

    register_tool(
        Tool(
            name="fast_tool",
            function=fast_tool,
            description="Fast tool",
            outputs=["value"],
            timeout=5,
        )
    )

    state = make_state(
        steps= [
            PlanStep(
                id=1,
                tool="fast_tool",
                tool_input="",
                depends_on=[],
                output="result",
            )
        ],
        
    )

    result = executor_node(state)

    tool_result = result["tool_results"][1]

    assert tool_result["success"] is True
    assert tool_result["status"] == StepStatus.SUCCESS

def test_timeout_creates_execution_record():

    register_tool(
        Tool(
            name="slow_tool_record",
            function=slow_tool,
            description="Slow tool",
            outputs=["value"],
            timeout=0.1,
        )
    )

    state = make_state(
        steps= [
            PlanStep(
                id=1,
                tool="slow_tool_record",
                tool_input="",
                depends_on=[],
                output="result",
            )
        ],
        
    )

    result = executor_node(state)

    record = result["execution_records"][0]

    assert record.success is False
    assert record.duration > 0
    assert "timed out" in record.error.lower()

def test_executor_waits_for_approval():

    register_tool(
        Tool(
            name="approval_tool",
            function=echo_tool,
            description="Approval tool",
            outputs=["answer"],
        )
    )

    step = PlanStep(
        id=1,
        tool="approval_tool",
        tool_input="",
        depends_on=[],
        output="answer",
        approval=ApprovalRequest(
            step_id=1,
            tool="approval_tool",
            reason="Requires manual approval",
        ),
    )

    state = make_state(
        steps=[step],
    )
    print(type(step))
    print(type(state["steps"][0]))
    result = executor_node(state)

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.WAITING_FOR_APPROVAL
    )
    assert result["approval_request"] == step.approval

def test_executor_does_not_execute_step_waiting_for_approval():

    executed = {
        "called": False,
    }

    def approval_tool(state):

        executed["called"] = True

        return {
            "messages": [],
            "output": {
                "answer": "Executed",
            },
            "success": True,
            "error": None,
        }

    register_tool(
        Tool(
            name="approval_tool",
            function=approval_tool,
            description="Approval tool",
            outputs=["answer"],
        )
    )

    step = PlanStep(
        id=1,
        tool="approval_tool",
        tool_input="",
        depends_on=[],
        output="answer",
        approval=ApprovalRequest(
            step_id=1,
            tool="approval_tool",
            reason="Requires manual approval",
        ),
    )

    state = make_state(
        steps=[step],
    )

    executor_node(state)

    assert executed["called"] is False

def test_executor_continues_independent_steps_while_waiting_for_approval():

    register_tool(
        Tool(
            name="approval_tool",
            function=echo_tool,
            description="Approval tool",
            outputs=["answer"],
        )
    )

    register_tool(
        Tool(
            name="independent_tool",
            function=echo_tool,
            description="Independent tool",
            outputs=["answer"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="approval_tool",
        tool_input="",
        depends_on=[],
        output="approval_output",
        approval=ApprovalRequest(
            step_id=1,
            tool="approval_tool",
            reason="Requires manual approval",
        ),
    )

    step2 = PlanStep(
        id=2,
        tool="echo_tool",
        tool_input="",
        depends_on=[1],
        output="dependent_output",
    )

    step3 = PlanStep(
        id=3,
        tool="independent_tool",
        tool_input="",
        depends_on=[],
        output="independent_output",
    )

    state = make_state(
        steps=[step1, step2, step3],
    )

    result = executor_node(state)

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.WAITING_FOR_APPROVAL
    )

    assert (
        result["tool_results"][3]["status"]
        == StepStatus.SUCCESS
    )

    assert 2 not in result["tool_results"]


def test_resume_after_approval():

    register_tool(
        Tool(
            name="approval_tool",
            function=echo_tool,
            description="Approval tool",
            outputs=["received"],
        )
    )

    register_tool(
        Tool(
            name="echo_tool",
            function=echo_tool,
            description="Echo tool",
            outputs=["received"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="approval_tool",
        tool_input="Approved input",
        depends_on=[],
        output="approval_output",
        approval=ApprovalRequest(
            step_id=1,
            tool="approval_tool",
            reason="Requires manual approval",
        ),
    )

    step2 = PlanStep(
        id=2,
        tool="echo_tool",
        tool_input="#1.received",
        depends_on=[1],
        output="final_answer",
    )

    state = make_state(
        steps=[step1, step2],
    )

    result = executor_node(state)

    assert (
            result["tool_results"][1]["status"]
            == StepStatus.WAITING_FOR_APPROVAL
        )
    state.update(result)

    state["approval_decision"] = (
        ApprovalDecision.APPROVED
    )

    result = executor_node(state)
    print(result["tool_results"][1]["output"])
    assert (
        result["tool_results"][1]["status"]
        == StepStatus.SUCCESS
    )

    assert (
        result["tool_results"][2]["status"]
        == StepStatus.SUCCESS
    )

def test_resume_after_rejection():

    register_tool(
        Tool(
            name="approval_tool",
            function=echo_tool,
            description="Approval tool",
            outputs=["received"],
        )
    )

    register_tool(
        Tool(
            name="echo_tool",
            function=echo_tool,
            description="Echo tool",
            outputs=["received"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="approval_tool",
        tool_input="Approved input",
        depends_on=[],
        output="approval_output",
        approval=ApprovalRequest(
            step_id=1,
            tool="approval_tool",
            reason="Requires manual approval",
        ),
    )

    step2 = PlanStep(
        id=2,
        tool="echo_tool",
        tool_input="#1.received",
        depends_on=[1],
        output="final_answer",
    )

    state = make_state(
        steps=[step1, step2],
    )

    result = executor_node(state)

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.WAITING_FOR_APPROVAL
    )

    state.update(result)

    state["approval_decision"] = (
        ApprovalDecision.REJECTED
    )

    result = executor_node(state)

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.FAILED
    )

    assert (
        result["tool_results"][2]["status"]
        == StepStatus.SKIPPED
    )

def yes_tool(state):

    return {
        "messages": [],
        "output": {
            "answer": "eligible",
        },
        "success": True,
        "error": None,
    }


def test_executor_branch_yes_path():

    register_tool(
        Tool(
            name="check",
            function=yes_tool,
            description="Check",
            outputs=["answer"],
        )
    )

    register_tool(
        Tool(
            name="dummy",
            function=echo_tool,
            description="Dummy",
            outputs=["answer"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="check",
        tool_input="Check",
        depends_on=[],
    )

    step2 = PlanStep(
        id=2,
        tool="dummy",
        tool_input="Approve",
        depends_on=[1],
        condition="#1.answer == 'eligible'",
    )

    step3 = PlanStep(
        id=3,
        tool="dummy",
        tool_input="Reject",
        depends_on=[1],
        condition="#1.answer != 'eligible'",
    )

    state = make_state(
        steps=[step1, step2, step3]
    )

    result = executor_node(state)

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.SUCCESS
    )

    assert (
        result["tool_results"][2]["status"]
        == StepStatus.SUCCESS
    )

    assert (
        result["tool_results"][3]["status"]
        == StepStatus.SKIPPED
    )

def no_tool(state):

    return {
        "messages": [],
        "output": {
            "answer": "not eligible",
        },
        "success": True,
        "error": None,
    }


def test_executor_branch_no_path():

    register_tool(
        Tool(
            name="check",
            function=no_tool,
            description="Check",
            outputs=["answer"],
        )
    )

    register_tool(
        Tool(
            name="dummy",
            function=echo_tool,
            description="Dummy",
            outputs=["answer"],
        )
    )

    step1 = PlanStep(
        id=1,
        tool="check",
        tool_input="Check",
        depends_on=[],
    )

    step2 = PlanStep(
        id=2,
        tool="dummy",
        tool_input="Approve",
        depends_on=[1],
        condition="#1.answer == 'eligible'",
    )

    step3 = PlanStep(
        id=3,
        tool="dummy",
        tool_input="Reject",
        depends_on=[1],
        condition="#1.answer != 'eligible'",
    )

    state = make_state(
        steps=[step1, step2, step3]
    )

    result = executor_node(state)

    assert (
        result["tool_results"][1]["status"]
        == StepStatus.SUCCESS
    )

    assert (
        result["tool_results"][2]["status"]
        == StepStatus.SKIPPED
    )

    assert (
        result["tool_results"][3]["status"]
        == StepStatus.SUCCESS
    )

