"""
Perfil de desempenho do hot path `get_dados_ano` (endpoint /api/dados/<ano>).

Cria um banco SQLite temporário com volume de dados realista (vários anos,
milhares de lançamentos) e mede o tempo de carregamento completo do ano,
com e sem cProfile, para identificar gargalos reais.

Uso:
    python scripts/perfil_dados_ano.py [--linhas 3000] [--anos 8]
"""
import argparse
import cProfile
import io
import pprint
import random
import sqlite3
import tempfile
import time
from pathlib import Path

random.seed(42)

CATEGORIAS = [
    "Moradia", "Alimentação", "Transporte", "Saúde", "Educação",
    "Lazer", "Assinaturas", "Mercado", "Vestuário", "Impostos",
    "Pets", "Presentes", "Viagem", "Manutenção", "Telefone",
    "Internet", "Energia", "Água", "Seguros", "Doações",
]


def criar_banco(linhas_por_ano: int, anos: int) -> str:
    """Cria um banco temporário populado e devolve o caminho do arquivo."""
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

    from financeiro.infrastructure.sqlite.schema import init_db

    fd, path = tempfile.mkstemp(suffix=".db")
    import os
    os.close(fd)

    def factory():
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    init_db(factory)
    conn = factory()
    ano_inicial = 2025 - anos + 1

    for ano in range(ano_inicial, 2026):
        conn.execute("INSERT OR IGNORE INTO anos(ano) VALUES(?)", (ano,))
        for i, nome in enumerate(CATEGORIAS):
            conn.execute(
                "INSERT INTO categorias(nome,ordem,inclui_fixas,ano,is_cartao) VALUES(?,?,?,?,0)",
                (nome, i, 1 if i % 4 == 0 else 0, ano),
            )
        # Despesas: linhas_por_ano lançamentos distribuídos pelos meses
        for _ in range(linhas_por_ano):
            mes = random.randint(1, 12)
            cat = random.choice(CATEGORIAS)
            conn.execute(
                "INSERT INTO despesas(ano,mes,categoria,valor,nota,ignorar_total) VALUES(?,?,?,?,?,?)",
                (ano, mes, cat, round(random.uniform(10, 3000), 2),
                 random.choice(["", "compra", "parcela", "promoção"]),
                 1 if random.random() < 0.05 else 0),
            )
        # Receitas: ~1 por mês + extras
        for mes in range(1, 13):
            conn.execute(
                "INSERT INTO receitas(ano,mes,descricao,valor,status) VALUES(?,?,?,?,?)",
                (ano, mes, "Salário", round(random.uniform(5000, 12000), 2), 1),
            )
        # Fixas e metas
        for cat_id in range(1, 6):
            conn.execute(
                "INSERT INTO despesas_fixas_cartao(descricao,valor,dia,ativa,cat_id,ano) VALUES(?,?,?,1,?,?)",
                (f"Fixa {cat_id}", round(random.uniform(50, 800), 2), random.randint(1, 28), cat_id, ano),
            )
        conn.execute(
            "INSERT INTO metas(descricao,valor,ano_meta,concluida,ano_criacao) VALUES(?,?,?,0,?)",
            ("Meta anual", 20000.0, ano, ano),
        )
        # Contas + depósitos + movimentações
        for conta_id in range(1, 6):
            conn.execute(
                "INSERT OR IGNORE INTO contas_correntes(id,nome,ordem,saldo_inicial) VALUES(?,?,?,?)",
                (conta_id, f"Conta {conta_id}", conta_id, 1000.0),
            )
            for mes in range(1, 13):
                if random.random() < 0.7:
                    conn.execute(
                        "INSERT INTO depositos_conta(ano,mes,conta_id,valor,nota) VALUES(?,?,?,?,?)",
                        (ano, mes, conta_id, round(random.uniform(100, 4000), 2), ""),
                    )
                if random.random() < 0.4:
                    conn.execute(
                        "INSERT INTO movimentacoes_mensais(ano,mes,conta_id,valor,nota,tipo) VALUES(?,?,?,?,?,?)",
                        (ano, mes, conta_id, round(random.uniform(-500, 500), 2), "", ""),
                    )
        # Rendimentos
        local_global_id = (ano - ano_inicial) * 3
        for local_id in range(1, 4):
            local_global_id += 1
            conn.execute(
                "INSERT INTO rendimentos_locais(id,ano,nome,ordem,projecao_taxa) VALUES(?,?,?,?,?)",
                (local_global_id, ano, f"Local {local_id}", local_id, 0.01),
            )
            for mes in range(1, 13):
                conn.execute(
                    "INSERT INTO rendimentos_lancamentos(ano,mes,local_id,tipo,valor,nota) VALUES(?,?,?,?,?,?)",
                    (ano, mes, local_global_id, "aporte", round(random.uniform(100, 2000), 2), ""),
                )
                if random.random() < 0.5:
                    conn.execute(
                        "INSERT INTO rendimentos_lancamentos(ano,mes,local_id,tipo,valor,nota) VALUES(?,?,?,?,?,?)",
                        (ano, mes, local_global_id, "rendimento", round(random.uniform(1, 300), 2), ""),
                    )
        conn.execute(
            "INSERT INTO pagamento_status(ano,mes,categoria,status) VALUES(?,?,?,?)",
            (ano, 3, "Moradia", 1),
        )
        conn.execute(
            "INSERT INTO fixas_excecoes(ano,mes,cat_id) VALUES(?,?,?)",
            (ano, 2, 1),
        )

    conn.commit()
    conn.close()
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--linhas", type=int, default=3000, help="despesas por ano")
    parser.add_argument("--anos", type=int, default=8, help="anos de histórico")
    parser.add_argument("--profile", action="store_true", help="executa com cProfile")
    args = parser.parse_args()

    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    os.environ.setdefault("DB_MODE", "sqlite")

    print(f"Criando banco temporário com {args.linhas} despesas/ano x {args.anos} anos...")
    t0 = time.perf_counter()
    path = criar_banco(args.linhas, args.anos)
    print(f"Banco criado em {time.perf_counter() - t0:.2f}s ({Path(path).stat().st_size / 1024:.0f} KB)")

    import sqlite3 as _sqlite3
    from financeiro.infrastructure.constantes import MESES
    from financeiro.infrastructure.sqlite.dashboard_repository import SQLiteDashboardRepository

    def factory(**kwargs):
        conn = _sqlite3.connect(path)
        conn.row_factory = _sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    repo = SQLiteDashboardRepository(factory, MESES)
    ano_alvo = 2025

    # Aquecimento (primeira chamada faz sync de rendimentos_realizados)
    repo.get_dados_ano(ano_alvo)

    if args.profile:
        pr = cProfile.Profile()
        pr.enable()
        for _ in range(3):
            repo.get_dados_ano(ano_alvo)
        pr.disable()
        s = io.StringIO()
        pr.print_stats(sort="cumulative")
        print(s.getvalue()[:6000])
    else:
        # Medição: melhor de 5 execuções
        tempos = []
        for _ in range(5):
            t0 = time.perf_counter()
            data = repo.get_dados_ano(ano_alvo)
            tempos.append(time.perf_counter() - t0)
        tempos.sort()
        print(f"\nTempo por carga de ano (melhor de 5): {tempos[0] * 1000:.1f} ms")
        print(f"  mediana: {tempos[2] * 1000:.1f} ms | pior: {tempos[-1] * 1000:.1f} ms")
        print(f"Resumo: {len(data['despesas'])} categorias, {len(data['anos'])} anos, "
              f"{len(data['contas'])} contas, {len(data['rendimentos_locais'])} locais de rendimento")


if __name__ == "__main__":
    import os
    main()
