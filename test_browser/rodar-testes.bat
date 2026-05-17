@echo off
chcp 65001 > nul
REM Rodar testes E2E com Playwright (Windows)
REM Uso: rodar-testes.bat [opcoes do pytest]

cd /d "%~dp0"

REM ═══════════════════════════════════════════════════════════════════
REM FORCAR SQLite — os testes NUNCA devem tocar no Supabase
REM ═══════════════════════════════════════════════════════════════════
set DB_MODE=sqlite

echo [1/3] Verificando Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python nao encontrado. Instale Python 3.10+ e tente novamente.
    pause
    exit /b 1
)
python --version

echo.
echo [1/3] Verificando dependencias...
python -c "import pytest" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   Instalando pytest...
    python -m pip install pytest -q
)
python -c "import playwright" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   Instalando playwright...
    python -m pip install playwright -q
)

echo.
echo [2/3] Verificando navegador Chromium...
python -c "from playwright.sync_api import sync_playwright; sync_playwright().__enter__().chromium.launch(headless=True).close()" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   Instalando Chromium...
    python -m playwright install chromium
) else (
    echo   Chromium ja instalado.
)

echo.
echo [3/3] Executando testes em test_browser/...
echo.
cd /d "%~dp0.."
python -m pytest test_browser/ %* -v --tb=short
set EXIT_CODE=%ERRORLEVEL%
cd /d "%~dp0"

echo.
if %EXIT_CODE% EQU 0 (
    echo Todos os testes passaram!
) else (
    echo Alguns testes falharam (codigo: %EXIT_CODE%).
)
pause
exit /b %EXIT_CODE%
