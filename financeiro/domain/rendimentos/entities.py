from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RendimentoLocal:
    ano: int
    nome: str
    conta_vinculada_id: Optional[int] = None


@dataclass(frozen=True)
class RendimentoLancamento:
    ano: int
    mes: int
    local_id: int
    tipo: str
    valor: float
    nota: str = ""
