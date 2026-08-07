import csv
import io
import re
import unicodedata

from financeiro.infrastructure.constantes import NOMES_MESES_NORMALIZADOS


MESES_CSV = {
    "jan": 1,
    "janeiro": 1,
    "fev": 2,
    "fevereiro": 2,
    "mar": 3,
    "marco": 3,
    "abr": 4,
    "abril": 4,
    "mai": 5,
    "maio": 5,
    "jun": 6,
    "junho": 6,
    "jul": 7,
    "julho": 7,
    "ago": 8,
    "agosto": 8,
    "set": 9,
    "setembro": 9,
    "out": 10,
    "outubro": 10,
    "nov": 11,
    "novembro": 11,
    "dez": 12,
    "dezembro": 12,
}


def normalizar_cabecalho_csv(valor):
    texto = str(valor or "").strip().lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return texto.strip()


def mes_por_cabecalho_csv(valor):
    return MESES_CSV.get(normalizar_cabecalho_csv(valor))


def linha_tem_mes_csv(row):
    return any(mes_por_cabecalho_csv(coluna) for coluna in row)


def parse_valor_csv(valor_raw, valores_invalidos=None):
    """Converte string de valor em float (suporta '1.234,56', '1,5', '-50')."""
    raw = valor_raw.strip()
    if not raw:
        return None
    neg = "-" in raw
    limpo = re.sub(r"[^\d,.]", "", raw)
    if not limpo:
        if valores_invalidos is not None:
            valores_invalidos.append(raw)
        return None
    limpo = limpo.replace(".", "").replace(",", ".")
    try:
        v = float(limpo)
        return -v if neg else v
    except ValueError:
        if valores_invalidos is not None:
            valores_invalidos.append(raw)
        return None


def detectar_cabecalho_csv(rows):
    """
    Detecta a linha do cabeçalho e o mapa coluna -> mês (1-12).
    Retorna (linha_cabecalho, col_to_mes).
    """
    linha_cabecalho = 1
    for i, r in enumerate(rows[:5]):
        if any(h.lower().strip().replace("ç", "c") in NOMES_MESES_NORMALIZADOS for h in r):
            linha_cabecalho = i
            break

    header = []
    for c in rows[linha_cabecalho]:
        norm = c.strip().lower().replace("\u00e7", "c").replace("\u00e3", "a").replace("\u00e2", "a")
        header.append(norm)

    col_to_mes = {}
    for i, h in enumerate(header):
        if h in NOMES_MESES_NORMALIZADOS:
            col_to_mes[i] = NOMES_MESES_NORMALIZADOS.index(h) + 1
    if not col_to_mes:
        # Fallback: cabeçalho com variações (abr., mês, etc.)
        for i, r in enumerate(rows[:5]):
            if linha_tem_mes_csv(r):
                linha_cabecalho = i
                break
        for i, h in enumerate(rows[linha_cabecalho]):
            mes = mes_por_cabecalho_csv(h)
            if mes:
                col_to_mes[i] = mes
    return linha_cabecalho, col_to_mes


def montar_csv_exportacao(ano, meses, cats, despesas, receitas, fixas, metas,
                          rend_locais, rendimentos, rend_tipos_por_local,
                          movimentacoes, depositos, fixas_excecoes):
    """
    Monta o CSV completo de exportação do ano a partir dos dados já agregados.
    Retorna bytes UTF-8 com BOM. Fonte única de verdade para o formato exportado.
    """
    def _brl(val):
        # Sempre 2 casas decimais, sem ruído de ponto flutuante (ex: 91424,40000000001)
        return f"{round(float(val or 0), 2):.2f}".replace(".", ",")

    out = io.StringIO()
    writer = csv.writer(out, delimiter=";", quoting=csv.QUOTE_ALL)
    out.write("sep=;\r\n")
    writer.writerow([ano] + [""] * 13)
    writer.writerow(["Despesas"] + [""] * 13)  # Título da seção de despesas
    writer.writerow([""] + meses + ["Total"])

    for cat in cats:
        row = [cat["nome"]]
        tot = 0
        for m in range(1, 13):
            d_info = despesas.get(cat["nome"], {}).get(m, {})
            vlanc = d_info.get("v", 0) or 0
            notas = d_info.get("notas", "")
            vfixas = 0
            if f"{cat['id']}_{m}" not in fixas_excecoes:
                vfixas += sum(f["valor"] for f in fixas if f.get("cat_id") == cat["id"])
                if cat["inclui_fixas"]:
                    vfixas += sum(f["valor"] for f in fixas if not f.get("cat_id"))
            v = vlanc + vfixas
            if v == 0 and notas:
                row.append(notas)
            else:
                row.append(_brl(v))
            tot += v
        row.append(_brl(tot))
        writer.writerow(row)

    writer.writerow([""] * 14)
    writer.writerow([""] * 14)
    writer.writerow(["Despesas Fixas", "Dia", "Valor"] + [""] * 11)
    for f in fixas:
        writer.writerow([f["descricao"], f.get("dia", ""), _brl(f["valor"])] + [""] * 11)
    writer.writerow(["Total Fixas", "", _brl(sum(f["valor"] for f in fixas))] + [""] * 11)

    writer.writerow([""] * 14)
    writer.writerow([""] * 14)
    writer.writerow(["Metas", "Valor Alvo", "Ano", "Status"] + [""] * 10)
    for mt in metas:
        status = "Concluida" if mt.get("concluida") else "Em andamento"
        writer.writerow([mt["descricao"], _brl(mt.get("valor", 0)), mt.get("ano_meta", ""), status] + [""] * 10)

    writer.writerow([""] * 14)
    writer.writerow([""] * 14)
    writer.writerow(["Receitas"] + meses + ["Total"])
    row_rec = ["Receitas"]
    total_rec = 0
    for m in range(1, 13):
        v = receitas.get(m, 0) or 0
        total_rec += v
        row_rec.append(_brl(v) if v else "")
    row_rec.append(_brl(total_rec))
    writer.writerow(row_rec)

    writer.writerow([""] * 14)
    writer.writerow([""] * 14)
    writer.writerow(["Rendimentos"] + meses + ["Total", "Conta Vinculada"])
    for rl in rend_locais:
        conta_vinculada_nome = rl.get("conta_vinculada_nome") or ""
        tipos = sorted(rend_tipos_por_local.get(rl["id"], set()))
        if not tipos:
            # Local sem lançamentos: exporta linha vazia com nome
            row = [rl["nome"]] + [""] * 13 + [conta_vinculada_nome]
            writer.writerow(row)
        elif len(tipos) == 1:
            # Um único tipo: exporta sem sufixo (compatível com versões anteriores)
            tipo_unico = tipos[0]
            row = [rl["nome"]]
            total_linha = 0.0
            for m in range(1, 13):
                v = float((rendimentos.get((rl["id"], tipo_unico), {}) or {}).get(m, 0) or 0)
                total_linha += v
                row.append(_brl(v) if v != 0 else "")
            row.append(_brl(total_linha))
            row.append(conta_vinculada_nome)
            writer.writerow(row)
        else:
            # Múltiplos tipos: uma linha por tipo com sufixo " - tipo"
            for tipo in tipos:
                sub_row = [f"{rl['nome']} - {tipo}"]
                sub_total = 0.0
                for m in range(1, 13):
                    v = float((rendimentos.get((rl["id"], tipo), {}) or {}).get(m, 0) or 0)
                    sub_total += v
                    sub_row.append(_brl(v) if v != 0 else "")
                sub_row.append(_brl(sub_total))
                # Conta vinculada só na primeira linha do grupo
                sub_row.append(conta_vinculada_nome if tipo == tipos[0] else "")
                writer.writerow(sub_row)

    # Movimentações Mensais (por conta)
    if movimentacoes:
        writer.writerow([""] * 14)
        writer.writerow([""] * 14)
        writer.writerow(["Movimentações"] + meses + ["Total"])
        for conta_nome in sorted(movimentacoes.keys()):
            row = [conta_nome]
            total_linha = 0
            for m in range(1, 13):
                v = movimentacoes[conta_nome].get(m, 0) or 0
                total_linha += v
                row.append(_brl(v) if v != 0 else "")
            row.append(_brl(total_linha))
            writer.writerow(row)

    # Depósitos / Contas — Saldo Acumulado
    if depositos:
        writer.writerow([""] * 14)
        writer.writerow([""] * 14)
        writer.writerow(["Contas Saldo Acumulado"] + meses + ["Total"])
        for conta_nome in sorted(depositos.keys()):
            row = [conta_nome]
            saldo_acumulado = 0.0
            for m in range(1, 13):
                delta = depositos[conta_nome].get(m, 0) or 0
                saldo_acumulado += delta
                row.append(_brl(saldo_acumulado))
            row.append(_brl(saldo_acumulado))
            writer.writerow(row)

    return ("\ufeff" + out.getvalue()).encode("utf-8")
