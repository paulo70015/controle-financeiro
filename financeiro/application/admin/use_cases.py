class AdminUseCases:
    def __init__(self, repository):
        self.repository = repository

    def salvar_config(self, payload: dict) -> None:
        self.repository.save_config(payload)

    def duplicar_ano(self, payload: dict) -> tuple[bool, str]:
        ano_origem_raw = payload.get("ano_origem")
        ano_destino_raw = payload.get("ano_destino")
        if not ano_origem_raw or not ano_destino_raw:
            return (False, "ano_origem e ano_destino obrigatorios")
        try:
            ano_origem = int(ano_origem_raw)
            ano_destino = int(ano_destino_raw)
        except (ValueError, TypeError):
            return (False, "ano_origem e ano_destino devem ser números inteiros")
        if ano_origem == ano_destino:
            return (False, "Anos devem ser diferentes")
        if self.repository.year_has_data(ano_destino):
            return (False, f"O ano {ano_destino} já possui dados")
        self.repository.duplicate_year(ano_origem=ano_origem, ano_destino=ano_destino)
        return (True, "")

    def criar_ano(self, ano: int) -> None:
        """Registra um ano na tabela `anos` sem duplicar dados."""
        self.repository.create_year(ano)

    def remover_ano(self, ano: int) -> None:
        self.repository.delete_year(ano)
