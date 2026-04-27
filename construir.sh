#!/bin/bash
echo "============================================"
echo " Controle Financeiro - Gerador de Executavel"
echo " Linux / macOS (PyInstaller)"
echo "============================================"
echo ""

# Verificar se parametro foi fornecido
if [ -z "$1" ]; then
    echo "ERRO: Parametro obrigatorio nao fornecido!"
    echo ""
    echo "Escolha um modo de build:"
    echo ""
    echo "  ./construir.sh --com-sqlite"
    echo "    > Modo STANDALONE com SQLite local"
    echo "    > Funciona imediatamente, sem configuracao"
    echo "    > Ideal para compartilhar"
    echo "    > Cada usuario tem seu proprio banco local"
    echo ""
    echo "  ./construir.sh --com-env-vazio"
    echo "    > Modo Supabase SEM credenciais"
    echo "    > Usuario precisa criar .env com suas credenciais"
    echo "    > Ideal para compartilhar quando quer que cada um use seu Supabase"
    echo ""
    echo "  ./construir.sh --com-env"
    echo "    > Modo Supabase COM suas credenciais embutidas"
    echo "    > NAO compartilhe - acessa SEU banco Supabase"
    echo "    > Ideal para uso pessoal em outro computador"
    echo ""
    echo "  Opcoes adicionais:"
    echo "    --log   Forca o modo console para exibir erros no terminal"
    echo ""
    exit 1
fi

# Processar parametro
INCLUIR_ENV=""
BUILD_MODE=""
DEBUG_FLAG="--noconsole"

for arg in "$@"; do
    if [ "$arg" == "--com-sqlite" ]; then
        INCLUIR_ENV=".env.sqlite"
        BUILD_MODE="standalone-sqlite"
        echo "[INFO] Build STANDALONE com SQLite - banco local embutido"
    elif [ "$arg" == "--com-env-vazio" ]; then
        INCLUIR_ENV=".env.example"
        BUILD_MODE="compartilhar-supabase"
        echo "[INFO] Build Supabase SEM credenciais - seguro para compartilhar"
    elif [ "$arg" == "--com-env" ]; then
        INCLUIR_ENV=".env"
        BUILD_MODE="pessoal-supabase"
        echo "[AVISO] Build com suas credenciais Supabase - NAO compartilhe!"
    elif [ "$arg" == "--log" ]; then
        DEBUG_FLAG="--console"
        echo "[INFO] Modo LOG ativado: O executavel exibira erros no terminal"
    fi
done

if [ -z "$BUILD_MODE" ]; then
    echo ""
    echo "ERRO: Parametro principal invalido ou nao fornecido!"
    echo "Use: --com-sqlite, --com-env-vazio ou --com-env"
    exit 1
fi
echo ""

# Diretorio do script
cd "$(dirname "$0")"

if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
else
    echo "ERRO: python3 nao encontrado!"
    echo "Instale com: sudo apt install python3 python3-pip  (Ubuntu/Debian)"
    echo "             brew install python                    (macOS)"
    exit 1
fi
echo "[OK] Python encontrado: $($PYTHON_CMD --version)"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    echo "AVISO: pip3 nao encontrado. Tentando instalar..."
    $PYTHON_CMD -m ensurepip --upgrade
fi

# Instalar dependencias de build
echo ""
echo "[1/3] Instalando dependencias de build..."
$PYTHON_CMD -m pip install --upgrade pip --quiet --break-system-packages
$PYTHON_CMD -m pip install pyinstaller flask supabase psycopg2-binary python-dotenv pystray pillow --quiet --break-system-packages
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao instalar dependencias."
    exit 1
fi
echo "[OK] Dependencias instaladas."

echo ""
echo "Preparando ambiente embutido..."
cp "$INCLUIR_ENV" ".env_embutido"

# Detectar separador de dados (Linux/Mac usam ":")
echo ""
echo "[2/3] Gerando executavel com PyInstaller..."

# Remover cache de build anterior que prende o noconsole
rm -rf build/ dist/ ControleFinanceiro.spec

$PYTHON_CMD -m PyInstaller \
    --onefile \
    $DEBUG_FLAG \
    --name "ControleFinanceiro" \
    --add-data "index.html:." \
    --add-data "partials:partials" \
    --add-data "static:static" \
    --add-data "$INCLUIR_ENV:." \
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

if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao gerar executavel."
    exit 1
fi
echo "[OK] Executavel gerado."

# Resultado
echo ""
echo "[3/3] Preparando pasta de distribuicao..."
if [ -f "dist/ControleFinanceiro" ]; then
    chmod +x dist/ControleFinanceiro
    echo "Executavel criado em: dist/ControleFinanceiro"
    echo ""
    if [ "$BUILD_MODE" == "pessoal-supabase" ]; then
        echo "========================================"
        echo "  ATENCAO: Executavel com suas credenciais!"
        echo "========================================"
        echo "NAO compartilhe este arquivo."
        echo "Ele acessa SEU banco Supabase diretamente."
        echo "Use apenas para uso pessoal."
    elif [ "$BUILD_MODE" == "standalone-sqlite" ]; then
        echo "========================================"
        echo "  SUCESSO: Executavel standalone criado!"
        echo "========================================"
        echo "Este executavel pode ser compartilhado."
        echo "Funciona imediatamente, sem configuracao."
        echo "Cada usuario tera seu proprio banco local."
        echo "O banco sera criado automaticamente na primeira execucao."
    elif [ "$BUILD_MODE" == "compartilhar-supabase" ]; then
        echo "========================================"
        echo "  SUCESSO: Executavel seguro criado!"
        echo "========================================"
        echo "Este executavel pode ser compartilhado."
        echo "O usuario precisara criar um arquivo .env com:"
        echo "  SUPABASE_URL=https://seu-projeto.supabase.co"
        echo "  SUPABASE_KEY=sua_chave_publica"
        echo ""
        echo "Use .env.example como modelo."
    fi
else
    echo "AVISO: Executavel nao encontrado em dist/"
fi

echo ""
echo "============================================"
echo " Build concluido!"
echo "============================================"
