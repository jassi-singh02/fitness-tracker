from fastapi import FastAPI
from routers import exercises
import time
import logging

app = FastAPI()
# we have put all our exercise routes in exercises.py that we import from
app.include_router(exercises.router)

logger = logging.getLogger("uvicorn")

# Here we can see that we are defining what the error and status codes look like
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms: .1f}ms)")
    return response