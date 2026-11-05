from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey
from .database import Base


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    categoria = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    recorrente = Column(Boolean, default=False)


class Recorrente(Base):
    __tablename__ = "recorrentes"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    categoria = Column(String, nullable=False)
    natureza = Column(String, nullable=False)
    dia_vencimento = Column(Integer, nullable=False, default=1)
    ativa = Column(Boolean, default=True)


class RecorrenteGerada(Base):
    __tablename__ = "recorrentes_geradas"

    id = Column(Integer, primary_key=True, index=True)
    recorrente_id = Column(Integer, ForeignKey("recorrentes.id"), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)


class Ativo(Base):
    __tablename__ = "ativos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    ativo = Column(Boolean, default=True)


class MovimentacaoInvestimento(Base):
    __tablename__ = "movimentacoes_investimento"

    id = Column(Integer, primary_key=True, index=True)
    ativo_id = Column(Integer, ForeignKey("ativos.id"), nullable=False)
    data = Column(Date, nullable=False)
    tipo = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    observacao = Column(String, nullable=True)
    transacao_id = Column(Integer, ForeignKey("transacoes.id"), nullable=True)
