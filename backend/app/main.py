from fastapi import FastAPI

from app.routers import memes

app = FastAPI(title="MemeLens API")
app.include_router(memes.router)


@app.get("/healthz")
def healthz():
    # DB connectivity check lands here in a later task.
    return {"status": "ok"}
