from typing import Generator
from sqlmodel import SQLModel, Session, create_engine
from app.config import settings

# SQLite connection args for multi-threading support in FastAPI
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, echo=False, connect_args=connect_args)

def init_db() -> None:
    """Initialize database tables and seed with FinEdge brand canon data if empty."""
    SQLModel.metadata.create_all(engine)

def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database sessions."""
    with Session(engine) as session:
        yield session
