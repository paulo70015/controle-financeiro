"""Regras puras de domínio para busca unificada no ano ativo."""

import unicodedata
from financeiro.infrastructure.fixas_utils import eh_soma_fixas


def normalizar_texto(texto: str | None) -> str:
    """Remove acentos e converte para minúsculas para busca insensível a caixa/acentuação."""
    if not texto:
        return ""
    nfd = unicodedata.normalize("NFD", str(texto))
    sem_acento = "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")
    return sem_acento.lower().strip()


def formatar_valor_busca(valor: float | None) -> list[str]:
    """Gera representações textuais de um valor numérico para comparação na busca."""
    if valor is None:
        return []
    try:
        v = abs(float(valor))
    except (TypeError, ValueError):
        return []
    sem_milhar = f"{v:.2f}".replace(".", ",")
    com_milhar = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    ponto = f"{v:.2f}"
    inteiro = str(int(v)) if v == int(v) else ""
    termos = [sem_milhar, com_milhar, ponto, f"r$ {sem_milhar}", f"r$ {com_milhar}"]
    if inteiro:
        termos.append(inteiro)
    return termos


def _casa_termo(q_norm: str, campos_texto: list[str | None], valor: float | None = None) -> bool:
    """Verifica se o termo normalizado casa com algum campo de texto ou valor."""
    if not q_norm:
        return False
    for campo in campos_texto:
        if campo and q_norm in normalizar_texto(campo):
            return True
    if valor is not None:
        for repr_val in formatar_valor_busca(valor):
            if q_norm in repr_val:
                return True
    return False


def filtrar_busca_ano(termo: str, registros: dict, limite: int = 50) -> list[dict]:
    """Filtra todos os registros de um ano pelo termo pesquisado.

    Espera em `registros`:
      - categorias: list[dict]
      - despesas: list[dict]
      - receitas: list[dict]
      - contas: list[dict]
      - depositos: list[dict]
      - movimentacoes: list[dict]
      - fixas: list[dict]
      - metas: list[dict]
      - rendimentos_locais: list[dict]
      - rendimentos_lancamentos: list[dict]
      - fixas_excecoes: set[str] | dict[str, bool]
    """
    q_norm = normalizar_texto(termo)
    if not q_norm:
        return []

    resultados: list[dict] = []
    categorias = registros.get("categorias") or []
    cat_id_por_nome = {c.get("nome"): c.get("id") for c in categorias if c.get("nome")}
    contas = registros.get("contas") or []
    conta_nome_por_id = {c.get("id"): c.get("nome") for c in contas if c.get("id") is not None}
    locais = registros.get("rendimentos_locais") or []
    local_nome_por_id = {l.get("id"): l.get("nome") for l in locais if l.get("id") is not None}
    fixas_excecoes = registros.get("fixas_excecoes") or {}

    # 1. Lançamentos de Despesas
    for d in registros.get("despesas") or []:
        nota = d.get("nota") or ""
        cat_nome = d.get("categoria") or ""
        mes = d.get("mes")
        cat_id = cat_id_por_nome.get(cat_nome)
        if eh_soma_fixas(nota) and cat_id is not None and f"{cat_id}_{mes}" in fixas_excecoes:
            continue
        valor = float(d.get("valor") or 0)
        nota_limpa = nota.replace("\u200b", "").strip()
        if _casa_termo(q_norm, [nota_limpa, cat_nome], valor):
            resultados.append({
                "tipo": "despesa",
                "visao": "despesas",
                "id": d.get("id"),
                "mes": mes,
                "categoria": cat_nome,
                "cat_id": cat_id,
                "titulo": cat_nome,
                "subtitulo": nota_limpa or ("Cartão (Não somado)" if d.get("ignorar_total") else "Despesa"),
                "valor": valor,
            })

    # 2. Lançamentos de Receitas
    for r in registros.get("receitas") or []:
        desc = (r.get("descricao") or "Receita").strip()
        nota = (r.get("nota") or "").strip()
        valor = float(r.get("valor") or 0)
        if _casa_termo(q_norm, [desc, nota, "Receitas"], valor):
            resultados.append({
                "tipo": "receita",
                "visao": "despesas",
                "id": r.get("id"),
                "mes": r.get("mes"),
                "titulo": desc,
                "subtitulo": nota or "Receita",
                "valor": valor,
            })

    # 3. Lançamentos de Rendimentos
    tipo_label_map = {"aporte": "Aporte", "saque": "Saque", "rendimento": "Rendimento"}
    for rl in registros.get("rendimentos_lancamentos") or []:
        nota = (rl.get("nota") or "").strip()
        if nota == "Projeção cancelada":
            continue
        local_id = rl.get("local_id")
        local_nome = local_nome_por_id.get(local_id) or "Rendimento"
        tipo_raw = rl.get("tipo") or "rendimento"
        tipo_label = tipo_label_map.get(tipo_raw, "Rendimento")
        valor = float(rl.get("valor") or 0)
        if _casa_termo(q_norm, [nota, local_nome, tipo_label], valor):
            resultados.append({
                "tipo": "rendimento_lanc",
                "visao": "rendimentos",
                "id": rl.get("id"),
                "mes": rl.get("mes"),
                "local_id": local_id,
                "local_nome": local_nome,
                "titulo": local_nome,
                "subtitulo": f"{tipo_label}: {nota}" if nota else tipo_label,
                "valor": -abs(valor) if tipo_raw == "saque" else valor,
            })

    # 4. Depósitos em Contas Correntes
    for dep in registros.get("depositos") or []:
        conta_id = dep.get("conta_id")
        conta_nome = conta_nome_por_id.get(conta_id) or "Conta"
        nota = (dep.get("nota") or "").strip()
        valor = float(dep.get("valor") or 0)
        if _casa_termo(q_norm, [nota, conta_nome], valor):
            resultados.append({
                "tipo": "deposito",
                "visao": "despesas",
                "id": dep.get("id"),
                "mes": dep.get("mes"),
                "conta_id": conta_id,
                "conta_nome": conta_nome,
                "titulo": conta_nome,
                "subtitulo": nota or "Depósito / Saque em conta",
                "valor": valor,
            })

    # 5. Movimentações Mensais
    for mv in registros.get("movimentacoes") or []:
        conta_id = mv.get("conta_id")
        conta_nome = conta_nome_por_id.get(conta_id) or "Conta"
        nota = (mv.get("nota") or "").strip()
        tipo_mv = (mv.get("tipo") or "").strip()
        valor = float(mv.get("valor") or 0)
        if _casa_termo(q_norm, [nota, conta_nome, tipo_mv, "Movimentação"], valor):
            resultados.append({
                "tipo": "movimentacao",
                "visao": "despesas",
                "id": mv.get("id"),
                "mes": mv.get("mes"),
                "conta_id": conta_id,
                "conta_nome": conta_nome,
                "titulo": f"Movimentação • {conta_nome}",
                "subtitulo": nota or tipo_mv or "Movimentação mensal",
                "valor": valor,
            })

    # 6. Despesas Fixas (Drawer)
    for fx in registros.get("fixas") or []:
        desc = (fx.get("descricao") or "").strip()
        valor = float(fx.get("valor") or 0)
        dia = fx.get("dia")
        if _casa_termo(q_norm, [desc, f"Dia {dia}" if dia else ""], valor):
            resultados.append({
                "tipo": "fixa",
                "visao": "drawer_fixas",
                "id": fx.get("id"),
                "mes": None,
                "titulo": desc,
                "subtitulo": f"Despesa Fixa (Dia {dia or '?'})",
                "valor": valor,
            })

    # 7. Metas (Drawer)
    for m in registros.get("metas") or []:
        desc = (m.get("descricao") or "").strip()
        valor = float(m.get("valor") or 0)
        ano_meta = m.get("ano_meta")
        if _casa_termo(q_norm, [desc, str(ano_meta) if ano_meta else ""], valor):
            resultados.append({
                "tipo": "meta",
                "visao": "drawer_metas",
                "id": m.get("id"),
                "mes": None,
                "titulo": desc,
                "subtitulo": f"Meta ({ano_meta or 'sem ano'})",
                "valor": valor,
            })

    # 8. Categorias de Despesas
    for c in categorias:
        nome = (c.get("nome") or "").strip()
        tooltip = (c.get("tooltip") or "").strip()
        if _casa_termo(q_norm, [nome, tooltip], None):
            resultados.append({
                "tipo": "categoria",
                "visao": "despesas",
                "id": c.get("id"),
                "mes": None,
                "categoria": nome,
                "cat_id": c.get("id"),
                "titulo": nome,
                "subtitulo": tooltip or "Categoria de Despesas",
                "valor": None,
            })

    # 9. Locais de Rendimentos
    for loc in locais:
        nome = (loc.get("nome") or "").strip()
        if _casa_termo(q_norm, [nome], None):
            resultados.append({
                "tipo": "rendimento_local",
                "visao": "rendimentos",
                "id": loc.get("id"),
                "mes": None,
                "local_id": loc.get("id"),
                "local_nome": nome,
                "titulo": nome,
                "subtitulo": "Local de Rendimento",
                "valor": None,
            })

    # 10. Contas Correntes
    for ct in contas:
        nome = (ct.get("nome") or "").strip()
        if _casa_termo(q_norm, [nome], None):
            resultados.append({
                "tipo": "conta",
                "visao": "despesas",
                "id": ct.get("id"),
                "mes": None,
                "conta_id": ct.get("id"),
                "conta_nome": nome,
                "titulo": nome,
                "subtitulo": "Conta Corrente",
                "valor": None,
            })

    return resultados[:limite]
