import glob
import io
import json
import os
import threading
from typing import Optional


class DriveSyncService:
    def __init__(self, db_path: str, base_dir: str, drive_file_id: Optional[str]):
        self.db_path = db_path
        self.base_dir = base_dir
        self.drive_file_id = drive_file_id

    def _encontrar_credentials(self):
        def _is_valid_sa_file(path):
            try:
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                return data.get("type") == "service_account" and "client_email" in data
            except Exception:
                return False

        preferred_path = os.path.join(self.base_dir, "service_account.json")
        if os.path.exists(preferred_path) and _is_valid_sa_file(preferred_path):
            return preferred_path

        for path in glob.glob(os.path.join(self.base_dir, "*.json")):
            if path != preferred_path and _is_valid_sa_file(path):
                return path

        return None

    def _drive_ativo(self):
        return bool(self.drive_file_id) and self._encontrar_credentials() is not None

    def _drive_service(self):
        from googleapiclient.discovery import build
        from google.oauth2 import service_account

        creds_path = self._encontrar_credentials()
        creds = service_account.Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def baixar_db(self):
        if not self._drive_ativo():
            return
        temp_db = self.db_path + ".tmp"
        try:
            from googleapiclient.http import MediaIoBaseDownload

            service = self._drive_service()
            req = service.files().get_media(fileId=self.drive_file_id)
            with io.FileIO(temp_db, "wb") as fh:
                dl = MediaIoBaseDownload(fh, req)
                done = False
                while not done:
                    _, done = dl.next_chunk()
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
            os.rename(temp_db, self.db_path)
        except Exception as e:
            print(f"\n[AVISO] Falha ao baixar do Google Drive: {e}")
            print("Iniciando com a versao local existente do banco de dados (se houver).\n")
            if os.path.exists(temp_db):
                os.remove(temp_db)

    def subir_db(self):
        if not self._drive_ativo() or not os.path.exists(self.db_path):
            return
        try:
            from googleapiclient.http import MediaFileUpload

            service = self._drive_service()
            media = MediaFileUpload(self.db_path, mimetype="application/octet-stream", resumable=False)
            service.files().update(fileId=self.drive_file_id, media_body=media).execute()
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"\n[AVISO] Falha ao enviar para o Google Drive: {e}\n")

    def subir_db_async(self):
        t = threading.Thread(target=self.subir_db, daemon=True)
        t.start()
