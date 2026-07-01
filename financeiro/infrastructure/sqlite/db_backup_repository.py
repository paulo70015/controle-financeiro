import os
import shutil
import logging

from financeiro.infrastructure.export_files import nome_arquivo_exportacao


class SQLiteDBBackupRepository:
    def __init__(self, connection_factory):
        self.connection_factory = connection_factory
        from financeiro.infrastructure.runtime.paths import get_data_dir
        self.db_path = os.path.join(get_data_dir(), "financeiro.db")
        self.bak_path = os.path.join(get_data_dir(), "financeiro.db.bak")

    def exportar_txt(self):
        """Exporta o banco SQLite como arquivo binário (.db)."""
        if not os.path.exists(self.db_path):
            return ({"erro": "Banco de dados nao encontrado."}, 404)

        try:
            with open(self.db_path, "rb") as f:
                conteudo = f.read()
        except OSError as e:
            return ({"erro": f"Falha ao ler banco: {str(e)}"}, 500)

        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f"attachment; filename={nome_arquivo_exportacao('controle-financeiro-bd', 'db')}",
        }
        return (conteudo, 200, headers)

    def importar_txt(self, file_storage):
        """Importa um banco SQLite, substituindo o atual com backup de segurança."""
        if file_storage is None:
            return ({"erro": "Nenhum arquivo enviado."}, 400)

        conteudo = file_storage.read()
        if not conteudo:
            return ({"erro": "Arquivo vazio."}, 400)

        # Validação mínima: tenta abrir como SQLite
        import sqlite3
        try:
            conn_tmp = sqlite3.connect(":memory:")
            conn_tmp.executescript("BEGIN; ROLLBACK;")  # só pra confirmar que é SQLite-style
            conn_tmp.close()
        except Exception:
            pass
        # Valida escrevendo em disco temporário e tentando abrir
        tmp_path = self.db_path + ".tmp_import"
        try:
            with open(tmp_path, "wb") as f:
                f.write(conteudo)
            test_conn = sqlite3.connect(f"file:{tmp_path}?mode=ro", uri=True)
            test_conn.execute("SELECT 1")
            test_conn.close()
        except Exception as e:
            # Garante que a conexão de teste foi fechada
            try:
                test_conn.close()
            except Exception:
                pass
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except PermissionError:
                pass  # Windows pode manter o lock por alguns ms
            return ({"erro": f"Arquivo invalido ou corrompido: {str(e)}"}, 400)

        # Backup de segurança do banco atual
        try:
            if os.path.exists(self.db_path):
                shutil.copy2(self.db_path, self.bak_path)
        except OSError as e:
            os.remove(tmp_path)
            return ({"erro": f"Falha ao criar backup de seguranca: {str(e)}"}, 500)

        # Substitui o banco
        try:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            shutil.move(tmp_path, self.db_path)
        except OSError as e:
            # Tenta restaurar backup
            if os.path.exists(self.bak_path):
                shutil.copy2(self.bak_path, self.db_path)
            return ({"erro": f"Falha ao substituir banco: {str(e)}"}, 500)

        # Fecha todas as conexões abertas antes de retornar
        try:
            conn = self.connection_factory()
            conn.close()
        except Exception:
            pass

        logging.info("Banco SQLite importado com sucesso. Backup anterior em %s", self.bak_path)
        return ({"ok": True, "importados": {"banco": "substituido"}, "bak_disponivel": os.path.exists(self.bak_path)}, 200)
