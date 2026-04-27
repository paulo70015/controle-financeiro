"""
Repositório de Categorias - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client
from financeiro.domain.categorias.entities import Categoria


class SupabaseCategoriasRepository:
    def __init__(self, client_factory):
        """
        Args:
            client_factory: Função que retorna instância do Supabase Client
        """
        self.client_factory = client_factory

    def add_categoria(self, categoria: Categoria) -> None:
        """Adiciona nova categoria com ordem sequencial"""
        client: Client = self.client_factory()
        
        # Obter última ordem
        response = client.table("categorias") \
            .select("ordem") \
            .eq("ano", categoria.ano) \
            .order("ordem", desc=True) \
            .limit(1) \
            .execute()
        
        ultima_ordem = response.data[0]["ordem"] if response.data else 0
        
        # Inserir categoria
        # Converter boolean para INTEGER (0/1)
        inclui_fixas_int = 1 if categoria.inclui_fixas else 0
        client.table("categorias").insert({
            "nome": categoria.nome,
            "ordem": ultima_ordem + 1,
            "inclui_fixas": inclui_fixas_int,
            "conta_vinculada_id": categoria.conta_vinculada_id,
            "ano": categoria.ano
        }).execute()

    def update_categoria(self, categoria_id: int, payload: dict) -> bool:
        """Atualiza categoria e propaga mudança de nome para despesas/status"""
        client: Client = self.client_factory()
        
        # Buscar categoria atual
        response = client.table("categorias") \
            .select("nome, ano") \
            .eq("id", categoria_id) \
            .execute()
        
        if not response.data:
            return False
        
        categoria_atual = response.data[0]
        nome_antigo = categoria_atual["nome"]
        ano = categoria_atual["ano"]
        
        # Preparar dados de atualização
        updates = {}
        
        # Atualizar nome (e propagar)
        novo_nome = payload.get("nome", "").strip()
        if novo_nome and novo_nome != nome_antigo:
            updates["nome"] = novo_nome
            
            # Propagar mudança de nome para despesas
            client.table("despesas") \
                .update({"categoria": novo_nome}) \
                .eq("categoria", nome_antigo) \
                .eq("ano", ano) \
                .execute()
            
            # Propagar mudança de nome para pagamento_status
            client.table("pagamento_status") \
                .update({"categoria": novo_nome}) \
                .eq("categoria", nome_antigo) \
                .eq("ano", ano) \
                .execute()
        
        # Atualizar inclui_fixas (converter boolean para INTEGER)
        if "inclui_fixas" in payload:
            updates["inclui_fixas"] = 1 if payload["inclui_fixas"] else 0
        
        # Atualizar tooltip
        if "tooltip" in payload:
            updates["tooltip"] = payload["tooltip"]
        
        # Atualizar conta_vinculada_id
        if "conta_vinculada_id" in payload:
            updates["conta_vinculada_id"] = payload["conta_vinculada_id"] or None
        
        # Executar atualização
        if updates:
            client.table("categorias") \
                .update(updates) \
                .eq("id", categoria_id) \
                .execute()
        
        return True

    def delete_categoria(self, categoria_id: int) -> None:
        """Deleta categoria e limpa dependências (despesas, fixas, depósitos)"""
        client: Client = self.client_factory()
        
        # Buscar categoria
        response = client.table("categorias") \
            .select("nome, ano") \
            .eq("id", categoria_id) \
            .execute()
        
        if not response.data:
            return
        
        nome = response.data[0]["nome"]
        ano = response.data[0]["ano"]
        
        # Buscar IDs de despesas para limpar depósitos vinculados
        despesas_response = client.table("despesas") \
            .select("id") \
            .eq("categoria", nome) \
            .eq("ano", ano) \
            .execute()
        
        ids_despesas = [d["id"] for d in despesas_response.data]
        
        # Deletar depósitos vinculados às despesas
        if ids_despesas:
            client.table("depositos_conta") \
                .delete() \
                .in_("despesa_id", ids_despesas) \
                .execute()
        
        # Deletar despesas da categoria
        client.table("despesas") \
            .delete() \
            .eq("categoria", nome) \
            .eq("ano", ano) \
            .execute()
        
        # Desvincular fixas (não deletar, apenas setar cat_id=NULL)
        client.table("despesas_fixas_cartao") \
            .update({"cat_id": None}) \
            .eq("cat_id", categoria_id) \
            .eq("ano", ano) \
            .execute()
        
        # Deletar categoria
        client.table("categorias") \
            .delete() \
            .eq("id", categoria_id) \
            .execute()

    def move_categoria(self, categoria_id: int, direcao: str) -> bool:
        """Move categoria para cima ou para baixo (swap de ordem)"""
        client: Client = self.client_factory()
        
        # Buscar ano da categoria
        response = client.table("categorias") \
            .select("ano") \
            .eq("id", categoria_id) \
            .execute()
        
        if not response.data:
            return False
        
        ano = response.data[0]["ano"]
        
        # Buscar todas as categorias do ano ordenadas
        categorias_response = client.table("categorias") \
            .select("id, ordem") \
            .eq("ano", ano) \
            .order("ordem") \
            .execute()
        
        categorias = categorias_response.data
        ids = [c["id"] for c in categorias]
        ordens = [c["ordem"] for c in categorias]
        
        if categoria_id not in ids:
            return False
        
        idx = ids.index(categoria_id)
        swap = idx - 1 if direcao == "cima" else idx + 1
        
        # Validar limites
        if not (0 <= swap < len(ids)):
            return False
        
        # Swap de ordens
        client.table("categorias") \
            .update({"ordem": ordens[swap]}) \
            .eq("id", ids[idx]) \
            .execute()
        
        client.table("categorias") \
            .update({"ordem": ordens[idx]}) \
            .eq("id", ids[swap]) \
            .execute()
        
        return True

    def reorder_categorias(self, ordem_ids: list[int]) -> None:
        """Reordena categorias conforme lista de IDs"""
        client: Client = self.client_factory()
        
        for i, categoria_id in enumerate(ordem_ids):
            client.table("categorias") \
                .update({"ordem": i}) \
                .eq("id", categoria_id) \
                .execute()

    def get_conta_vinculada(self, categoria: str, ano: int) -> int | None:
        """Retorna o ID da conta vinculada à categoria, ou None"""
        client: Client = self.client_factory()
        
        response = client.table("categorias") \
            .select("conta_vinculada_id") \
            .eq("nome", categoria) \
            .eq("ano", ano) \
            .execute()
        
        if not response.data:
            return None
        
        conta_id = response.data[0].get("conta_vinculada_id")
        return conta_id if conta_id else None
