#!/bin/bash
cd "$(dirname "$0")"

PYTHON_CMD=""
for cmd in python3.12 python3.11 python3.10 python3 python; do
    if command -v "$cmd" &>/dev/null; then
        if "$cmd" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' &>/dev/null; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    $PYTHON_CMD app.py
else
    echo "ERRO: Python 3.10 ou superior nao encontrado no PATH!"
    exit 1
fi
