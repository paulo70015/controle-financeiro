"""
Helper de paths para runtime - Suporta modo dev e PyInstaller
"""

import os
import sys


def get_base_dir() -> str:
    """
    Retorna o diretório base da aplicação.
    - PyInstaller: sys._MEIPASS (arquivos embutidos temporários)
    - Dev: diretório raiz do projeto
    """
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_data_dir() -> str:
    """
    Retorna o diretório de dados persistentes.
    - PyInstaller: pasta onde o .exe está rodando
    - Dev: diretório raiz do projeto
    """
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
