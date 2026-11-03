from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os

os.makedirs("data", exist_ok=True)
DATABASE_URL = "sqlite:///./data/financeiro.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
