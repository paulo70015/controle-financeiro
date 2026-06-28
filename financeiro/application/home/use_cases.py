import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class HomeUseCases:
    def __init__(self, repository):
        self.repository = repository

    def listar_anos(self, ano_atual=None):
        anos = self.repository.get_anos()
        if not anos:
            anos.add(datetime.now().year)
        if ano_atual:
            anos.add(ano_atual)
        return sorted(anos, reverse=True)

    def garantir_ano_existe(self, ano: int) -> None:
        """Persiste o ano na tabela `anos` se ainda não existir (best-effort)."""
        try:
            self.repository.ensure_year_exists(ano)
        except Exception as e:
            logger.warning("Falha ao garantir ano %s: %s", ano, e)

