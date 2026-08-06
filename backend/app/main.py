from fastapi import FastAPI

from app.routers import memes, search

app = FastAPI(title="MemeLens API")
app.include_router(memes.router)
app.include_router(search.router)


@app.get("/healthz")
def healthz():
    # DB connectivity check lands here in a later task.
    return {"status": "ok"}
