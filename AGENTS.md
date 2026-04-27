# AGENTS.md

## Contexto do Projeto

Este projeto e o Controle Financeiro Pessoal v1.3.0.

Antes de alterar codigo, leia quando relevante:
- `.kiro/steering/project-context.md`
- `.kiro/steering/conventions.md`

Para mudancas relacionadas a Supabase, SQLite, schema, Flutter ou migracao, consulte tambem:
- `.kiro/docs/migracao-supabase/`
- `specs/`
- `docs/`

## Regras Principais

- Backend: Python 3.10+ e Flask.
- Frontend: HTML, CSS e JavaScript Vanilla. Nao sugerir React, Vue, Svelte, jQuery ou frameworks externos.
- Manter arquitetura DDD simplificada:
  - `financeiro/domain/`: entidades e regras puras.
  - `financeiro/application/`: use cases e orquestracao de negocio.
  - `financeiro/infrastructure/`: banco de dados e servicos externos.
  - `financeiro/interfaces/http/`: rotas Flask sem regra de negocio.
- Interface, alertas e mensagens voltadas ao usuario devem ficar em PT-BR.
- Nao renomear tabelas ou colunas existentes sem necessidade explicita.
- Preservar compatibilidade com runtime PyInstaller.
- Nao criar rotas de gravacao que alterem arquivos no `BASE_DIR` em producao.
- Sempre verificar nulidade antes de manipular elementos DOM.
- Aplicar DRY rigorosamente no backend e no frontend.

## Fluxo Para Funcionalidades Backend

Ao criar ou alterar funcionalidade que envolva backend, seguir este fluxo:

1. Repository: criar ou adaptar metodo no `*_repository.py`.
2. Use Case: atualizar regra em `use_cases.py`.
3. Route: expor via blueprint Flask em `*_routes.py`.
4. JS Module: conectar no modulo correspondente em `static/js/modules/`.

## Regras de Negocio Criticas

- Fixas com excecoes: ao apagar uma fixa de um mes especifico, inserir em `fixas_excecoes`; nao deletar a fixa recorrente.
- Status de pagamento pertence a celula `(ano, mes, categoria)`, nao a uma despesa individual.
- Rendimentos usam saldo acumulado: `Saldo(N) = Saldo(N-1) + Aporte(N) + Rendimento(N)`.
- Ao criar, editar ou duplicar fixas entre anos, remapear `cat_id` para categoria homonima no ano de destino.
- Modais de detalhe usam Lazy Commit com filas locais; gravacao/delecao efetiva ocorre no fechamento do modal.
- Requisicoes de `load()` devem proteger contra race condition com identificador sequencial.

## Testes

Apos alteracoes relevantes, rodar os testes aplicaveis:

- `python test_suite.py`
- `python test_sqlite_mode.py`
- `python test_dependencies_compatibility.py`

Se algum teste nao puder ser executado, informe o motivo.
