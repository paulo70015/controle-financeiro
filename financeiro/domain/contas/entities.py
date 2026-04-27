from dataclasses import dataclass


@dataclass(frozen=True)
class Conta:
    nome: str
    saldo_inicial: float = 0.0


@dataclass(frozen=True)
class DepositoConta:
    ano: int
    mes: int
    conta_id: int
    valor: float
    nota: str = ""


@dataclass(frozen=True)
class MovimentacaoMensal:
    ano: int
    mes: int
    conta_id: int
    valor: float
    nota: str = ""

