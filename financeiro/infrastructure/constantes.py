"""Constantes compartilhadas da aplicação (fonte única de verdade)."""

# Nomes abreviados dos meses (colunas de tabela e cabeçalhos de CSV)
MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

# Nomes completos dos meses (modais e template)
MESES_EXTENSO = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

# Nomes completos em minúsculo, sem acentos (detecção de cabeçalho em CSV)
NOMES_MESES_NORMALIZADOS = [
    "janeiro", "fevereiro", "marco", "abril", "maio", "junho",
    "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
]
