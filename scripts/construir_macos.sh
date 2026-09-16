#!/bin/bash
# Gera o pacote .app (macOS) do Controle Financeiro via PyInstaller.
#
# Uso:
#   ./construir_macos.sh --com-env         credenciais Supabase embutidas (NAO compartilhar)
#   ./construir_macos.sh --com-env-vazio   Supabase sem credenciais (seguro para compartilhar)
#   ./construir_macos.sh --com-sqlite      standalone com banco SQLite local
#
# Requer Python 3.10+ com as dependencias de requirements.txt instaladas.
# Sem venv: o script procura, nesta ordem, $PYTHON_CMD, python3.13, python3.12,
# python3.11, python3.10 e python3 (interpretadores globais do sistema).
set -euo pipefail

cd "$(dirname "$0")/.."

APP_NAME="ControleFinanceiro"
MODO=""
INCLUIR_ENV=""

mostrar_uso() {
    echo "Escolha um modo de build:"
    echo "  ./construir_macos.sh --com-sqlite"
    echo "  ./construir_macos.sh --com-env-vazio"
    echo "  ./construir_macos.sh --com-env"
}

if [ $# -eq 0 ]; then
    echo "ERRO: Parametro obrigatorio nao fornecido!"
    mostrar_uso
    exit 1
fi

NOVO_MODO=""
NOVO_ENV=""
for arg in "$@"; do
    case "$arg" in
        --com-sqlite)
            NOVO_MODO="standalone-sqlite"
            NOVO_ENV=""
            ;;
        --com-env-vazio)
            NOVO_MODO="compartilhar-supabase"
            NOVO_ENV=".env.example"
            ;;
        --com-env)
            NOVO_MODO="pessoal-supabase"
            NOVO_ENV=".env"
            ;;
        *)
            echo "ERRO: Parametro invalido: $arg"
            mostrar_uso
            exit 1
            ;;
    esac

    if [ -n "$MODO" ] && [ "$NOVO_MODO" != "$MODO" ]; then
        echo "ERRO: Escolha apenas um modo de build por vez."
        mostrar_uso
        exit 1
    fi

    MODO="$NOVO_MODO"
    INCLUIR_ENV="$NOVO_ENV"
done

# Descreve o motivo pelo qual um interpretador nao serve para o build.
# String vazia = interpretador valido (Python 3.10+ com PyInstaller).
motivo_rejeicao() {
    local cmd="$1"

    if [ ! -x "$cmd" ] && ! command -v "$cmd" >/dev/null 2>&1; then
        echo "nao encontrado"
        return
    fi

    if ! "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
        echo "versao $("$cmd" -c 'import platform; print(platform.python_version())' 2>/dev/null) (o projeto exige 3.10+)"
        return
    fi

    if ! "$cmd" -c 'import PyInstaller' >/dev/null 2>&1; then
        echo "PyInstaller nao instalado"
        return
    fi

    echo ""
}

# Monta a lista de candidatos e o primeiro que serve para o build.
# Preenche PYTHON_SELECIONADO (vazio se nenhum servir) e RELATORIO_PYTHON.
selecionar_python() {
    local cmd motivo
    local candidatos

    if [ -n "${PYTHON_CMD:-}" ]; then
        candidatos=("$PYTHON_CMD")
    else
        candidatos=(python3.13 python3.12 python3.11 python3.10 python3)
    fi

    PYTHON_SELECIONADO=""
    RELATORIO_PYTHON=""
    for cmd in "${candidatos[@]}"; do
        motivo="$(motivo_rejeicao "$cmd")"
        if [ -z "$motivo" ]; then
            PYTHON_SELECIONADO="$cmd"
            return 0
        fi
        RELATORIO_PYTHON="${RELATORIO_PYTHON}  - $cmd: $motivo
"
    done

    return 1
}

echo "============================================"
echo " Controle Financeiro - Gerador macOS (.app)"
echo "============================================"
echo ""

echo "[1/3] Verificando ambiente Python e limpando build anterior..."

if ! selecionar_python; then
    echo "ERRO: nenhum Python utilizavel para o build foi encontrado."
    echo "Interpretadores verificados:"
    printf '%s' "$RELATORIO_PYTHON"
    echo ""
    echo "Instale as dependencias no Python global (o projeto nao usa venv):"
    echo "  brew install python@3.12                                    (se nao tiver 3.10+)"
    echo "  python3.12 -m pip install --break-system-packages -r requirements.txt"
    echo ""
    echo "O --break-system-packages e' exigido pelo PEP 668: o Python do Homebrew"
    echo "marca o site-packages como 'externally managed'."
    exit 1
fi

PYTHON_CMD="$PYTHON_SELECIONADO"

echo "[OK] Interpretador: $("$PYTHON_CMD" -V 2>&1) ($PYTHON_CMD)"

# Gerar BUILD_NUMBER se nao existir (para que a versao exiba o build)
if [ ! -f "BUILD_NUMBER" ]; then
    echo "[INFO] BUILD_NUMBER nao encontrado, gerando..."
    "$PYTHON_CMD" gerar_build.py
fi

rm -rf build/ dist/ ControleFinanceiro.spec

echo "[2/3] Gerando pacote .app com PyInstaller..."

ADD_DATA_ENV=()
if [ -n "$INCLUIR_ENV" ]; then
    echo "Preparando ambiente embutido ($INCLUIR_ENV)..."
    cp "$INCLUIR_ENV" ".env_embutido"
    # O arquivo temporario nao pode sobrar nem quando o build falha.
    trap 'rm -f ".env_embutido"' EXIT
    ADD_DATA_ENV=(--add-data "$INCLUIR_ENV:." --add-data ".env_embutido:.")
fi

RC_BUILD=0
# ${ADD_DATA_ENV[@]+...} protege a expansao de array vazio no bash 3.2 (bash -u).
"$PYTHON_CMD" -m PyInstaller \
    --windowed \
    --noconfirm \
    --name "$APP_NAME" \
    --add-data "index.html:." \
    --add-data "partials:partials" \
    --add-data "static:static" \
    ${ADD_DATA_ENV[@]+"${ADD_DATA_ENV[@]}"} \
    --add-data "BUILD_NUMBER:." \
    --hidden-import flask \
    --hidden-import pystray \
    --hidden-import PIL \
    --hidden-import PIL.Image \
    --hidden-import PIL.ImageDraw \
    --hidden-import PIL.ImageFont \
    --hidden-import postgrest \
    --hidden-import dotenv \
    --hidden-import supabase \
    --collect-submodules financeiro \
    app.py || RC_BUILD=$?

if [ "$RC_BUILD" -ne 0 ]; then
    echo ""
    echo "ERRO: PyInstaller falhou (codigo $RC_BUILD). O .app NAO foi gerado."
    exit 1
fi

echo "[3/3] Configurando Info.plist para App de Bandeja (Tray)..."
PLIST_PATH="dist/$APP_NAME.app/Contents/Info.plist"
EXEC_PATH="dist/$APP_NAME.app/Contents/MacOS/$APP_NAME"

if [ ! -f "$PLIST_PATH" ] || [ ! -x "$EXEC_PATH" ]; then
    echo ""
    echo "ERRO: o PyInstaller nao gerou o pacote esperado em dist/$APP_NAME.app."
    exit 1
fi

# Idempotente: o PyInstaller ja cria NSHighResolutionCapable no Info.plist,
# e plutil -insert falha em chave existente.
definir_plist_booleano() {
    plutil -remove "$1" "$PLIST_PATH" >/dev/null 2>&1 || true
    plutil -insert "$1" -bool true "$PLIST_PATH"
}

# A magia do macOS: Oculta o app do Dock e o transforma num background/tray app perfeito
definir_plist_booleano LSUIElement
definir_plist_booleano NSHighResolutionCapable
echo "[OK] Info.plist ajustado com sucesso."

echo ""
echo "[LIMPEZA] Removendo arquivos temporarios..."
rm -rf build/ ControleFinanceiro.spec controlefinanceiro.log dist/controlefinanceiro.log
echo "[OK] Apenas o .app em dist/ foi mantido."

echo ""
echo "================================================================"
echo " SUCESSO! Aplicativo gerado em: dist/$APP_NAME.app"
case "$MODO" in
    pessoal-supabase)
        echo " ATENCAO: credenciais do Supabase embutidas no app."
        echo " NAO compartilhe este arquivo."
        ;;
    compartilhar-supabase)
        echo " Para conectar no Supabase, crie o arquivo:"
        echo "   dist/$APP_NAME.app/Contents/MacOS/.env"
        echo " com SUPABASE_URL e SUPABASE_KEY (use .env.example como modelo)."
        ;;
    standalone-sqlite)
        echo " Banco SQLite local criado automaticamente na primeira execucao."
        echo " Pode ser compartilhado."
        ;;
esac
echo "================================================================"
