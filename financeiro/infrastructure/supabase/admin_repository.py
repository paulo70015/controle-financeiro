"""
Repositório de Admin - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client


class SupabaseAdminRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def save_config(self, payload: dict) -> None:
        """Salva configurações (upsert)"""
        client: Client = self.client_factory()
        
        for chave, valor in payload.items():
            client.table("config").upsert({
                "chave": chave,
                "valor": str(valor)
            }, on_conflict="chave").execute()

    def duplicate_year(self, ano_origem: int, ano_destino: int) -> None:
        """Duplica todos os dados de um ano para outro"""
        client: Client = self.client_factory()

        # Garantir que o ano de destino existe na tabela `anos`
        client.table("anos").upsert({"ano": ano_destino}).execute()

        # Duplicar categorias e mapear IDs
        cat_map = {}
        cats_response = client.table("categorias") \
            .select("*") \
            .eq("ano", ano_origem) \
            .execute()
        
        for c in cats_response.data:
            new_cat_response = client.table("categorias").insert({
                "nome": c["nome"],
                "ordem": c["ordem"],
                "inclui_fixas": c["inclui_fixas"],
                "conta_vinculada_id": c["conta_vinculada_id"],
                "tooltip": c["tooltip"],
                "ano": ano_destino
            }).execute()
            cat_map[c["id"]] = new_cat_response.data[0]["id"]
        
        # Duplicar fixas (remapear cat_id)
        fixas_response = client.table("despesas_fixas_cartao") \
            .select("*") \
            .eq("ano", ano_origem) \
            .execute()
        
        fixas_insert = []
        for f in fixas_response.data:
            new_cat_id = cat_map.get(f["cat_id"]) if f["cat_id"] else None
            fixas_insert.append({
                "descricao": f["descricao"],
                "valor": f["valor"],
                "dia": f["dia"],
                "cat_id": new_cat_id,
                "ativa": f["ativa"],
                "ano": ano_destino
            })
        
        if fixas_insert:
            client.table("despesas_fixas_cartao").insert(fixas_insert).execute()
        
        # Duplicar despesas (e depósitos vinculados)
        desp_response = client.table("despesas") \
            .select("mes, categoria, valor, nota") \
            .eq("ano", ano_origem) \
            .execute()
        
        for r in desp_response.data:
            # Inserir despesa
            desp_insert_response = client.table("despesas").insert({
                "ano": ano_destino,
                "mes": r["mes"],
                "categoria": r["categoria"],
                "valor": r["valor"],
                "nota": r["nota"]
            }).execute()
            
            despesa_id = desp_insert_response.data[0]["id"]
            
            # Verificar se categoria tem conta vinculada
            cat_response = client.table("categorias") \
                .select("conta_vinculada_id") \
                .eq("nome", r["categoria"]) \
                .eq("ano", ano_destino) \
                .execute()
            
            if cat_response.data and cat_response.data[0]["conta_vinculada_id"]:
                client.table("depositos_conta").insert({
                    "ano": ano_destino,
                    "mes": r["mes"],
                    "conta_id": cat_response.data[0]["conta_vinculada_id"],
                    "valor": -r["valor"],
                    "nota": r["nota"],
                    "despesa_id": despesa_id
                }).execute()
        
        # Duplicar receitas
        rec_response = client.table("receitas") \
            .select("mes, descricao, valor, nota") \
            .eq("ano", ano_origem) \
            .execute()
        
        receitas_insert = [{
            "ano": ano_destino,
            "mes": r["mes"],
            "descricao": r["descricao"],
            "valor": r["valor"],
            "nota": r["nota"]
        } for r in rec_response.data]
        
        if receitas_insert:
            client.table("receitas").insert(receitas_insert).execute()
        
        # Duplicar rendimentos - locais
        rend_locais_map = {}
        rend_locais_response = client.table("rendimentos_locais") \
            .select("id, nome, ordem, conta_vinculada_id") \
            .eq("ano", ano_origem) \
            .execute()
        
        for rl in rend_locais_response.data:
            new_local_response = client.table("rendimentos_locais").insert({
                "ano": ano_destino,
                "nome": rl["nome"],
                "ordem": rl["ordem"],
                "conta_vinculada_id": rl.get("conta_vinculada_id"),
            }).execute()
            rend_locais_map[rl["id"]] = new_local_response.data[0]["id"]
        
        # Duplicar rendimentos - lançamentos
        rend_lanc_response = client.table("rendimentos_lancamentos") \
            .select("mes, local_id, tipo, valor, nota") \
            .eq("ano", ano_origem) \
            .execute()
        
        rend_lanc_insert = []
        for rl in rend_lanc_response.data:
            novo_local_id = rend_locais_map.get(rl["local_id"])
            if not novo_local_id:
                continue
            rend_lanc_insert.append({
                "ano": ano_destino,
                "mes": rl["mes"],
                "local_id": novo_local_id,
                "tipo": rl["tipo"],
                "valor": rl["valor"],
                "nota": rl["nota"]
            })
        
        if rend_lanc_insert:
            client.table("rendimentos_lancamentos").insert(rend_lanc_insert).execute()

    def create_year(self, ano: int) -> None:
        """Registra um ano na tabela `anos` sem duplicar dados."""
        client: Client = self.client_factory()
        client.table("anos").upsert({"ano": ano}).execute()

    def year_has_data(self, ano: int) -> bool:
        """Verifica se um ano tem dados — fonte única: tabela `anos`."""
        client: Client = self.client_factory()
        response = client.table("anos").select("ano").eq("ano", ano).limit(1).execute()
        return len(response.data) > 0

    def delete_year(self, ano: int) -> None:
        """Remove o ano e TODOS os dados vinculados via ON DELETE CASCADE."""
        client: Client = self.client_factory()
        client.table("anos").delete().eq("ano", ano).execute()
