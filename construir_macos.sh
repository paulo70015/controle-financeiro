#!/bin/bash
echo "============================================"
echo " Controle Financeiro - Gerador macOS (.app)"
echo "============================================"
echo ""

if [ -z "$1" ]; then
    echo "ERRO: Parametro obrigatorio nao fornecido!"
    echo "Escolha um modo de build:"
    echo "  ./construir_macos.sh --com-sqlite"
    echo "  ./construir_macos.sh --com-env-vazio"
    echo "  ./construir_macos.sh --com-env"
    exit 1
fi

INCLUIR_ENV=""
BUILD_MODE=""

for arg in "$@"; do
    if [ "$arg" == "--com-sqlite" ]; then
        INCLUIR_ENV=""
        BUILD_MODE="standalone-sqlite"
    elif [ "$arg" == "--com-env-vazio" ]; then
        INCLUIR_ENV=".env.example"
        BUILD_MODE="compartilhar-supabase"
    elif [ "$arg" == "--com-env" ]; then
        INCLUIR_ENV=".env"
        BUILD_MODE="pessoal-supabase"
    fi
done

cd "$(dirname "$0")"
PYTHON_CMD="python3"

# Monta flags de dados opcionais
ADD_DATA_ENV=""
if [ -n "$INCLUIR_ENV" ]; then
    echo "Preparando ambiente embutido..."
    cp "$INCLUIR_ENV" ".env_embutido"
    ADD_DATA_ENV="--add-data \"$INCLUIR_ENV:.\" --add-data \".env_embutido:\""
fi

echo "[1/3] Limpando build anterior..."
rm -rf build/ dist/ ControleFinanceiro.spec

echo "[2/3] Gerando pacote .app com PyInstaller..."
$PYTHON_CMD -m PyInstaller \
    --windowed \
    --noconfirm \
    --name "ControleFinanceiro" \
    --add-data "index.html:." \
    --add-data "partials:partials" \
    --add-data "static:static" \
    ${ADD_DATA_ENV:+--add-data "$INCLUIR_ENV:." --add-data ".env_embutido:."} \
    --hidden-import flask \
    --hidden-import pystray \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --hidden-import PIL.ImageDraw \
    --hidden-import postgrest \
    --hidden-import dotenv \
    --hidden-import supabase \
    --collect-submodules financeiro \
    app.py

[ -n "$INCLUIR_ENV" ] && rm -f ".env_embutido"

echo "[3/3] Configurando Info.plist para App de Bandeja (Tray)..."
PLIST_PATH="dist/ControleFinanceiro.app/Contents/Info.plist"

if [ -f "$PLIST_PATH" ]; then
    # A magia do macOS: Oculta o app do Dock e o transforma num background/tray app perfeito
    plutil -insert LSUIElement -bool true "$PLIST_PATH"
    plutil -insert NSHighResolutionCapable -bool true "$PLIST_PATH"
    echo "[OK] Info.plist ajustado com sucesso."
fi

echo ""
echo "================================================================"
echo " SUCESSO! Aplicativo gerado em: dist/ControleFinanceiro.app"
echo "================================================================"