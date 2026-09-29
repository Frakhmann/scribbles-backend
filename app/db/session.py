from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()

# dependency
def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# alias for type hints
DbDep = Session
