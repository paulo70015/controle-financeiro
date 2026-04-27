from dataclasses import dataclass


@dataclass(frozen=True)
class RendimentoLocal:
    ano: int
    nome: str


@dataclass(frozen=True)
class RendimentoLancamento:
    ano: int
    mes: int
    local_id: int
    tipo: str
    valor: float
    nota: str = ""
