class AdminUseCases:
    def __init__(self, repository):
        self.repository = repository

    def salvar_config(self, payload: dict) -> None:
        self.repository.save_config(payload)

    def duplicar_ano(self, payload: dict) -> tuple[bool, str]:
        ano_origem = payload.get("ano_origem")
        ano_destino = payload.get("ano_destino")
        if not ano_origem or not ano_destino:
            return (False, "ano_origem e ano_destino obrigatorios")
        if ano_origem == ano_destino:
            return (False, "Anos devem ser diferentes")
        if self.repository.year_has_data(int(ano_destino)):
            return (False, f"O ano {ano_destino} já possui dados")
        self.repository.duplicate_year(ano_origem=ano_origem, ano_destino=ano_destino)
        return (True, "")

    def remover_ano(self, ano: int) -> None:
        self.repository.delete_year(ano)
