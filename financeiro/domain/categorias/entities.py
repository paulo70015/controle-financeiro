from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Categoria:
    ano: int
    nome: str
    inclui_fixas: int = 0
    conta_vinculada_id: Optional[int] = None
