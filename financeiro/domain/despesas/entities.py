from dataclasses import dataclass


@dataclass(frozen=True)
class Despesa:
    ano: int
    mes: int
    categoria: str
    valor: float
    nota: str = ""
    ignorar_total: bool = False


@dataclass(frozen=True)
class DespesaLote:
    ano: int
    categoria: str
    valor_base: float
    acrescimo: float = 0.0
    nota: str = ""
    ignorar_total: bool = False
