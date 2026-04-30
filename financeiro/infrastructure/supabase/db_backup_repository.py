import json
from datetime import datetime, timezone

from financeiro.infrastructure.export_files import nome_arquivo_exportacao
from financeiro.infrastructure.supabase.client import Client


TABLES = [
    {
        "name": "config",
        "pk": "chave",
        "columns": ["chave", "valor"],
        "delete_field": "chave",
    },
    {
        "name": "contas_correntes",
        "pk": "id",
        "columns": ["id", "nome", "ordem", "saldo_inicial"],
    },
    {
        "name": "categorias",
        "pk": "id",
        "columns": ["id", "nome", "ordem", "inclui_fixas", "conta_vinculada_id", "tooltip", "ano"],
        "refs": {"conta_vinculada_id": "contas_correntes"},
    },
    {
        "name": "despesas",
        "pk": "id",
        "columns": ["id", "ano", "mes", "categoria", "valor", "nota", "data_alteracao", "ignorar_total"],
    },
    {
        "name": "receitas",
        "pk": "id",
        "columns": ["id", "ano", "mes", "descricao", "valor", "nota", "data_alteracao", "status"],
    },
    {
        "name": "despesas_fixas_cartao",
        "pk": "id",
        "columns": ["id", "descricao", "valor", "dia", "ativa", "cat_id", "ano"],
        "refs": {"cat_id": "categorias"},
    },
    {
        "name": "fixas_excecoes",
        "pk": "id",
        "columns": ["id", "ano", "mes", "cat_id"],
        "refs": {"cat_id": "categorias"},
    },
    {
        "name": "fixas_aplicadas_manual",
        "pk": "id",
        "columns": ["id", "ano", "mes", "fixa_id", "data_aplicacao"],
        "refs": {"fixa_id": "despesas_fixas_cartao"},
    },
    {
        "name": "pagamento_status",
        "pk": "id",
        "columns": ["id", "ano", "mes", "categoria", "status"],
    },
    {
        "name": "metas",
        "pk": "id",
        "columns": ["id", "descricao", "valor", "ano_meta", "concluida", "ano_criacao"],
    },
    {
        "name": "depositos_conta",
        "pk": "id",
        "columns": ["id", "ano", "mes", "conta_id", "valor", "nota", "despesa_id"],
        "refs": {"conta_id": "contas_correntes", "despesa_id": "despesas"},
    },
    {
        "name": "movimentacoes_mensais",
        "pk": "id",
        "columns": ["id", "ano", "mes", "conta_id", "valor", "nota"],
        "refs": {"conta_id": "contas_correntes"},
    },
    {
        "name": "rendimentos_locais",
        "pk": "id",
        "columns": ["id", "ano", "nome", "ordem", "projecao_taxa"],
    },
    {
        "name": "rendimentos_lancamentos",
        "pk": "id",
        "columns": ["id", "ano", "mes", "local_id", "tipo", "valor", "nota", "data_alteracao"],
        "refs": {"local_id": "rendimentos_locais"},
    },
]


class SupabaseDBBackupRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def exportar_txt(self):
        client: Client = self.client_factory()
        data = {
            "tipo": "controle_financeiro_supabase_dump",
            "versao": 1,
            "gerado_em": datetime.now(timezone.utc).isoformat(),
            "tabelas": {},
        }

        for table in TABLES:
            data["tabelas"][table["name"]] = self._select_all(client, table)

        payload = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        headers = {
            "Content-Type": "text/plain; charset=utf-8",
            "Content-Disposition": f"attachment; filename={nome_arquivo_exportacao('controle-financeiro-bd', 'txt')}",
        }
        return (payload, 200, headers)

    def importar_txt(self, file_storage):
        client: Client = self.client_factory()
        try:
            dump = json.loads(file_storage.read().decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return ({"erro": "Arquivo TXT invalido. Exporte novamente pelo menu BD."}, 400)

        if dump.get("tipo") != "controle_financeiro_supabase_dump":
            return ({"erro": "Arquivo TXT nao pertence ao backup do banco do Controle Financeiro."}, 400)

        tabelas = dump.get("tabelas")
        if not isinstance(tabelas, dict):
            return ({"erro": "Arquivo TXT sem bloco de tabelas valido."}, 400)

        try:
            self._limpar_tabelas(client)
            id_maps = {}
            importados = {}
            for table in TABLES:
                rows = tabelas.get(table["name"], [])
                id_maps[table["name"]] = {}
                importados[table["name"]] = self._insert_rows(client, table, rows, id_maps)
        except Exception as exc:
            return ({"erro": f"Falha ao importar banco: {str(exc)}"}, 500)

        return ({"ok": True, "importados": importados}, 200)

    def _select_all(self, client: Client, table: dict) -> list[dict]:
        rows = []
        start = 0
        page_size = 1000
        columns = ",".join(table["columns"])
        while True:
            response = (
                client.table(table["name"])
                .select(columns)
                .order(table["pk"])
                .range(start, start + page_size - 1)
                .execute()
            )
            batch = response.data or []
            rows.extend(batch)
            if len(batch) < page_size:
                return rows
            start += page_size

    def _limpar_tabelas(self, client: Client) -> None:
        for table in reversed(TABLES):
            delete_field = table.get("delete_field", "id")
            if delete_field == "id":
                client.table(table["name"]).delete().neq(delete_field, -1).execute()
            else:
                client.table(table["name"]).delete().neq(delete_field, "__controle_financeiro_nunca__").execute()

    def _insert_rows(self, client: Client, table: dict, rows: list[dict], id_maps: dict) -> int:
        if not rows:
            return 0

        insert_rows = []
        old_ids = []
        pk = table["pk"]
        for row in rows:
            if not isinstance(row, dict):
                continue
            old_ids.append(row.get(pk))
            prepared = {
                column: row.get(column)
                for column in table["columns"]
                if (pk != "id" or column != pk) and column in row
            }
            self._remap_refs(prepared, table.get("refs", {}), id_maps)
            insert_rows.append(prepared)

        if not insert_rows:
            return 0

        for start in range(0, len(insert_rows), 500):
            chunk = insert_rows[start:start + 500]
            chunk_old_ids = old_ids[start:start + 500]
            response = client.table(table["name"]).insert(chunk).execute()
            inserted_rows = response.data or []

            if len(inserted_rows) == len(chunk_old_ids):
                for old_id, new_row in zip(chunk_old_ids, inserted_rows):
                    if old_id is not None and pk in new_row:
                        id_maps[table["name"]][old_id] = new_row[pk]

        return len(insert_rows)

    def _remap_refs(self, row: dict, refs: dict, id_maps: dict) -> None:
        for column, target_table in refs.items():
            old_value = row.get(column)
            if old_value is None:
                continue
            row[column] = id_maps.get(target_table, {}).get(old_value, old_value)
