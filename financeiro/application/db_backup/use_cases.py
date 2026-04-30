class DBBackupUseCases:
    def __init__(self, repository):
        self.repository = repository

    def exportar(self):
        return self.repository.exportar_txt()

    def importar(self, file_storage):
        if file_storage is None:
            return ({"erro": "Nenhum arquivo enviado"}, 400)
        return self.repository.importar_txt(file_storage)
