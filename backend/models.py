from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base


class Transacao(Base):
    __tablename__ = "transacoes"

    id = Column(Integer, primary_key=True, index=True)
    data = Column(Date, nullable=False)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)      # negativo = despesa
    categoria = Column(String, nullable=False)
    tipo = Column(String, nullable=False)      # Fixo / Cartao / Extra / Investimento
    recorrente = Column(Boolean, default=False)


class DespesaFixa(Base):
    __tablename__ = "despesas_fixas"

    id = Column(Integer, primary_key=True, index=True)
    descricao = Column(String, nullable=False)
    valor = Column(Float, nullable=False)      # armazenado como negativo
    categoria = Column(String, nullable=False)
    dia_vencimento = Column(Integer, nullable=False, default=1)
    ativa = Column(Boolean, default=True)


class FixaGerada(Base):
    """Marca quais despesas fixas já foram geradas em cada mês, para não duplicar."""
    __tablename__ = "fixas_geradas"

    id = Column(Integer, primary_key=True, index=True)
    despesa_fixa_id = Column(Integer, ForeignKey("despesas_fixas.id"), nullable=False)
    ano = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
