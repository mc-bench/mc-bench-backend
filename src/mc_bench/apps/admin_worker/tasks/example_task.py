from ..app import app


@app.task(name="admin_example_task")
def example_task():
    return {"ok": True}
