"""
Módulo central de versionamento do Controle Financeiro Pessoal.

Versão base: 1.3.0
Build: timestamp DDMMAAHHMMSS gerado automaticamente a cada commit via hook.

Uso:
    from version import get_version, get_version_full, get_build

    get_version()       → "1.3.0"           (sem build)
    get_build()         → "120126143052"    (timestamp, ou "" se BUILD não existir)
    get_version_full()  → "v1.3.0-b120126143052"  (com build) ou "v1.3.0" (sem)
"""

import os
import sys

# Versão base do sistema (manual, alterada apenas em releases)
VERSION_BASE = "1.3.0"

# Caminho do arquivo BUILD_NUMBER (mesmo diretório que este módulo)
_BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
_BUILD_PATH = os.path.join(_BUILD_DIR, "BUILD_NUMBER")

# Em runtime PyInstaller, o BUILD_NUMBER pode estar em DATA_DIR (junto ao .exe)
if getattr(sys, 'frozen', False):
    _DATA_DIR = os.path.dirname(sys.executable)
    _ALT_BUILD = os.path.join(_DATA_DIR, "BUILD_NUMBER")
    if os.path.exists(_ALT_BUILD):
        _BUILD_PATH = _ALT_BUILD


def get_version() -> str:
    """Retorna a versão base (ex: '1.3.0')."""
    return VERSION_BASE


def get_build() -> str:
    """
    Retorna o número do build (timestamp DDMMAAHHMMSS).
    Retorna string vazia se o arquivo BUILD não existir.
    """
    try:
        with open(_BUILD_PATH, "r", encoding="utf-8") as f:
            build = f.read().strip()
            # Validação básica: 12 dígitos
            if len(build) == 12 and build.isdigit():
                return build
            return ""
    except (FileNotFoundError, PermissionError):
        return ""


def get_version_full() -> str:
    """
    Retorna a versão completa para exibição.
    Com build: 'v1.3.0-b120126143052'
    Sem build: 'v1.3.0'
    """
    build = get_build()
    if build:
        return f"v{VERSION_BASE}-b{build}"
    return f"v{VERSION_BASE}"


if __name__ == "__main__":
    print(f"Versão base : {get_version()}")
    print(f"Build       : {get_build() or '(não definido)'}")
    print(f"Completa    : {get_version_full()}")
