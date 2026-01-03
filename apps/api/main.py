"""FastAPI main application."""

import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from apps.api.routers import configs, controls, data, executions, health, plans, portfolio
from packages.ops.logging import setup_logging

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Trading System API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware: request_id, run_id
@app.middleware("http")
async def add_request_ids(request: Request, call_next: Callable) -> Response:
    """Add request_id and run_id to request."""
    request_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())

    request.state.request_id = request_id
    request.state.run_id = run_id

    response = await call_next(request)

    # Add to response headers
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Run-ID"] = run_id

    return response


app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(controls.router, prefix="/controls", tags=["controls"])
app.include_router(configs.router, prefix="/configs", tags=["configs"])
app.include_router(plans.router, prefix="/plans", tags=["plans"])
app.include_router(executions.router, prefix="/executions", tags=["executions"])
app.include_router(portfolio.router, prefix="/portfolio", tags=["portfolio"])
app.include_router(data.router, prefix="/data", tags=["data"])


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
