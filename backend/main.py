from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from typing import List

from .database import Base, engine, SessionLocal
from .models import Transacao
from .schemas import TransacaoCreate, TransacaoOut

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meu Financeiro")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.post("/transacoes", response_model=TransacaoOut)
def criar_transacao(t: TransacaoCreate, db: Session = Depends(get_db)):
    nova = Transacao(**t.model_dump())
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova

@app.get("/transacoes", response_model=List[TransacaoOut])
def listar_transacoes(db: Session = Depends(get_db)):
    return db.query(Transacao).order_by(Transacao.data.desc()).all()
