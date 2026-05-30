# Copilot Instructions

## Commands

### Install dependencies
```bash
python -m pip install -r requirements.txt
```

### Run the app locally
```bash
# macOS/Linux
./iniciar_log.sh

# direct Flask entrypoint
python app.py --show-console
```

### Build distributables
```bash
# Windows .exe
construir.bat --com-sqlite
construir.bat --com-env-vazio
construir.bat --com-env

# macOS .app
./construir_macos.sh --com-sqlite
./construir_macos.sh --com-env-vazio
./construir_macos.sh --com-env
```

### Test commands
```bash
# integration/API regression suite
python test_suite.py

# SQLite repository integrity
python test_sqlite_mode.py
python -m pytest test_sqlite_mode.py -k test_sqlite_repositories

# dependency compatibility checks
python test_dependencies_compatibility.py
python -m pytest test_dependencies_compatibility.py -k test_sqlite_mode

# Playwright E2E suite (runner forces DB_MODE=sqlite)
bash test_browser/rodar-testes.sh

# single E2E test or subset
bash test_browser/rodar-testes.sh -k test_criar_despesa_simples
bash test_browser/rodar-testes.sh test_browser/test_despesas.py
```

## High-level architecture

- `app.py` is the bootstrap: it resolves `BASE_DIR` vs `DATA_DIR` for PyInstaller, loads `.env` before importing the app modules, preserves an externally forced `DB_MODE`, and registers all Flask blueprints.
- The backend follows a simplified DDD split:
  - `financeiro/domain/` contains pure entities.
  - `financeiro/application/*/use_cases.py` contains business orchestration.
  - `financeiro/infrastructure/` contains repositories and runtime integrations.
  - `financeiro/interfaces/http/*_routes.py` exposes thin Flask blueprints.
- `financeiro/infrastructure/repository_factory.py` is the switchboard between SQLite and Supabase. Most backend features have twin repositories in `financeiro/infrastructure/sqlite/` and `financeiro/infrastructure/supabase/`; changes that affect persistence usually need both implementations.
- The home page is server-rendered only as a shell: `financeiro/interfaces/http/home_routes.py` renders `index.html`, injects `window.CF_BOOT`, and the SPA takes over from there.
- `static/js/app-main.js` is the frontend bootstrap and shared state holder (`ano`, `dados`, `viewAtiva`). It fetches `/api/dados/<ano>`, then re-renders either the **Despesas** or **Rendimentos** view.
- `financeiro/interfaces/http/dashboard_routes.py` + `financeiro/application/dashboard/use_cases.py` provide the aggregate `/api/dados/<ano>` payload that drives most reloads in the SPA.
- Frontend scripts are plain browser scripts loaded in `index.html`, not ES modules. Files under `static/js/modules/` communicate through globals exposed by `app-main.js` and `window.*` helper functions.

## Key repository conventions

- Treat `AGENTS.md`, `.kiro/steering/project-context.md`, and `.kiro/steering/conventions.md` as the primary instruction sources before changing code.
- Keep user-facing labels, alerts, and messages in **PT-BR**.
- Do not introduce frontend frameworks or external UI libraries; this codebase stays on HTML/CSS/JavaScript Vanilla.
- Keep DDD boundaries strict: routes parse requests and return JSON, use cases own business rules, repositories own persistence details.
- For backend features, follow the repo's standard flow: repository method -> use case -> Flask route -> `static/js/modules/` integration.
- Do not rename existing database tables or columns unless explicitly required.
- Preserve PyInstaller behavior: writes must go to runtime data locations, never to files served from `BASE_DIR`.
- Never run validation against a live Supabase environment by default. Tests and scripted validation should force `DB_MODE=sqlite`, and the Playwright runner already aborts if Supabase appears active.
- `sessionStorage('cfViewAtiva')` controls the active top-level view. Switching between **Despesas** and **Rendimentos** rebuilds the DOM for that view.
- `app-main.js` should stay relatively thin; feature-specific behavior belongs in `static/js/modules/*.js`, domain helpers in `static/js/domain/`, and shared calculation logic in `static/js/application/`.
- Always null-check DOM elements before attaching listeners or mutating them.
- Detail modals use **lazy commit**: local delete/undo queues are accumulated in the modal and only persisted when the modal closes.
- `load()` requests are protected against race conditions with sequential IDs, and heavy UI transitions intentionally wait a few milliseconds so the loader/opacity change paints before a full rerender.
- Critical business rules to preserve:
  - removing a fixed expense for one month creates an entry in `fixas_excecoes` instead of deleting the recurring item;
  - payment status belongs to the `(ano, mes, categoria)` cell, not to an individual expense row;
  - rendimentos use accumulated balance: `Saldo(N) = Saldo(N-1) + Aporte(N) + Rendimento(N)`;
  - when duplicating/editing across years, remap `cat_id` to the matching category in the target year.
- Schema changes must also update `.kiro/docs/migracao-supabase/MIGRACAO-APP-FLUTTER.md` so the Flutter-side contract stays aligned.
- The repo has a Git hook in `.githooks/pre-commit` that regenerates `BUILD_NUMBER` during commits; avoid overwriting that workflow.
