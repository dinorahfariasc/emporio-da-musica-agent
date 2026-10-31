from fastapi import FastAPI

from app.api import health, stream_test

app = FastAPI(title="Empório da Música Agent API", version="0.1.0")
app.include_router(health.router)
app.include_router(stream_test.router)
