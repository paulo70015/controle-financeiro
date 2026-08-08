# Plano — Bug de infraestrutura: timeout intermitente no E2E (Page.goto)

> **Status:** resolvido em 2026-08-07 (ver seção 10 — correções estruturais aplicadas e
> critério de aceite validado).
> **Criado em:** 2026-08-07
> **Responsável:** a definir quando for retomado

## 1. Contexto

Os testes E2E (Playwright, `test_browser/`) apresentam **falha intermitente de infraestrutura**:
`Page.goto: Timeout 30000ms exceeded` ao navegar para `http://127.0.0.1:8085/?ano=2036`
(ANO_TESTE = ano atual + 10), **sempre no setup da fixture `page`** (nunca em asserção).

- Nunca foi relacionado a mudança de código: o arquivo que errou passou isolado logo em seguida.
- Não é coberto pelos critérios de aceite de feature — é ruído de ambiente.

## 2. Evidências (execuções em 2026-08-07)

| Execução | Resultado | Erro |
|---|---|---|
| E2E completo (após correção metas) | 124/124 OK | — |
| E2E `test_metas` + `test_navegacao` | 24/24 OK | — |
| E2E completo | 123 passed, **1 error** | `test_ui_interactions::TestDragDrop::test_drag_handle_existe` — goto timeout |
| `test_ui_interactions.py` isolado | 6/6 OK | — |
| E2E completo | 123 passed, **1 error** | `test_contas::TestMovimentacaoMensal::test_abrir_movimentacao` — goto timeout |
| `test_contas.py` isolado | 11/11 OK | — |
| `test_metas` + `test_fixas` + `test_navegacao` | 29/29 OK | — |

Padrão: **~1 error por execução completa**, sempre no `goto` da primeira página de algum teste;
execuções curtas/isoladas nunca falham.

## 3. Sintomas e observações

1. O erro é `TimeoutError` no `page.goto` (evento `load`) — o servidor pode estar respondendo, mas o
   navegador não completou o load em 30s (ou o servidor travou momentaneamente).
2. Em execução anterior foi observado `sqlite3.OperationalError: database is locked` em POSTs
   — **causado por 2 servidores órfãos** (`python app.py --show-console`) deixados pelo
   `test_suite.py` (o `proc.terminate()` no Windows não mata o processo filho). Órfãos mortos
   → locks sumiram, mas o timeout de navegação persistiu intermitente.
3. O projeto fica em `C:\Users\pdtlc\OneDrive\Documentos\controle_financeiro` — **OneDrive
   sincroniza o diretório**, incluindo `financeiro.db` (compartilhado entre todas as suítes).

## 4. Hipóteses (ordenadas por probabilidade)

- **H1 — OneDrive/antivírus escaneando o diretório**: o primeiro acesso aos arquivos
  (`financeiro.db`, assets) fica lento de forma imprevisível; explica a intermitência e o fato
  de nunca reproduzir isolado (carga menor).
- **H2 — Primeiro load da sessão lento (servidor single-thread)**: `init_db` + primeira
  requisição + OneDrive scan podem estourar os 30s do `goto`; testes posteriores usam caches.
- **H3 — Concorrência de escrita SQLite**: `debouncedLoad` do frontend dispara requisições
  concorrentes; sem `busy_timeout`, um lock momentâneo (outro processo/suíte com o mesmo
  `financeiro.db`) segura o `/api/dados` e atrasa o load além de 30s.
- **H4 — Órfãos do `test_suite.py` reaparecendo**: se alguém rodar `test_suite.py` antes do
  E2E, servidores na 8086 reabrem o `financeiro.db` e reintroduzem locks (H3).

## 5. Plano de investigação (quando for atacar)

Ordem sugerida — cada passo é barato e descarta uma hipótese:

1. **Checar órfãos antes de rodar**: script rápido que verifica portas 8085/8086 e processos
   `python app.py` antes da suíte; matar se existirem. (Descarta H4/H3 parcial.)
2. **Instrumentar o load**: na fixture `page` do `test_browser/conftest.py`, logar o tempo do
   `goto` e o tempo de resposta do servidor (`/` e `/api/dados/<ano>`); no timeout, salvar
   screenshot + `page.content()` truncado para diagnóstico. (Confirma H1/H2/H3.)
3. **Teste de isolamento do OneDrive**: copiar o projeto para um caminho fora do OneDrive
   (ex: `C:\tmp\controle_financeiro`) e rodar a suíte completa 2×. Se zerar os erros → H1
   confirmada.
4. **Reprodução estressada**: rodar a suíte completa 3× seguidas e contabilizar erros (meta:
   reprodutibilidade documentada antes de corrigir).

## 6. Correções candidatas (aplicar só após confirmar a hipótese)

- **conftest.py**: aumentar timeout do `goto` para 60s **ou** adicionar retry (1 tentativa)
  no setup da fixture `page` — mitiga H1/H2 sem mudar a semântica dos testes.
- **test_suite.py**: encerrar servidores com `taskkill /T /F` (ou `CREATE_NEW_PROCESS_GROUP`
  + `CTRL_BREAK`) para não deixar órfãos — corrige H4 de vez.
- **SQLite**: `PRAGMA busy_timeout` (ex: 5000) e/ou `journal_mode=WAL` na connection_factory
  — reduz H3 (avaliar impacto no backup/restore do conftest, que já limpa WAL/SHM).
- **Isolamento físico**: mover o banco de teste para um temp dir fora do OneDrive
  (o conftest já tem `DB_TESTE` — hoje morto, pois o app sempre usa `financeiro.db` na raiz).
  Esta é a correção estrutural mais forte para H1.

## 7. Critério de aceite

- 2 execuções completas consecutivas da suíte E2E **sem nenhum error/assertion**.
- O tempo do `goto` da fixture fica registrado em log (para detectar regressão futura).

## 8. Fora de escopo

- Não alterar a semântica dos testes para "esconder" o erro (ex: `pytest.mark.flaky` sem
  diagnóstico).
- Não misturar esta correção com mudanças de feature (histórico do repo fica rastreável).

## 9. Referências

- `test_browser/conftest.py` — fixture `page` (goto) e `flask_server` (backup/restore do db).
- `test_suite.py` — lança `app.py --show-console` e não mata o processo filho no Windows.
- `financeiro/infrastructure/sqlite/schema.py` — `PRAGMA foreign_keys = ON` no `init_db`.
- AGENTS.md → "Isolamento de Ambiente (Testes vs Producao)" — lição: infra compartilhada é a
  causa mais comum de falhas intermitentes.

## 10. Resolução (2026-08-07)

> **Status:** resolvido — aplicadas as correções estruturais da seção 6 (H1, H3 e H4),
> sem esperar reprodução estressada. O banco de teste foi fisicamente isolado do OneDrive,
> eliminando a causa mais provável (H1) por construção, e as demais correções são baratas
> e independentes. Critério de aceite validado com 2 execuções completas consecutivas.

### O que foi feito

1. **Isolamento físico do banco de teste (H1 — correção estrutural)**
   - `financeiro/infrastructure/runtime/paths.py`: novas funções `get_db_path()` e
     `get_db_backup_path()`; `get_db_path()` respeita a env var `SQLITE_DB_PATH`
     (default inalterado: `<data_dir>/financeiro.db`).
   - `repository_factory.py`, `sqlite/csv_repository.py`, `sqlite/db_backup_repository.py`:
     passam a usar `get_db_path()`/`get_db_backup_path()` (DRY — caminho centralizado).
   - `test_browser/conftest.py`: o servidor E2E recebe `SQLITE_DB_PATH` apontando para
     `%TEMP%/controle_financeiro_e2e/financeiro.db` — **fora do OneDrive** e sem tocar no
     `financeiro.db` real do usuário (o antigo backup/restore de `financeiro.db.bak_tests`
     foi removido — não é mais necessário).

2. **Órfãos (H4/H3)**
   - Novo módulo `test_browser/processos_util.py` (DRY): `kill_arvore()` — no Windows usa
     `taskkill /T /F` (o `terminate()` não mata o processo filho) — e
     `matar_servidores_na_porta()` (netstat/lsof + kill).
   - `test_browser/conftest.py`: `matar_servidores_na_porta(8085)` antes de subir o
     servidor (mata órfãos de execuções anteriores) e `kill_arvore()` no teardown.
   - `test_suite.py`: pré-kill na porta 8086 e `kill_arvore()` no teardown e no `atexit`
     (elimina os órfãos que reintroduziam locks no banco).

3. **Robustez do goto (H2)**
   - Fixture `page`: `goto` e `wait_for_function` com timeout de 60s e **retry de 1
     tentativa** no setup; tempos registrados em `test_browser/artefatos/e2e-goto.log`
     (aceite: tempo do goto em log). Em falha final, salva screenshot + HTML truncado em
     `test_browser/artefatos/` para diagnóstico.

4. `test_browser/artefatos/` adicionado ao `.gitignore`.

5. **`test_suite.py` e `test_sqlite_mode.py` (unitários) também isolados**: os servidores/
   testes recebem `SQLITE_DB_PATH` apontando para diretórios próprios em `%TEMP%`
   (`controle_financeiro_unit`, `controle_financeiro_sqlite_mode`) — as suítes deixam de
   compartilhar/competir pelo mesmo banco e o `financeiro.db` real do usuário nunca mais é
   tocado por nenhuma suíte (o `test_sqlite_mode.py` antes **deletava** o banco real da raiz).

6. **DRY**: `test_browser/processos_util.py` centraliza `matar_servidores_na_porta`,
   `kill_arvore` e `limpar_banco_teste` (remover banco + bak/WAL/SHM com tolerância a
   handles abertos no Windows) — usado pelo conftest, test_suite e test_sqlite_mode.

### Notas

- `busy_timeout = 5000` já existia em `repository_factory._get_sqlite_connection` — nada a fazer (H3 residual).
- Com o banco em TEMP, os testes E2E nunca mais competem com o `financeiro.db` real nem
  dependem do estado de sincronização do OneDrive. Execuções curtas isoladas já
  funcionavam; o objetivo é eliminar o ~1 error por execução completa.
- Validação: ver critério de aceite na seção 7 — 2 execuções completas consecutivas sem
  error/assertion (histórico das execuções registrado junto da resolução).

## 11. Otimização de velocidade (2026-08-07)

Diagnóstico: cada execução completa levava ~380s (124 testes, ~3,1s/teste), com a maior
parte em (a) setup da fixture `page` — mediana 0,8s de goto, mas picos de 4–51s causados
por antivírus/OneDrive escaneando os assets do projeto (o antigo timeout de 30s do
`Page.goto` estourava exatamente nesses picos) — e (b) ações/esperas dos testes. O
backend é irrelevante: 4–7ms por requisição (benchmark).

### O que foi feito

- **Execução paralela com pytest-xdist** (`-n 4 --dist loadfile`):
  - `test_browser/conftest.py`: cada worker usa porta (`8085 + índice`) e banco em TEMP
    próprios (`controle_financeiro_e2e_gwN`) — sem xdist o comportamento é o histórico
    (porta 8085, `controle_financeiro_e2e`).
  - `test_browser/rodar-testes.bat` e `rodar-testes.sh`: instalam `pytest-xdist` se
    faltar e rodam com `-n 4 --dist loadfile` (arquivos inteiros por worker, preservando
    a ordem intra-arquivo).
- **Resultado**: ~380s → **~72–136s** (3–5× mais rápido), sem órfãos, sem tocar no
  `financeiro.db` real.

### Nota sobre o 1 skip

`test_fixas_avancado::test_aplicar_fixa_manual` pula quando não há fixa "aplicável".
Reproduz **isolado** (sem xdist, banco limpo) — é comportamento pré-existente do teste
condicional, mascarado na execução sequencial completa pela ordem dos arquivos
(`test_fixas.py` cria "Aluguel" com dia 15 antes). Não é regressão da paralelização.

### Próximos passos possíveis (não aplicados)

- Trocar sleeps fixos (`wait_for_load` 200ms, waits de 300ms–2s) por esperas condicionais
  (~40s de ganho, com risco controlado de flakiness).
- Investigar os picos de 4–51s no goto (antivírus/OneDrive sobre assets JS/CSS — fora do
  controle da suíte; o retry + timeout 60s já absorve).
