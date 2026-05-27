"""Módulo central de versionamento do Controle Financeiro Pessoal."""

import argparse
import os
import re
import sys

# Versão base do sistema (alterada pela skill de commit conforme o impacto)
VERSION_BASE = "1.4.5"

# Caminho do arquivo BUILD_NUMBER (mesmo diretório que este módulo)
_BUILD_DIR = os.path.dirname(os.path.abspath(__file__))
_BUILD_PATH = os.path.join(_BUILD_DIR, "BUILD_NUMBER")

# Em runtime PyInstaller, o BUILD_NUMBER pode estar em DATA_DIR (junto ao .exe)
if getattr(sys, 'frozen', False):
    _DATA_DIR = os.path.dirname(sys.executable)
    _ALT_BUILD = os.path.join(_DATA_DIR, "BUILD_NUMBER")
    if os.path.exists(_ALT_BUILD):
        _BUILD_PATH = _ALT_BUILD

_VERSION_RE = re.compile(r'^VERSION_BASE = "(?P<version>\d+\.\d+\.\d+)"$', re.MULTILINE)
_BUMP_ALIASES = {
    "major": "major",
    "maior": "major",
    "grande": "major",
    "minor": "minor",
    "menor": "minor",
    "pequena": "minor",
    "patch": "patch",
    "fix": "patch",
    "correcao": "patch",
    "correção": "patch",
}


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
    Com build: 'v1.3.0-120126143052'
    Sem build: 'v1.3.0'
    """
    build = get_build()
    if build:
        return f"v{VERSION_BASE}-{build}"
    return f"v{VERSION_BASE}"


def _normalizar_bump(nivel: str) -> str:
    bump = _BUMP_ALIASES.get(nivel.strip().lower())
    if not bump:
        opcoes = ", ".join(sorted(_BUMP_ALIASES))
        raise ValueError(f"Nivel de versão inválido: {nivel}. Use: {opcoes}")
    return bump


def calcular_proxima_versao(version: str, nivel: str) -> str:
    """Calcula a próxima versão sem alterar arquivos."""
    major, minor, patch = (int(part) for part in version.split("."))
    bump = _normalizar_bump(nivel)

    if bump == "major":
        return f"{major + 1}.0.0"
    if bump == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def atualizar_versao_base(nivel: str, arquivo: str | None = None) -> tuple[str, str]:
    """Atualiza VERSION_BASE neste arquivo e retorna (versao_anterior, nova_versao)."""
    if getattr(sys, 'frozen', False):
        raise RuntimeError("Atualização de versão não é permitida no runtime PyInstaller.")

    version_file = arquivo or os.path.abspath(__file__)
    with open(version_file, "r", encoding="utf-8") as f:
        conteudo = f.read()

    match = _VERSION_RE.search(conteudo)
    if not match:
        raise RuntimeError("Não foi possível localizar VERSION_BASE em version.py.")

    versao_atual = match.group("version")
    nova_versao = calcular_proxima_versao(versao_atual, nivel)
    novo_conteudo = _VERSION_RE.sub(f'VERSION_BASE = "{nova_versao}"', conteudo, count=1)

    with open(version_file, "w", encoding="utf-8") as f:
        f.write(novo_conteudo)

    return versao_atual, nova_versao


def _main() -> int:
    parser = argparse.ArgumentParser(description="Exibe ou atualiza a versão do sistema.")
    bump_group = parser.add_mutually_exclusive_group()
    bump_group.add_argument(
        "--next",
        choices=sorted(_BUMP_ALIASES),
        help="Exibe a próxima versão sem alterar arquivos.",
    )
    bump_group.add_argument(
        "--bump",
        choices=sorted(_BUMP_ALIASES),
        help="Incrementa VERSION_BASE: major/grande, minor/pequena ou patch/correcao.",
    )
    args = parser.parse_args()

    if args.next:
        nova = calcular_proxima_versao(VERSION_BASE, args.next)
        print(f"{VERSION_BASE} -> {nova}")
        return 0

    if args.bump:
        anterior, nova = atualizar_versao_base(args.bump)
        print(f"[OK] Versão atualizada: {anterior} -> {nova}")
        return 0

    print(f"Versão base : {get_version()}")
    print(f"Build       : {get_build() or '(não definido)'}")
    print(f"Completa    : {get_version_full()}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
