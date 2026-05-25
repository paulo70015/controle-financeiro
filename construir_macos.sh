#!/bin/bash
echo "============================================"
echo " Controle Financeiro - Gerador macOS (.app)"
echo "============================================"
echo ""

if [ -z "$1" ]; then
    echo "ERRO: Parametro obrigatorio nao fornecido!"
    echo "Escolha um modo de build:"
    echo "  ./construir_macos.sh --com-sqlite"
    echo "  ./construir_macos.sh --com-env"
    exit 1
fi

BUILD_MODE=""
SQLITE_MODE=false

for arg in "$@"; do
    if [ "$arg" == "--com-sqlite" ]; then
        BUILD_MODE="standalone-sqlite"
        SQLITE_MODE=true
    elif [ "$arg" == "--com-env" ]; then
        BUILD_MODE="pessoal-supabase"
        # Aceita .env ou ".env (1)" (nome gerado pelo Google Drive)
        if [ ! -f ".env" ] && [ ! -f ".env (1)" ]; then
            echo "ERRO: Nenhum arquivo .env encontrado!"
            echo "Crie um arquivo .env com SUPABASE_URL e SUPABASE_KEY."
            exit 1
        fi
    fi
done

cd "$(dirname "$0")"
PYTHON_CMD="python3"

# ═══════════════════════════════════════════════════════════════════
# Sempre gerar .env_embutido — sem condicionais, sem expansão bash
# que pode falhar com paths contendo espaços ou caracteres especiais
# ═══════════════════════════════════════════════════════════════════
echo "Preparando ambiente embutido..."
if [ "$SQLITE_MODE" = true ]; then
    echo "DB_MODE=sqlite" > ".env_embutido"
else
    # --com-env: copia o .env real (ou .env (1) do Google Drive)
    if [ -f ".env" ]; then
        cp ".env" ".env_embutido"
    elif [ -f ".env (1)" ]; then
        cp ".env (1)" ".env_embutido"
    fi
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
    --add-data ".env_embutido:." \
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

rm -f ".env_embutido"

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
