#!/usr/bin/env python3
"""
Gera o número de build baseado no timestamp atual (DDMMAAHHMMSS)
e escreve no arquivo BUILD_NUMBER na raiz do projeto.

Uso:
    python gerar_build.py          # gera BUILD_NUMBER com timestamp agora
    python gerar_build.py --print  # apenas exibe, não escreve
"""

import os
import sys
from datetime import datetime


def gerar_build_number() -> str:
    """Retorna o timestamp no formato DDMMAAHHMMSS."""
    agora = datetime.now()
    return agora.strftime("%d%m%y%H%M%S")


def main():
    build = gerar_build_number()

    if "--print" in sys.argv:
        print(build)
        return

    # Escreve no arquivo BUILD_NUMBER (raiz do projeto = mesmo dir que este script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    build_path = os.path.join(script_dir, "BUILD_NUMBER")

    with open(build_path, "w", encoding="utf-8") as f:
        f.write(build + "\n")

    print(f"[OK] Build gerado: {build} -> {build_path}")


if __name__ == "__main__":
    main()
