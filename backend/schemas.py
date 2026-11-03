from pydantic import BaseModel
from datetime import date

class TransacaoCreate(BaseModel):
    data: date
    descricao: str
    valor: float
    categoria: str
    tipo: str
    recorrente: bool = False

class TransacaoOut(TransacaoCreate):
    id: int
    class Config:
        from_attributes = True
