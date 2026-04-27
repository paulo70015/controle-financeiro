from dataclasses import dataclass


@dataclass(frozen=True)
class Receita:
    ano: int
    mes: int
    descricao: str
    valor: float
    nota: str = ""


@dataclass(frozen=True)
class ReceitaLote:
    ano: int
    descricao: str
    valor_base: float
    acrescimo: float = 0.0
    nota: str = ""

