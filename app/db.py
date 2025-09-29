from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from .settings import settings


def create_engine(url: str) -> AsyncEngine:
    return create_async_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=20)


engine: AsyncEngine | None = None
session_factory: async_sessionmaker[AsyncSession] | None = None


def init_engines() -> None:
    global engine, session_factory
    if not settings.database_url:
        return
    engine = create_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def session_ctx() -> AsyncIterator[AsyncSession]:
    if session_factory is None:
        init_engines()
    assert session_factory is not None, "Session factory is not initialized"
    async with session_factory() as session:
        yield session


async def session_dep() -> AsyncIterator[AsyncSession]:
    async with session_ctx() as session:
        yield session


