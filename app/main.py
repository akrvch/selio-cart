from __future__ import annotations

import asyncio
import logging
from concurrent import futures

import grpc
from fastapi import FastAPI

from app.db import init_engines
from app.settings import settings
from app.api.v1.routes_read import router as read_router
from app.api.v1.routes_write import router as write_router
from app.grpc.server import serve_grpc


log = logging.getLogger(__name__)


app = FastAPI(title="Sellio Cart", version="0.1.0")
app.include_router(read_router)
app.include_router(write_router)


@app.on_event("startup")
async def on_startup() -> None:
    init_engines()
    # Start gRPC server in background
    asyncio.get_event_loop().create_task(serve_grpc(settings.grpc_port))
    log.info("gRPC server started on port %s", settings.grpc_port)


@app.get("/")
async def root():
    return {"service": "sellio-cart"}


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


