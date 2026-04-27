import os
import webbrowser

def run_mac_tray(on_exit_sync, app_url="http://localhost:8080"):
    try:
        import pystray
        from pystray import MenuItem as item
        from PIL import Image, ImageDraw

        def create_image():
            img = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([1, 1, 30, 30], fill=(21, 101, 192, 255))
            draw.text((7, 9), "CF", fill=(255, 255, 255, 255))
            return img

        def on_open(icon, item):
            webbrowser.open(app_url)

        def on_exit(icon, item):
            icon.stop()
            on_exit_sync()
            os._exit(0)

        menu = (
            item('Abrir no Navegador', on_open, default=True),
            item('Fechar Aplicacao', on_exit)
        )
        icon = pystray.Icon("ControleFinanceiro", create_image(), "Controle Financeiro", menu)
        icon.run()
    except Exception as e:
        print(f"Erro no tray do Mac: {e}")