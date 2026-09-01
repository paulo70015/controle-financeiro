"""Validacoes numericas compartilhadas (regras puras de dominio)."""

import math


def parse_valor_finito(valor, campo: str = "valor") -> float:
    """Converte `valor` para float rejeitando NaN/Inf (BUG-7).

    Levanta ValueError com mensagem em PT-BR quando a conversao falha ou o
    resultado nao e um numero finito. Usado pelos use cases de despesas,
    rendimentos e contas para impedir que NaN/Inf cheguem ao banco
    (NaN viraria NULL no SQLite e corromperia agregados).
    """
    try:
        numero = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"{campo} deve ser um número válido")
    if not math.isfinite(numero):
        raise ValueError(f"{campo} deve ser um número finito")
    return numero
