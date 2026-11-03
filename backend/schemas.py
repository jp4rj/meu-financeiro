from pydantic import BaseModel
from datetime import date
from typing import Optional


class TransacaoCreate(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str
    tipo: str
    recorrente: bool = False


class TransacaoUpdate(BaseModel):
    data: Optional[date] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    categoria: Optional[str] = None
    tipo: Optional[str] = None
    recorrente: Optional[bool] = None


class TransacaoOut(TransacaoCreate):
    id: int

    class Config:
        from_attributes = True


class DespesaFixaCreate(BaseModel):
    descricao: str
    valor: float                      # envie positivo; o backend torna negativo
    categoria: str
    dia_vencimento: int = 1


class DespesaFixaUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    categoria: Optional[str] = None
    dia_vencimento: Optional[int] = None
    ativa: Optional[bool] = None


class DespesaFixaOut(BaseModel):
    id: int
    descricao: str
    valor: float
    categoria: str
    dia_vencimento: int
    ativa: bool

    class Config:
        from_attributes = True


class ParcelamentoCreate(BaseModel):
    descricao: str
    valor_total: float                # envie positivo; o backend divide e torna negativo
    categoria: str
    tipo: str = "Cartao"
    data_primeira_parcela: date
    num_parcelas: int
