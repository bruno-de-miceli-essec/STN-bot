import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Chemin SQLite stable (Render écrit dans /opt/render/project/src/)
DEFAULT_SQLITE_PATH = os.getenv("SQLITE_PATH", "/opt/render/project/src/app.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

# Pour SQLite, autoriser l'accès multi-threads des workers web
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
Base = declarative_base()

def init_db() -> None:
    """Créer les tables si besoin (idempotent). À appeler au démarrage et avant tout accès DB."""
    from models import Form, Response  # noqa: F401 (enregistrement des modèles)
    with engine.begin() as conn:
        Base.metadata.create_all(bind=conn)