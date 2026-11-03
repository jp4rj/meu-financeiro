from sqlalchemy import Column, Integer, String, Float, Date, Boolean
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
