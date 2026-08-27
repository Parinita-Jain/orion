from persistence import save_workflow

state = {
    "workflow_id": "test-workflow",
    "iteration": 1,
}

save_workflow(state)