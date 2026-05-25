from financeiro.domain.despesas.entities import Despesa, DespesaLote


class DespesasUseCases:
    def __init__(self, repository, categorias_repository):
        self.repository = repository
        self.categorias_repository = categorias_repository

    def lancar(self, payload: dict) -> int:
        despesa = Despesa(
            ano=int(payload["ano"]),
            mes=int(payload["mes"]),
            categoria=payload["categoria"],
            valor=float(payload.get("valor") or 0),
            nota=payload.get("nota", ""),
            ignorar_total=bool(payload.get("ignorar_total", False)),
        )
        
        # Inserir despesa (repositório retorna ID)
        despesa_id = self.repository.add_despesa(despesa)
        
        # Aplicar regra de negócio de movimentação
        if not despesa.ignorar_total and despesa.valor > 0:
            # Buscar conta vinculada
            conta_id = self.categorias_repository.get_conta_vinculada(
                despesa.categoria, 
                despesa.ano
            )
            
            # Se categoria tem conta vinculada, registrar débito
            if conta_id:
                self.repository.add_deposito_vinculado_simples(
                    ano=despesa.ano,
                    mes=despesa.mes,
                    conta_id=conta_id,
                    valor=-despesa.valor,  # Débito (valor negativo)
                    nota=despesa.nota or despesa.categoria,
                    despesa_id=despesa_id,
                )
        
        return despesa_id

    def lancar_lote(self, payload: dict) -> list[int]:
        lote = DespesaLote(
            ano=int(payload["ano"]),
            categoria=payload["categoria"],
            valor_base=float(payload.get("valor") or 0),
            acrescimo=float(payload.get("acrescimo") or 0),
            nota=payload.get("nota", ""),
            ignorar_total=bool(payload.get("ignorar_total", False)),
        )
        meses = payload.get("meses", list(range(1, 13)))
        
        # Buscar conta vinculada uma única vez (otimização)
        conta_id = None
        if not lote.ignorar_total:
            conta_id = self.categorias_repository.get_conta_vinculada(
                lote.categoria, 
                lote.ano
            )
        
        # Preparar dados para lote
        despesas_data = []
        depositos_data = []
        
        for i, mes in enumerate(meses):
            valor = round(lote.valor_base + (lote.acrescimo * i), 2)
            
            despesas_data.append({
                'ano': lote.ano,
                'mes': mes,
                'categoria': lote.categoria,
                'valor': valor,
                'nota': lote.nota,
                'ignorar_total': lote.ignorar_total,
            })
            
            # Se tem conta vinculada e valor > 0, preparar depósito
            if conta_id and valor > 0:
                depositos_data.append({
                    'ano': lote.ano,
                    'mes': mes,
                    'conta_id': conta_id,
                    'valor': -valor,  # Débito
                    'nota': lote.nota or lote.categoria,
                })
        
        # Delegar ao repositório (transação atômica)
        ids = self.repository.add_despesa_lote_com_depositos(despesas_data, depositos_data)
        return ids

    def excluir(self, despesa_id: int) -> None:
        self.repository.delete_despesa(despesa_id)

    def detalhar(self, ano: int, mes: int, categoria: str) -> list[dict]:
        return self.repository.get_despesas_detalhe(ano=ano, mes=mes, categoria=categoria)

    def excluir_categoria_no_ano(self, ano: int, categoria: str) -> None:
        self.repository.delete_despesas_da_categoria_no_ano(ano=ano, categoria=categoria)

    def editar(self, despesa_id: int, payload: dict) -> None:
        valor = float(payload.get("valor", 0))
        nota = payload.get("nota", "")
        ignorar_total = bool(payload.get("ignorar_total", False))
        mes = payload.get("mes")
        
        # Buscar dados da despesa
        despesa_info = self.repository.get_despesa_by_id(despesa_id)
        if not despesa_info:
            return
        mes_destino = int(mes) if mes is not None else int(despesa_info["mes"])
        
        # Buscar conta vinculada (se aplicável)
        conta_id = None
        if not ignorar_total and valor > 0:
            conta_id = self.categorias_repository.get_conta_vinculada(
                despesa_info['categoria'],
                despesa_info['ano']
            )
        
        # Delegar ao repositório (transação atômica)
        self.repository.update_despesa_com_deposito(
            despesa_id=despesa_id,
            valor=valor,
            nota=nota,
            ignorar_total=ignorar_total,
            conta_id=conta_id,
            ano=despesa_info['ano'],
            mes=mes_destino,
            categoria=despesa_info['categoria'],
        )
