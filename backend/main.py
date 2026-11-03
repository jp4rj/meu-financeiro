from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List
from datetime import date
import calendar

from .database import Base, engine, SessionLocal
from .models import Transacao, DespesaFixa, FixaGerada
from .schemas import (
    TransacaoCreate, TransacaoUpdate, TransacaoOut,
    DespesaFixaCreate, DespesaFixaUpdate, DespesaFixaOut,
    ParcelamentoCreate,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meu Financeiro")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Transações ----------

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


@app.get("/transacoes/mes/{ano}/{mes}", response_model=List[TransacaoOut])
def transacoes_do_mes(ano: int, mes: int, db: Session = Depends(get_db)):
    _gerar_fixas_do_mes(ano, mes, db)
    return (
        db.query(Transacao)
        .filter(extract("year", Transacao.data) == ano)
        .filter(extract("month", Transacao.data) == mes)
        .order_by(Transacao.data.desc())
        .all()
    )


@app.put("/transacoes/{transacao_id}", response_model=TransacaoOut)
def editar_transacao(transacao_id: int, dados: TransacaoUpdate, db: Session = Depends(get_db)):
    t = db.query(Transacao).filter(Transacao.id == transacao_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(t, campo, valor)
    db.commit()
    db.refresh(t)
    return t


# ---------- Parcelamento ----------

@app.post("/parcelamentos", response_model=List[TransacaoOut])
def criar_parcelamento(p: ParcelamentoCreate, db: Session = Depends(get_db)):
    if p.num_parcelas < 2:
        raise HTTPException(status_code=400, detail="Use no mínimo 2 parcelas")
    valor_parcela = round(-abs(p.valor_total) / p.num_parcelas, 2)

    ano, mes = p.data_primeira_parcela.year, p.data_primeira_parcela.month
    dia = p.data_primeira_parcela.day
    criadas = []

    for i in range(1, p.num_parcelas + 1):
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        data_parcela = date(ano, mes, min(dia, ultimo_dia))

        t = Transacao(
            data=data_parcela,
            descricao=f"{p.descricao} ({i}/{p.num_parcelas})",
            valor=valor_parcela,
            categoria=p.categoria,
            tipo=p.tipo,
            recorrente=False,
        )
        db.add(t)
        db.flush()
        criadas.append(t)

        mes += 1
        if mes > 12:
            mes = 1
            ano += 1

    db.commit()
    for t in criadas:
        db.refresh(t)
    return criadas


# ---------- Despesas fixas ----------

@app.post("/despesas-fixas", response_model=DespesaFixaOut)
def criar_despesa_fixa(d: DespesaFixaCreate, db: Session = Depends(get_db)):
    nova = DespesaFixa(
        descricao=d.descricao,
        valor=-abs(d.valor),
        categoria=d.categoria,
        dia_vencimento=d.dia_vencimento,
        ativa=True,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


@app.get("/despesas-fixas", response_model=List[DespesaFixaOut])
def listar_despesas_fixas(db: Session = Depends(get_db)):
    return db.query(DespesaFixa).order_by(DespesaFixa.descricao).all()


@app.put("/despesas-fixas/{fixa_id}", response_model=DespesaFixaOut)
def editar_despesa_fixa(fixa_id: int, dados: DespesaFixaUpdate, db: Session = Depends(get_db)):
    f = db.query(DespesaFixa).filter(DespesaFixa.id == fixa_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Despesa fixa não encontrada")
    alteracoes = dados.model_dump(exclude_unset=True)
    if "valor" in alteracoes and alteracoes["valor"] is not None:
        alteracoes["valor"] = -abs(alteracoes["valor"])
    for campo, valor in alteracoes.items():
        setattr(f, campo, valor)
    db.commit()
    db.refresh(f)
    return f


def _gerar_fixas_do_mes(ano: int, mes: int, db: Session):
    """Gera as transações das despesas fixas ativas do mês, sem duplicar."""
    fixas = db.query(DespesaFixa).filter(DespesaFixa.ativa == True).all()
    for f in fixas:
        ja_gerada = (
            db.query(FixaGerada)
            .filter(FixaGerada.despesa_fixa_id == f.id)
            .filter(FixaGerada.ano == ano)
            .filter(FixaGerada.mes == mes)
            .first()
        )
        if ja_gerada:
            continue

        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(f.dia_vencimento, ultimo_dia)
        t = Transacao(
            data=date(ano, mes, dia),
            descricao=f.descricao,
            valor=f.valor,
            categoria=f.categoria,
            tipo="Fixo",
            recorrente=True,
        )
        db.add(t)
        db.add(FixaGerada(despesa_fixa_id=f.id, ano=ano, mes=mes))
    db.commit()
