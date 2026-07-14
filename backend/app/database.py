from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy_utils import database_exists, create_database

from app.config import settings

# Works for Postgres out of the box. For MySQL swap DATABASE_URL to
# mysql+pymysql://user:pass@host:3306/hcp_crm and `pip install pymysql`.
engine = create_engine(settings.database_url, pool_pre_ping=True)


def ensure_database_exists():
    """Create the target database itself (not just its tables) if it
    doesn't exist yet. Connects to the server's default maintenance DB
    (e.g. 'postgres' for Postgres) using the same credentials/host from
    DATABASE_URL, issues CREATE DATABASE, then leaves `engine` pointed at
    the real target DB for everything else. Requires the DB user to have
    CREATE DATABASE privileges."""
    if not database_exists(engine.url):
        create_database(engine.url)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
