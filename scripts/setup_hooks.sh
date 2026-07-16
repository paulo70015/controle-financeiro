#!/usr/bin/env bash
# setup_hooks.sh - Instala os hooks Git do projeto
# Executar uma vez após clonar o repositório.

set -e

echo "============================================"
echo " Instalando hooks Git do projeto..."
echo "============================================"

git config core.hooksPath .githooks

echo ""
echo "[OK] Hooks instalados com sucesso!"
echo "Os hooks em .githooks/ serão executados a cada commit."
echo ""
