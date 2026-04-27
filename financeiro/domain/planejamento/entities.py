from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Fixa:
    descricao: str
    valor: float
    ano: int
    dia: int = 0
    cat_id: Optional[int] = None
    ativa: int = 1


@dataclass(frozen=True)
class Meta:
    descricao: str
    valor: float
    ano_criacao: int
    ano_meta: Optional[int] = None
    concluida: int = 0


@dataclass(frozen=True)
class PagamentoStatus:
    ano: int
    mes: int
    categoria: str
    status: int

