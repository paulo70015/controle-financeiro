# Contrato do Banco de Dados (Web & Flutter)

Este documento define as regras canônicas para a estrutura e evolução do banco de dados `financas.db`, garantindo a estabilidade entre a aplicação Web (Python/Flask) e o aplicativo mobile (Flutter).

## 1. Nomenclatura Canônica (Snake Case)
- **Proibido** renomear tabelas ou colunas em uso pelo app legado.
- O padrão real do banco utiliza `_` (snake_case). O Flutter deve mapear as chaves exatamente neste formato.
- **Tabelas/Colunas fixadas:** `rendimentos_locais`, `rendimentos_lancamentos`, `cat_id`, `local_id`, `ano_meta`, `ano_criacao`, `projecao_taxa`, `data_alteracao`.

## 2. Versionamento do Schema
- O arquivo `.db` atua como um contrato compartilhado.
- A tabela `config` deve sempre conter a chave `schema_version`.
- A aplicação Web é a **única responsável** por rodar migrações estruturais (`ALTER TABLE`).
- **Regra de Compatibilidade:** Novas colunas adicionadas devem ser obrigatoriamente `NULLABLE` ou possuir um `DEFAULT`. Remoções de colunas exigem auditoria prévia em ambos os clients.

## 3. Integridade e Exclusão (Cascade Controlado)
- A exclusão de entidades segue o modelo de **Cascade Controlado**.
- O backend (e o mobile) devem forçar a diretiva `PRAGMA foreign_keys = ON;` ao conectar no SQLite.
- Ao apagar um pai (ex: Local de Rendimento), os registros filhos devem ser apagados via `ON DELETE CASCADE` diretamente pelo banco, evitando quebras de referência nas views do Flutter.

## 4. Tipagem e Centralização da Verdade
- A aplicação Web centraliza a verdade absoluta sobre: Tipos, restrições `NOT NULL`, valores `DEFAULT`, Índices e `Foreign Keys`.
- Se o banco for recriado no mobile, o Flutter deve apenas espelhar estritamente estas tipagens.

## 5. Concorrência e Sincronização
- Como múltiplos clients gravam no mesmo arquivo físico, `data_alteracao` (em UTC) atua como referência temporal.
- **Safe Upload:** Antes de qualquer envio ao Google Drive, o serviço verificará o `modifiedTime` do arquivo remoto via HEAD request. Caso o arquivo remoto tenha sofrido modificação posterior ao último download local, o sistema bloqueará o upload preventivamente (evitando overwrite cego).