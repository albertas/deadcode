# Task: Generate unused-code test cases for the FastAPI framework

Create a set of test cases that exercise how `deadcode` analyses code written
with the FastAPI framework (route handlers decorated with `@app.get`/`@router.post`,
dependency-injection callables, Pydantic models, lifecycle/event hooks, etc.), where
framework-invoked symbols are genuinely "used" even though no in-project call site
exists. Then verify that `deadcode` handles these cases correctly — not reporting
framework entrypoints as false positives while still detecting truly unused code —
and adjust the tool if it does not.
