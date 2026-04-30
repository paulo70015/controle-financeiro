from datetime import datetime


def nome_arquivo_exportacao(nome_base: str, extensao: str) -> str:
    sufixo_data = datetime.now().strftime("_%d%m%Y")
    return f"{nome_base}{sufixo_data}.{extensao.lstrip('.')}"
