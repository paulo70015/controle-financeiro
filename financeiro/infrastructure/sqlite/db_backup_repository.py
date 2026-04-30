class SQLiteDBBackupRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory

    def exportar_txt(self):
        return ({"erro": "Exportacao de BD TXT disponivel apenas no modo Supabase."}, 400)

    def importar_txt(self, file_storage):
        return ({"erro": "Importacao de BD TXT disponivel apenas no modo Supabase."}, 400)
