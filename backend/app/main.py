"""FastAPI application entry point.

Run with:  uvicorn app.main:app --reload
Swagger UI: http://localhost:8000/docs
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.routers import auth, dashboard, expenses, groups, invites, settlements

logger = logging.getLogger("settleup")

API_PREFIX = "/api/v1"

app = FastAPI(
    title="SettleUp API",
    description="Group expense management and settlement platform. "
    "Log in via /auth/login, then click **Authorize** and paste the access_token.",
    version="1.0.0",
)

# CORS: allow the React dev server (a different origin/port) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,  # we send the JWT in a header, not in cookies
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.exception_handler(RequestValidationError)
def validation_error_handler(request: Request, exc: RequestValidationError):
    """Return 422 with only the field location and message.

    FastAPI's default response echoes the submitted value back ("input"), which for
    /auth/register would include the password, so we strip it."""
    errors = [
        {"loc": list(err.get("loc", [])), "msg": err.get("msg", "Invalid value"), "type": err.get("type")}
        for err in exc.errors()
    ]
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, content={"detail": errors})


@app.exception_handler(IntegrityError)
def integrity_error_handler(request: Request, exc: IntegrityError):
    """A database constraint rejected the data. Do not leak SQL details to clients."""
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc.orig)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "The request conflicts with existing data"},
    )


@app.exception_handler(Exception)
def unhandled_error_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


app.include_router(auth.router, prefix=API_PREFIX)
app.include_router(groups.router, prefix=API_PREFIX)
app.include_router(invites.router, prefix=API_PREFIX)
app.include_router(expenses.router, prefix=API_PREFIX)
app.include_router(settlements.router, prefix=API_PREFIX)
app.include_router(dashboard.router, prefix=API_PREFIX)


@app.get(f"{API_PREFIX}/health", tags=["Health"])
def health():
    """Simple liveness check used when setting up the project."""
    return {"status": "ok"}
