
from fastapi import FastAPI

app = FastAPI(title="MemeLens API")


@app.get("/healthz")
def healthz():
    # DB connectivity check lands here in a later task.
    return {"status": "ok"}
