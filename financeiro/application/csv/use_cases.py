class CSVUseCases:
    def __init__(self, repository):
        self.repository = repository

    def importar(self, file_storage):
        if file_storage is None:
            return ({"erro": "Nenhum arquivo enviado"}, 400)
        return self.repository.importar_csv(file_storage)

    def desfazer_importacao(self):
        return self.repository.desfazer_importacao()

    def exportar(self, ano: int):
        return self.repository.exportar_csv(ano)
