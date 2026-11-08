from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import keyring
import os

os.makedirs("data", exist_ok=True)

SENHA_DB = keyring.get_password("meu_financeiro", "jamiro")
if not SENHA_DB:
    raise RuntimeError("Senha do banco não encontrada no keyring. Rode o passo 2.")

CAMINHO_DB = os.path.abspath("data/financeiro.db")

DATABASE_URL = URL.create(
    drivername="sqlite+pysqlcipher",
    password=SENHA_DB,
    database=CAMINHO_DB,
)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()
