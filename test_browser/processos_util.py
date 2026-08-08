"""
Utilitários de infraestrutura para as suítes de teste (DRY).

- matar_servidores_na_porta(porta): mata órfãos ouvindo numa porta de teste
  (portas 8085/8086 são exclusivas das suítes — qualquer processo nelas é órfão).
- kill_arvore(proc): encerra um subprocesso e sua árvore (no Windows,
  proc.terminate() não mata o processo filho — usa taskkill /T /F).
- limpar_banco_teste(db_path): remove um banco de teste e derivados (bak, WAL/SHM),
  tolerando handles ainda abertos no Windows logo após taskkill /F.
"""

import os
import subprocess
import sys
from pathlib import Path


def limpar_banco_teste(db_path: Path):
    """Remove o banco de teste e derivados (bak/WAL/SHM).

    Não remove o diretório pai — o chamador decide (o setup recria o diretório
    antes de subir o servidor; o teardown pode remover o diretório vazio).
    """
    for p in (db_path, Path(str(db_path) + ".bak")):
        for suf in ("", "-wal", "-shm"):
            aux = Path(str(p) + suf)
            try:
                if aux.exists():
                    aux.unlink()
            except OSError:
                pass  # handle ainda aberto no Windows logo após taskkill /F


def matar_servidores_na_porta(porta: int):
    """Mata processos ouvindo na porta (órfãos de execuções anteriores)."""
    pids = set()
    try:
        if sys.platform == "win32":
            out = subprocess.run(
                ["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True, timeout=10
            ).stdout
            for linha in out.splitlines():
                partes = linha.split()
                # Coluna local (indice 1) termina em :PORTA e o estado e LISTENING;
                # endswith evita casar :80850..:80859.
                if len(partes) >= 5 and "LISTENING" in partes and partes[1].endswith(f":{porta}"):
                    pids.add(partes[-1])
        else:
            out = subprocess.run(
                ["lsof", "-ti", f"tcp:{porta}"], capture_output=True, text=True, timeout=10
            ).stdout
            pids = {p for p in out.split() if p.isdigit()}
    except (subprocess.SubprocessError, OSError):
        return

    for pid in pids:
        if pid == str(os.getpid()):
            continue
        try:
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/T", "/F", "/PID", pid], capture_output=True, timeout=10)
            else:
                os.kill(int(pid), 9)
            print(f"[testes] Orfao na porta {porta} morto (PID {pid})")
        except (subprocess.SubprocessError, OSError):
            pass


def kill_arvore(proc):
    """Mata o processo e sua árvore (no Windows, terminate não mata o filho)."""
    if sys.platform == "win32":
        try:
            r = subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True, timeout=10
            )
            if r.returncode == 0:
                return
        except (subprocess.SubprocessError, OSError):
            pass
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
