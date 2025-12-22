from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
from app.core.config import settings
from app.db.base import Base  # <- Se importa la Base aquí

# Engine de conexión
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)

# Sesión de base de datos
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency para FastAPI
def get_db() -> Generator[Session, None, None]:
    """
    Dependency que provee una sesión de base de datos.
    Se cierra automáticamente después de cada request.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
