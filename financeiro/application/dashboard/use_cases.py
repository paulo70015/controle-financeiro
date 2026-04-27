class DashboardUseCases:
    def __init__(self, repository):
        self.repository = repository

    def carregar_dados_ano(self, ano: int) -> dict:
        data = self.repository.get_dados_ano(ano)
        data["is_bloqueado"] = self.repository.is_ano_bloqueado(ano)
        return data


