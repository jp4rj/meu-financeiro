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


class RecorrenteCreate(BaseModel):
    descricao: str
    valor: float
    categoria: str
    natureza: str
    dia_vencimento: int = 1


class RecorrenteUpdate(BaseModel):
    descricao: Optional[str] = None
    valor: Optional[float] = None
    categoria: Optional[str] = None
    natureza: Optional[str] = None
    dia_vencimento: Optional[int] = None
    ativa: Optional[bool] = None


class RecorrenteOut(BaseModel):
    id: int
    descricao: str
    valor: float
    categoria: str
    natureza: str
    dia_vencimento: int
    ativa: bool

    class Config:
        from_attributes = True


class ParcelamentoCreate(BaseModel):
    descricao: str
    valor_total: float
    categoria: str
    tipo: str = "Cartao"
    data_primeira_parcela: date
    num_parcelas: int


class AtivoCreate(BaseModel):
    nome: str
    categoria: str


class AtivoUpdate(BaseModel):
    nome: Optional[str] = None
    categoria: Optional[str] = None
    ativo: Optional[bool] = None


class AtivoOut(BaseModel):
    id: int
    nome: str
    categoria: str
    ativo: bool

    class Config:
        from_attributes = True


class AtivoComSaldo(AtivoOut):
    saldo: float


class MovimentacaoCreate(BaseModel):
    ativo_id: int
    data: date
    tipo: str
    valor: float
    observacao: Optional[str] = None


class MovimentacaoUpdate(BaseModel):
    data: Optional[date] = None
    tipo: Optional[str] = None
    valor: Optional[float] = None
    observacao: Optional[str] = None


class MovimentacaoOut(BaseModel):
    id: int
    ativo_id: int
    data: date
    tipo: str
    valor: float
    observacao: Optional[str] = None
    transacao_id: Optional[int] = None

    class Config:
        from_attributes = True


class ResumoInvestimentosMes(BaseModel):
    aportes: float
    resgates: float
    rendimentos: float
