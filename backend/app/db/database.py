from app.core.config import env
from sqlalchemy import create_engine # connects to db
from sqlalchemy.orm import declarative_base # creates base orm class for models
from sqlalchemy.orm import sessionmaker # creates session

DATABASE_URL = env.DATABASE_URL
# SQLAlchemy treats plain ``postgresql://`` as the psycopg2 dialect. The
# application deliberately depends on Psycopg 3 (``psycopg``), so accept the
# common URL form supplied by hosted Postgres providers and select that driver.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(
    DATABASE_URL,
    # For Sqlite
    # connect_args={"check_same_thread": False}, # allows multiple threads to access the db
    # For Postgres
    pool_size=100,
    max_overflow=0,
    echo=env.DEBUG
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine  # session can only be created with engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
