import sys

def run_windows_tray(on_exit_sync, app_url="http://localhost:8080"):
    """
    Ponto de entrada mantido com o mesmo nome para compatibilidade com o app.py.
    Roteia para a implementacao correta da bandeja de acordo com o sistema operacional.
    """
    if sys.platform == "win32":
        from financeiro.infrastructure.runtime.tray_win import run_win_tray
        run_win_tray(on_exit_sync, app_url)
    else:
        from financeiro.infrastructure.runtime.tray_mac import run_mac_tray
        run_mac_tray(on_exit_sync, app_url)
