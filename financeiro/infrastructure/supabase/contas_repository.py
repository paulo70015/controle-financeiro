"""
Repositório de Contas Correntes - Supabase
Migrado de SQLite para PostgreSQL via Supabase
"""

from financeiro.infrastructure.supabase.client import Client
from financeiro.domain.contas.entities import Conta, DepositoConta, MovimentacaoMensal


class SupabaseContasRepository:
    def __init__(self, client_factory):
        self.client_factory = client_factory

    def add_conta(self, conta: Conta) -> None:
        """Adiciona conta com ordem sequencial"""
        client: Client = self.client_factory()
        
        # Obter última ordem
        response = client.table("contas_correntes") \
            .select("ordem") \
            .order("ordem", desc=True) \
            .limit(1) \
            .execute()
        
        ordem = response.data[0]["ordem"] if response.data else 0
        
        # Inserir conta (ON CONFLICT DO NOTHING via upsert)
        try:
            client.table("contas_correntes").insert({
                "nome": conta.nome,
                "ordem": ordem + 1,
                "saldo_inicial": conta.saldo_inicial
            }).execute()
        except Exception:
            # Ignorar se já existe (equivalente a INSERT OR IGNORE)
            pass

    def update_conta(self, conta_id: int, payload: dict) -> None:
        """Atualiza dados da conta"""
        client: Client = self.client_factory()
        
        updates = {}
        
        if "saldo_inicial" in payload:
            updates["saldo_inicial"] = float(payload["saldo_inicial"])
        
        if "nome" in payload and payload["nome"].strip():
            updates["nome"] = payload["nome"].strip()
        
        if updates:
            client.table("contas_correntes") \
                .update(updates) \
                .eq("id", conta_id) \
                .execute()

    def ano_existe(self, ano: int) -> bool:
        """Verifica se o ano existe na tabela `anos` (fonte da verdade)."""
        client: Client = self.client_factory()
        resp = client.table("anos").select("ano").eq("ano", ano).limit(1).execute()
        return bool(resp.data)

    def delete_conta(self, conta_id: int) -> None:
        """Deleta conta e limpa dependências"""
        client: Client = self.client_factory()
        
        # Deletar depósitos (CASCADE automático, mas explícito para clareza)
        client.table("depositos_conta") \
            .delete() \
            .eq("conta_id", conta_id) \
            .execute()
        
        # Deletar movimentações (CASCADE automático)
        client.table("movimentacoes_mensais") \
            .delete() \
            .eq("conta_id", conta_id) \
            .execute()
        
        # Desvincular categorias
        client.table("categorias") \
            .update({"conta_vinculada_id": None}) \
            .eq("conta_vinculada_id", conta_id) \
            .execute()

        # Desvincular locais de rendimento
        client.table("rendimentos_locais") \
            .update({"conta_vinculada_id": None}) \
            .eq("conta_vinculada_id", conta_id) \
            .execute()
        
        # Deletar conta
        client.table("contas_correntes") \
            .delete() \
            .eq("id", conta_id) \
            .execute()

    def add_deposito(self, deposito: DepositoConta) -> int:
        """Adiciona depósito e retorna o ID"""
        client: Client = self.client_factory()
        
        response = client.table("depositos_conta").insert({
            "ano": deposito.ano,
            "mes": deposito.mes,
            "conta_id": deposito.conta_id,
            "valor": deposito.valor,
            "nota": deposito.nota,
            "despesa_id": None
        }).execute()
        
        return response.data[0]["id"]

    def update_deposito(self, deposito_id: int, valor: float, nota: str) -> None:
        """Atualiza depósito"""
        client: Client = self.client_factory()
        
        client.table("depositos_conta").update({
            "valor": valor,
            "nota": nota
        }).eq("id", deposito_id).execute()

    def delete_deposito(self, deposito_id: int) -> None:
        """Deleta depósito"""
        client: Client = self.client_factory()
        
        client.table("depositos_conta") \
            .delete() \
            .eq("id", deposito_id) \
            .execute()

    def delete_deposito_matching(
        self,
        ano: int,
        mes: int,
        conta_id: int,
        valor: float,
        nota: str,
    ) -> int:
        """
        Apaga UM depósito que casa exatamente com (ano, mes, conta_id, valor, nota).
        Usada para reverter o reflexo automático de um rendimento. Se o usuário
        editou o depósito, o match falha e nada é removido.
        Retorna a qtd removida (0 ou 1).
        """
        client: Client = self.client_factory()
        response = client.table("depositos_conta") \
            .select("id") \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .eq("conta_id", conta_id) \
            .eq("valor", valor) \
            .eq("nota", nota or "") \
            .order("id", desc=True) \
            .limit(1) \
            .execute()
        if not response.data:
            return 0
        client.table("depositos_conta") \
            .delete() \
            .eq("id", response.data[0]["id"]) \
            .execute()
        return 1

    def get_depositos_detalhe(self, ano: int, mes: int, conta_id: int) -> list[dict]:
        """Retorna todos os depósitos de uma conta em um mês"""
        client: Client = self.client_factory()
        
        response = client.table("depositos_conta") \
            .select("*") \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .eq("conta_id", conta_id) \
            .execute()
        
        return response.data

    def save_movimentacao(self, movimentacao: MovimentacaoMensal, movimentacao_id: int | None = None) -> int:
        """Insere ou atualiza uma movimentação mensal"""
        client: Client = self.client_factory()

        payload = {
            "ano": movimentacao.ano,
            "mes": movimentacao.mes,
            "conta_id": movimentacao.conta_id,
            "valor": movimentacao.valor,
            "nota": movimentacao.nota,
            "tipo": movimentacao.tipo or ""
        }
        if movimentacao_id:
            client.table("movimentacoes_mensais") \
                .update(payload) \
                .eq("id", movimentacao_id) \
                .execute()
            return movimentacao_id

        response = client.table("movimentacoes_mensais").insert(payload).execute()
        return response.data[0]["id"]

    def delete_movimentacao_matching(
        self,
        ano: int,
        mes: int,
        conta_id: int,
        valor: float,
        nota: str,
        tipo: str = "",
    ) -> int:
        """
        Apaga UMA movimentação que casa exatamente com (ano, mes, conta_id, valor, nota, tipo).
        Usada para reverter o reflexo automático de um rendimento. Se o usuário
        editou a movimentação, o match falha e nada é removido.
        """
        client: Client = self.client_factory()
        response = client.table("movimentacoes_mensais") \
            .select("id") \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .eq("conta_id", conta_id) \
            .eq("valor", valor) \
            .eq("nota", nota or "") \
            .eq("tipo", tipo or "") \
            .order("id", desc=True) \
            .limit(1) \
            .execute()
        if not response.data:
            return 0
        client.table("movimentacoes_mensais") \
            .delete() \
            .eq("id", response.data[0]["id"]) \
            .execute()
        return 1

    def delete_movimentacao(self, movimentacao_id: int) -> None:
        """Deleta uma movimentação mensal"""
        client: Client = self.client_factory()

        client.table("movimentacoes_mensais") \
            .delete() \
            .eq("id", movimentacao_id) \
            .execute()

    def delete_movimentacoes_mes(self, ano: int, mes: int) -> None:
        """Deleta todas as movimentações de um mês"""
        client: Client = self.client_factory()

        client.table("movimentacoes_mensais") \
            .delete() \
            .eq("ano", ano) \
            .eq("mes", mes) \
            .execute()
