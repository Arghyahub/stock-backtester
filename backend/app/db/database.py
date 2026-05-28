from app.core.config import env
from sqlalchemy import create_engine # connects to db
from sqlalchemy.orm import declarative_base # creates base orm class for models
from sqlalchemy.orm import sessionmaker # creates session

DATABASE_URL = env.DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    # For Sqlite
    # connect_args={"check_same_thread": False}, # allows multiple threads to access the db
    # For Postgres
    pool_size=100,
    max_overflow=0,
    echo=True
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