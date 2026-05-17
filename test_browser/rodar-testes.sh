#!/bin/bash
# Rodar testes E2E com Playwright (macOS / Linux)
# Uso: bash rodar-testes.sh [opcoes do pytest]
cd "$(dirname "$0")"

# ═══════════════════════════════════════════════════════════════════
# FORÇAR SQLite — os testes NUNCA devem tocar no Supabase
# ═══════════════════════════════════════════════════════════════════
export DB_MODE=sqlite

VERMELHO='\033[0;31m'
VERDE='\033[0;32m'
AZUL='\033[0;34m'
SEM_COR='\033[0m'

# Detectar Python 3.10+
PYTHON_CMD=""
for cmd in python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${VERMELHO}Python 3.10+ nao encontrado. Instale e tente novamente.${SEM_COR}"
    exit 1
fi

echo -e "${AZUL}Python detectado:${SEM_COR} $($PYTHON_CMD --version)"

# Instalar pytest e playwright se necessario
echo ""
echo -e "${AZUL}[1/3] Verificando dependencias...${SEM_COR}"
$PYTHON_CMD -c "import pytest" 2>/dev/null || {
    echo "  Instalando pytest..."
    $PYTHON_CMD -m pip install pytest --break-system-packages -q
}
$PYTHON_CMD -c "import playwright" 2>/dev/null || {
    echo "  Instalando playwright..."
    $PYTHON_CMD -m pip install playwright --break-system-packages -q
}

# Instalar Chromium se necessario
echo ""
echo -e "${AZUL}[2/3] Verificando navegador Chromium...${SEM_COR}"
$PYTHON_CMD -c "
from playwright.sync_api import sync_playwright
try:
    with sync_playwright() as p:
        p.chromium.launch(headless=True).close()
    print('  Chromium ja instalado.')
except Exception:
    print('  Instalando Chromium...')
    import subprocess, sys
    subprocess.run([sys.executable, '-m', 'playwright', 'install', 'chromium'], check=True)
" 2>/dev/null || $PYTHON_CMD -m playwright install chromium

# Rodar testes
echo ""
echo -e "${AZUL}[3/3] Executando testes em test_browser/...${SEM_COR}"
echo ""
cd ..  # Volta para raiz do projeto (conftest.py usa caminhos relativos)
$PYTHON_CMD -m pytest test_browser/ "$@" -v --tb=short
EXIT_CODE=$?
cd - > /dev/null

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${VERDE}Todos os testes passaram!${SEM_COR}"
else
    echo -e "${VERMELHO}Alguns testes falharam (codigo: $EXIT_CODE).${SEM_COR}"
fi
exit $EXIT_CODE
