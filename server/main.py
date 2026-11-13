from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
from db import create_db_and_tables
from config import settings
from routers import exercises
import time
import logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield   # server runs here

app = FastAPI(lifespan=lifespan)
# we have put all our exercise routes in exercises.py that we import from
app.include_router(exercises.router)

logger = logging.getLogger("uvicorn")

#  defining what the error and status codes look like
@app.middleware("http")
async def log_requests(request, call_next):
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms:.1f}ms)")
    return response

# our global error handler, so anything without an HTTP exception will be caught by this
@app.exception_handler(Exception)
async def catch_all(request: Request, exc: Exception):
    # .exception will attach the full stack trace to the console too
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    # Below is what the client sees
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# our global error handler for any 422 Unprocessable Content Errors
# pretty unnecessary now - really depends on how the frontend is designed
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request, exc):
    errors = []
    for e in exc.errors():
        field = ".".join(str(part) for part in e ["loc"][1:]) # drops the body
        message = e["msg"].removeprefix("Value error, ")
        errors.append({"field": field or "request", "message": message})
    return JSONResponse(status_code=422, content={"detail": "Invalid input", "errors": errors})

#testing env file
@app.get("/")
def root():
    return {"app": "Hello World"}