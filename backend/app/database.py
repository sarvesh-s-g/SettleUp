"""Database engine, session factory and the FastAPI session dependency."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# pool_pre_ping checks that a pooled connection is still alive before using it.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# autoflush=False: SQL is sent only when we flush/commit explicitly or run a query.
# expire_on_commit=False: objects keep their loaded values after commit, so we can
# still build the response from them.
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class of every ORM model. Base.metadata describes all tables."""


def get_db() -> Generator[Session, None, None]:
    """Give each request its own session and always close it afterwards.

    If the request handler raises, any uncommitted work is rolled back.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
