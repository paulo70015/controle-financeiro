"""Criacao do servidor HTTP com porta exclusiva.

No Windows, o ``SO_REUSEADDR`` que o socketserver/werkzeug liga por padrao
permite que DOIS processos facam bind na mesma porta ao mesmo tempo — o
resultado e duas instancias do app ativas, com requisicoes caindo
aleatoriamente em uma ou outra. Aqui o socket e criado manualmente com
``SO_EXCLUSIVEADDRUSE`` (Windows) para que a segunda instancia falhe no bind.
"""
import socket
import sys

from werkzeug.serving import ThreadedWSGIServer

HOST_PADRAO = "127.0.0.1"


class PortaEmUsoError(OSError):
    """A porta ja esta ocupada (provavelmente outra instancia do app)."""


def _criar_socket_exclusivo(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        if sys.platform == "win32":
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        else:
            # Em POSIX, SO_REUSEADDR so reaproveita TIME_WAIT; nao permite
            # dois listeners na mesma porta.
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(128)
    except OSError as e:
        sock.close()
        raise PortaEmUsoError(e.errno, f"Porta {port} ja esta em uso") from e
    return sock


def criar_servidor(flask_app, port, host=HOST_PADRAO):
    """Cria o servidor ja vinculado a porta. Levanta PortaEmUsoError se ocupada.

    O bind acontece de forma sincrona (na thread chamadora), entao o erro
    e detectado antes de abrir navegador/tray.
    """
    sock = _criar_socket_exclusivo(host, port)
    try:
        # fd=... faz o werkzeug reutilizar nosso socket (duplicado) sem novo bind
        return ThreadedWSGIServer(host, port, flask_app, fd=sock.fileno())
    finally:
        sock.close()
