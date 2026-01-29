from collections.abc import AsyncGenerator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# Async engine and session
engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Sync engine and session (for LangGraph agents)
sync_engine = create_engine(settings.database_url_sync, echo=False)
sync_session_factory = sessionmaker(sync_engine, class_=Session, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextmanager
def get_sync_session():
    """
    동기 세션 컨텍스트 매니저 (LangGraph 에이전트용)

    Yields:
        Session: 동기 SQLAlchemy 세션
    """
    session = sync_session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
