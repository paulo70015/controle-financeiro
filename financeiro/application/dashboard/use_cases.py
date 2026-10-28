class DashboardUseCases:
    def __init__(self, repository):
        self.repository = repository

    def carregar_dados_ano(self, ano: int) -> dict:
        data = self.repository.get_dados_ano(ano)
        data["is_bloqueado"] = self.repository.is_ano_bloqueado(ano)
        return data

    def buscar_dados_ano(self, ano: int, termo: str) -> list[dict]:
        termo_limpo = (termo or "").strip()
        if not termo_limpo:
            return []
        return self.repository.buscar_no_ano(ano, termo_limpo)



