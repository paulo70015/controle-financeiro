#!/bin/bash

# Muda para o diretorio onde o script esta localizado
cd "$(dirname "$0")/.."

PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "ERRO: Python 3.10 ou superior nao encontrado no PATH!"
    echo "O sistema requer Python >= 3.10 (devido a sintaxe de tipos, ex: dict | None)."
    read -p "Pressione [Enter] para sair..."
    exit 1
fi

echo "============================================"
echo " Controle Financeiro v1.3.0 (Supabase)"
echo " Log de inicializacao: $(date +'%d/%m/%Y %H:%M:%S')"
echo "============================================"
echo ""

echo "[1/4] Verificando Python..."
$PYTHON_CMD --version
echo "OK."
echo ""

echo "[2/4] Verificando dependencias..."
if ! $PYTHON_CMD -c "from importlib.metadata import version; print('Flask', version('flask'))" &>/dev/null; then
    echo "Flask nao encontrado. Instalando dependencias..."
    $PYTHON_CMD -m pip install -r requirements.txt --break-system-packages
    if [ $? -ne 0 ]; then
        echo "ERRO: Falha ao instalar dependencias."
        read -p "Pressione [Enter] para sair..."
        exit 1
    fi
fi
if ! $PYTHON_CMD -c "import supabase" &>/dev/null; then
    echo "Supabase nao encontrado. Instalando..."
    $PYTHON_CMD -m pip install supabase postgrest python-dotenv --break-system-packages
fi
if ! $PYTHON_CMD -c "import psycopg2" &>/dev/null; then
    echo "Psycopg2 nao encontrado. Instalando..."
    $PYTHON_CMD -m pip install psycopg2-binary --break-system-packages
fi
echo "OK."
echo ""

echo "[3/4] Verificando arquivos..."
for file in "app.py" "index.html"; do
    if [ ! -f "$file" ]; then
        echo "ERRO: $file nao encontrado na pasta $(pwd)"
        read -p "Pressione [Enter] para sair..."
        exit 1
    fi
    echo "$file ......... OK"
done

if [ ! -f ".env" ]; then
    echo "ERRO: .env nao encontrado na pasta $(pwd)"
    echo "Crie o arquivo .env com SUPABASE_URL e SUPABASE_KEY"
    read -p "Pressione [Enter] para sair..."
    exit 1
fi
echo ".env ........... OK"
echo ""

echo "[4/4] Iniciando servidor em http://localhost:8080"
echo ""
echo "============================================"
echo " LOGS DO SERVIDOR ABAIXO"
echo " Pressione Ctrl+C para encerrar"
echo "============================================"
echo ""

$PYTHON_CMD app.py --show-console "$@"

echo ""
echo "Servidor encerrado."
read -p "Pressione [Enter] para sair..."
