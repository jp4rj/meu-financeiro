from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import extract
from typing import List
from datetime import date, datetime
from pydantic import BaseModel
import calendar
import os
import shutil
import sqlite3
import tempfile

from .database import Base, engine, SessionLocal, CAMINHO_DB
from .models import (
    Transacao, Recorrente, RecorrenteGerada,
    Ativo, MovimentacaoInvestimento, AtualizacaoSaldo,
)
from .schemas import (
    TransacaoCreate, TransacaoUpdate, TransacaoOut,
    RecorrenteCreate, RecorrenteUpdate, RecorrenteOut,
    ParcelamentoCreate,
    AtivoCreate, AtivoUpdate, AtivoOut, AtivoComSaldo,
    MovimentacaoCreate, MovimentacaoUpdate, MovimentacaoOut,
    AtualizacaoSaldoCreate, AtualizacaoSaldoOut,
    ResumoInvestimentosMes,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Meu Financeiro")

DB_FILE = CAMINHO_DB


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class SaldoAcumulado(BaseModel):
    saldo: float
    receitas: float
    despesas: float
    aportes: float
    resgates: float


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
    _gerar_recorrentes_do_mes(ano, mes, db)
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


# ---------- Recorrentes ----------

@app.post("/recorrentes", response_model=RecorrenteOut)
def criar_recorrente(r: RecorrenteCreate, db: Session = Depends(get_db)):
    if r.natureza not in ("Despesa", "Receita"):
        raise HTTPException(status_code=400, detail="Natureza deve ser 'Despesa' ou 'Receita'")
    valor_final = -abs(r.valor) if r.natureza == "Despesa" else abs(r.valor)
    nova = Recorrente(
        descricao=r.descricao, valor=valor_final, categoria=r.categoria,
        natureza=r.natureza, dia_vencimento=r.dia_vencimento, ativa=True,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return nova


@app.get("/recorrentes", response_model=List[RecorrenteOut])
def listar_recorrentes(db: Session = Depends(get_db)):
    return db.query(Recorrente).order_by(Recorrente.descricao).all()


@app.put("/recorrentes/{recorrente_id}", response_model=RecorrenteOut)
def editar_recorrente(recorrente_id: int, dados: RecorrenteUpdate, db: Session = Depends(get_db)):
    r = db.query(Recorrente).filter(Recorrente.id == recorrente_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recorrente não encontrado")
    alteracoes = dados.model_dump(exclude_unset=True)
    if "natureza" in alteracoes and alteracoes["natureza"] not in (None, "Despesa", "Receita"):
        raise HTTPException(status_code=400, detail="Natureza deve ser 'Despesa' ou 'Receita'")
    if "valor" in alteracoes and alteracoes["valor"] is not None:
        natureza = alteracoes.get("natureza", r.natureza)
        alteracoes["valor"] = -abs(alteracoes["valor"]) if natureza == "Despesa" else abs(alteracoes["valor"])
    for campo, valor in alteracoes.items():
        setattr(r, campo, valor)
    db.commit()
    db.refresh(r)
    return r


def _gerar_recorrentes_do_mes(ano: int, mes: int, db: Session):
    recorrentes = db.query(Recorrente).filter(Recorrente.ativa == True).all()
    for r in recorrentes:
        ja_gerada = (
            db.query(RecorrenteGerada)
            .filter(RecorrenteGerada.recorrente_id == r.id)
            .filter(RecorrenteGerada.ano == ano)
            .filter(RecorrenteGerada.mes == mes)
            .first()
        )
        if ja_gerada:
            continue
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        dia = min(r.dia_vencimento, ultimo_dia)
        tipo = "Fixo" if r.natureza == "Despesa" else "Receita"
        t = Transacao(
            data=date(ano, mes, dia), descricao=r.descricao, valor=r.valor,
            categoria=r.categoria, tipo=tipo, recorrente=True,
        )
        db.add(t)
        db.add(RecorrenteGerada(recorrente_id=r.id, ano=ano, mes=mes))
    db.commit()


# ---------- Ativos ----------

@app.post("/ativos", response_model=AtivoOut)
def criar_ativo(a: AtivoCreate, db: Session = Depends(get_db)):
    novo = Ativo(nome=a.nome, categoria=a.categoria, ativo=True)
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo


def _calcular_saldo_ativo(ativo_id: int, db: Session) -> float:
    ultima = (
        db.query(AtualizacaoSaldo)
        .filter(AtualizacaoSaldo.ativo_id == ativo_id)
        .order_by(AtualizacaoSaldo.data.desc(), AtualizacaoSaldo.id.desc())
        .first()
    )
    if not ultima:
        return 0.0
    movs_desde = (
        db.query(MovimentacaoInvestimento)
        .filter(MovimentacaoInvestimento.ativo_id == ativo_id)
        .filter(MovimentacaoInvestimento.data >= ultima.data)
        .filter(MovimentacaoInvestimento.automatica == False)
        .all()
    )
    delta = 0.0
    for m in movs_desde:
        if m.tipo == "Aporte":
            delta += m.valor
        elif m.tipo == "Resgate":
            delta -= m.valor
    return ultima.saldo_informado + delta


@app.get("/ativos", response_model=List[AtivoComSaldo])
def listar_ativos(db: Session = Depends(get_db)):
    ativos = db.query(Ativo).order_by(Ativo.nome).all()
    resultado = []
    for a in ativos:
        saldo = _calcular_saldo_ativo(a.id, db)
        resultado.append(AtivoComSaldo(
            id=a.id, nome=a.nome, categoria=a.categoria, ativo=a.ativo, saldo=saldo,
        ))
    return resultado


@app.put("/ativos/{ativo_id}", response_model=AtivoOut)
def editar_ativo(ativo_id: int, dados: AtivoUpdate, db: Session = Depends(get_db)):
    a = db.query(Ativo).filter(Ativo.id == ativo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(a, campo, valor)
    db.commit()
    db.refresh(a)
    return a


# ---------- Movimentações ----------

def _criar_ou_atualizar_espelho(mov: MovimentacaoInvestimento, ativo: Ativo, db: Session):
    if mov.tipo in ("Rendimento", "Prejuízo"):
        if mov.transacao_id:
            espelho = db.query(Transacao).filter(Transacao.id == mov.transacao_id).first()
            if espelho:
                db.delete(espelho)
            mov.transacao_id = None
        return

    valor_caixa = -abs(mov.valor) if mov.tipo == "Aporte" else abs(mov.valor)
    descricao = f"{mov.tipo}: {ativo.nome}"

    if mov.transacao_id:
        espelho = db.query(Transacao).filter(Transacao.id == mov.transacao_id).first()
        if espelho:
            espelho.data = mov.data
            espelho.descricao = descricao
            espelho.valor = valor_caixa
            espelho.categoria = ativo.categoria
            espelho.tipo = "Investimento" if mov.tipo == "Aporte" else "Receita"
            return

    espelho = Transacao(
        data=mov.data,
        descricao=descricao,
        valor=valor_caixa,
        categoria=ativo.categoria,
        tipo="Investimento" if mov.tipo == "Aporte" else "Receita",
        recorrente=False,
    )
    db.add(espelho)
    db.flush()
    mov.transacao_id = espelho.id


@app.post("/movimentacoes", response_model=MovimentacaoOut)
def criar_movimentacao(m: MovimentacaoCreate, db: Session = Depends(get_db)):
    if m.tipo not in ("Aporte", "Resgate"):
        raise HTTPException(status_code=400, detail="Tipo deve ser Aporte ou Resgate. Rendimento vem da atualização de saldo.")
    if m.valor <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser positivo")
    ativo = db.query(Ativo).filter(Ativo.id == m.ativo_id).first()
    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    nova = MovimentacaoInvestimento(
        ativo_id=m.ativo_id, data=m.data, tipo=m.tipo,
        valor=abs(m.valor), observacao=m.observacao, automatica=False,
    )
    db.add(nova)
    db.flush()
    _criar_ou_atualizar_espelho(nova, ativo, db)
    db.commit()
    db.refresh(nova)
    return nova


@app.get("/movimentacoes", response_model=List[MovimentacaoOut])
def listar_movimentacoes(ativo_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(MovimentacaoInvestimento)
    if ativo_id is not None:
        q = q.filter(MovimentacaoInvestimento.ativo_id == ativo_id)
    return q.order_by(MovimentacaoInvestimento.data.desc()).all()


@app.put("/movimentacoes/{mov_id}", response_model=MovimentacaoOut)
def editar_movimentacao(mov_id: int, dados: MovimentacaoUpdate, db: Session = Depends(get_db)):
    m = db.query(MovimentacaoInvestimento).filter(MovimentacaoInvestimento.id == mov_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Movimentação não encontrada")
    if m.automatica:
        raise HTTPException(status_code=400, detail="Movimentações automáticas (Rendimento/Prejuízo) não podem ser editadas aqui.")
    alteracoes = dados.model_dump(exclude_unset=True)
    if "tipo" in alteracoes and alteracoes["tipo"] not in (None, "Aporte", "Resgate"):
        raise HTTPException(status_code=400, detail="Tipo deve ser Aporte ou Resgate")
    if "valor" in alteracoes and alteracoes["valor"] is not None:
        alteracoes["valor"] = abs(alteracoes["valor"])
    for campo, valor in alteracoes.items():
        setattr(m, campo, valor)
    ativo = db.query(Ativo).filter(Ativo.id == m.ativo_id).first()
    _criar_ou_atualizar_espelho(m, ativo, db)
    db.commit()
    db.refresh(m)
    return m


@app.get("/movimentacoes/mes/{ano}/{mes}", response_model=ResumoInvestimentosMes)
def resumo_movimentacoes_mes(ano: int, mes: int, db: Session = Depends(get_db)):
    movs = (
        db.query(MovimentacaoInvestimento)
        .filter(extract("year", MovimentacaoInvestimento.data) == ano)
        .filter(extract("month", MovimentacaoInvestimento.data) == mes)
        .all()
    )
    aportes = sum(m.valor for m in movs if m.tipo == "Aporte")
    resgates = sum(m.valor for m in movs if m.tipo == "Resgate")
    rendimentos = sum(m.valor for m in movs if m.tipo == "Rendimento")
    prejuizos = sum(m.valor for m in movs if m.tipo == "Prejuízo")
    return ResumoInvestimentosMes(aportes=aportes, resgates=resgates, rendimentos=rendimentos, prejuizos=prejuizos)


# ---------- Atualização de saldo ----------

@app.post("/atualizacoes-saldo", response_model=AtualizacaoSaldoOut)
def criar_atualizacao_saldo(a: AtualizacaoSaldoCreate, db: Session = Depends(get_db)):
    ativo = db.query(Ativo).filter(Ativo.id == a.ativo_id).first()
    if not ativo:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    ultima = (
        db.query(AtualizacaoSaldo)
        .filter(AtualizacaoSaldo.ativo_id == a.ativo_id)
        .order_by(AtualizacaoSaldo.data.desc(), AtualizacaoSaldo.id.desc())
        .first()
    )

    if ultima is None:
        nova = AtualizacaoSaldo(
            ativo_id=a.ativo_id, data=a.data, saldo_informado=a.saldo_informado,
            saldo_anterior=None, aportes_periodo=0, resgates_periodo=0,
            rendimento_liquido=None, rendimento_percentual=None,
        )
        db.add(nova)
        db.commit()
        db.refresh(nova)
        return nova

    movs = (
        db.query(MovimentacaoInvestimento)
        .filter(MovimentacaoInvestimento.ativo_id == a.ativo_id)
        .filter(MovimentacaoInvestimento.data > ultima.data)
        .filter(MovimentacaoInvestimento.data <= a.data)
        .filter(MovimentacaoInvestimento.automatica == False)
        .all()
    )
    aportes = sum(m.valor for m in movs if m.tipo == "Aporte")
    resgates = sum(m.valor for m in movs if m.tipo == "Resgate")

    rendimento = a.saldo_informado - ultima.saldo_informado - aportes + resgates
    percentual = (rendimento / ultima.saldo_informado * 100) if ultima.saldo_informado > 0 else None

    nova = AtualizacaoSaldo(
        ativo_id=a.ativo_id, data=a.data, saldo_informado=a.saldo_informado,
        saldo_anterior=ultima.saldo_informado, aportes_periodo=aportes, resgates_periodo=resgates,
        rendimento_liquido=rendimento, rendimento_percentual=percentual,
    )
    db.add(nova)
    db.flush()

    if rendimento > 0:
        db.add(MovimentacaoInvestimento(
            ativo_id=a.ativo_id, data=a.data, tipo="Rendimento",
            valor=abs(rendimento), observacao="Gerado por atualização de saldo", automatica=True,
        ))
    elif rendimento < 0:
        db.add(MovimentacaoInvestimento(
            ativo_id=a.ativo_id, data=a.data, tipo="Prejuízo",
            valor=abs(rendimento), observacao="Gerado por atualização de saldo", automatica=True,
        ))

    db.commit()
    db.refresh(nova)
    return nova


@app.get("/atualizacoes-saldo", response_model=List[AtualizacaoSaldoOut])
def listar_atualizacoes_saldo(ativo_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(AtualizacaoSaldo)
    if ativo_id is not None:
        q = q.filter(AtualizacaoSaldo.ativo_id == ativo_id)
    return q.order_by(AtualizacaoSaldo.data.desc()).all()


# ---------- Saldo acumulado ----------

@app.get("/saldo-acumulado/{ano}/{mes}", response_model=SaldoAcumulado)
def saldo_acumulado_ate(ano: int, mes: int, db: Session = Depends(get_db)):
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    limite = date(ano, mes, ultimo_dia)

    trans = db.query(Transacao).filter(Transacao.data <= limite).all()
    receitas = sum(t.valor for t in trans if t.valor > 0)
    despesas = sum(abs(t.valor) for t in trans if t.valor < 0)

    movs = db.query(MovimentacaoInvestimento).filter(MovimentacaoInvestimento.data <= limite).all()
    aportes = sum(m.valor for m in movs if m.tipo == "Aporte")
    resgates = sum(m.valor for m in movs if m.tipo == "Resgate")

    saldo = receitas - despesas
    return SaldoAcumulado(
        saldo=saldo, receitas=receitas, despesas=despesas,
        aportes=aportes, resgates=resgates,
    )


# ---------- Backup e Restauração ----------

@app.get("/backup")
def baixar_backup():
    if not os.path.exists(DB_FILE):
        raise HTTPException(status_code=404, detail="Banco de dados não encontrado")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.close()

    try:
        import sqlcipher3
        import keyring

        senha = keyring.get_password("meu_financeiro", "jamiro")
        if not senha:
            raise HTTPException(status_code=500, detail="Senha não encontrada no keyring")

        src = sqlcipher3.connect(DB_FILE)
        src.execute(f"PRAGMA key = '{senha}'")
        dst = sqlcipher3.connect(tmp.name)
        dst.execute(f"PRAGMA key = '{senha}'")
        with dst:
            src.backup(dst)
        src.close()
        dst.close()
    except HTTPException:
        os.unlink(tmp.name)
        raise
    except Exception as e:
        os.unlink(tmp.name)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar backup: {e}")

    nome = f"financeiro_{datetime.now().strftime('%Y-%m-%d_%H%M')}.db"
    return FileResponse(tmp.name, media_type="application/octet-stream", filename=nome)


@app.post("/restaurar")
async def restaurar_backup(arquivo: UploadFile = File(...)):
    conteudo = await arquivo.read()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    tmp.write(conteudo)
    tmp.close()

    try:
        import sqlcipher3
        import keyring

        senha = keyring.get_password("meu_financeiro", "jamiro")
        if not senha:
            raise HTTPException(status_code=500, detail="Senha não encontrada no keyring")

        con = sqlcipher3.connect(tmp.name)
        con.execute(f"PRAGMA key = '{senha}'")
        cur = con.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tabelas = {r[0] for r in cur.fetchall()}
        con.close()
    except HTTPException:
        os.unlink(tmp.name)
        raise
    except Exception as e:
        os.unlink(tmp.name)
        raise HTTPException(status_code=400, detail=f"Arquivo inválido: {e}")

    esperadas = {"transacoes", "ativos", "recorrentes"}
    if not esperadas.issubset(tabelas):
        os.unlink(tmp.name)
        raise HTTPException(status_code=400, detail="O arquivo não parece ser um banco válido do Meu Financeiro.")

    if os.path.exists(DB_FILE):
        backup_atual = DB_FILE.replace(".db", f"_antes_restauracao_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db")
        try:
            shutil.copy2(DB_FILE, backup_atual)
        except Exception as e:
            os.unlink(tmp.name)
            raise HTTPException(status_code=500, detail=f"Erro ao salvar cópia de segurança: {e}")

    engine.dispose()

    try:
        shutil.move(tmp.name, DB_FILE)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao substituir banco: {e}")

    return {"ok": True, "mensagem": "Banco restaurado. Feche esta aba e rode ./iniciar.sh novamente."}
