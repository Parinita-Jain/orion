from registry import get_tool


def validate_plan(steps):
    if not steps:
       return ["Execution plan is empty."]
    errors = []

    # Check duplicate IDs

    ids = set()

    for step in steps:

        if step.id in ids:

            errors.append(
                f"Duplicate step id: {step.id}"
            )

        ids.add(step.id)
    
    #Check unknown tools
    for step in steps:

        if get_tool(step.tool) is None:

            errors.append(
                f"Unknown tool: {step.tool}"
            )
    
    #Check dependency exists
    step_ids = {
    step.id
    for step in steps 
    }
        
    for step in steps:

        for dependency in step.depends_on:

            if dependency not in step_ids:

                errors.append(
                    f"Step {step.id} depends on "
                    f"missing step {dependency}"
                )
    
    # Check self-dependency
    for step in steps:

        if step.id in step.depends_on:

            errors.append(
                f"Step {step.id} depends on itself."
            )
    
    #Check dependency order
    for step in steps:

        for dependency in step.depends_on:

            if dependency >= step.id:

                errors.append(
                    f"Step {step.id} depends on "
                    f"future step {dependency}"
                )

    expected = 1

    for step in sorted(steps, key=lambda s: s.id):

        if step.id != expected:

            errors.append(
                f"Expected step id {expected}, found {step.id}"
            )

        expected += 1

    for step in steps:
    
            if (
                step.approval is not None
                and step.approval.required
                and (
                    step.approval.reason is None
                    or not step.approval.reason.strip()
                )
            ):
                errors.append(
                    f"Step {step.id}: approval requires a reason."
                )

    return errors

