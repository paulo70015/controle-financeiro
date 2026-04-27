# 💰 Controle Financeiro Pessoal v1.3.0

Aplicativo de controle financeiro pessoal com interface web moderna.

## 🚀 Início Rápido

```bash
# Windows
iniciar_log.bat

# Linux/Mac
./iniciar_log.sh
```

## 📚 Documentação

Toda a documentação está organizada na pasta [`docs/`](docs/):

- **[COMECE-AQUI.txt](COMECE-AQUI.txt)** - Boas-vindas e primeiros passos
- **[LEIAME.txt](LEIAME.txt)** - Guia completo em português
- **[docs/INICIO-RAPIDO.md](docs/INICIO-RAPIDO.md)** - Setup em 5 minutos
- **[docs/FAQ.md](docs/FAQ.md)** - Perguntas frequentes
- **[docs/INDICE.md](docs/INDICE.md)** - Índice completo da documentação

## 📦 Gerar Executável

```bash
# Standalone SQLite (recomendado para compartilhar)
construir.bat --com-sqlite

# Supabase vazio (cada um cria conta)
construir.bat --com-env-vazio

# Pessoal (suas credenciais - não compartilhe)
construir.bat --com-env
```

Veja [docs/DISTRIBUICAO.md](docs/DISTRIBUICAO.md) para mais detalhes.

## 🛠️ Tecnologias

- **Backend:** Python 3.10+, Flask
- **Frontend:** HTML5, CSS3, JavaScript Vanilla
- **Banco:** SQLite (local) ou Supabase (nuvem)
- **Arquitetura:** DDD (Domain-Driven Design)

## 📄 Licença

MIT License - Veja [LICENSE](LICENSE) para detalhes.

---

**Documentação completa:** [`docs/`](docs/)
