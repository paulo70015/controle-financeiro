# 📖 Regras de Negócio — Controle Financeiro Pessoal v1.3.0

> **Framework Diátaxis:** Este documento atua como **Explanation** (compreensão profunda dos conceitos, motivações e modelos mentais do sistema) e **Reference** (especificação técnica exata de fórmulas, transições de estado, comportamentos de banco e restrições).

---

## 1. Visão Geral e Arquitetura do Domínio

O Controle Financeiro Pessoal é estruturado sobre duas premissas centrais:

1. **Duas Visões Independentes (Dual-View):**
   - **Visão de Despesas:** Foco no fluxo de caixa diário, despesas categorizadas, compras de cartão de crédito, despesas fixas recorrentes, receitas mensais, contas bancárias e metas.
   - **Visão de Rendimentos:** Foco na consolidação de patrimônio líquido, investimentos, aportes, saques, rendimentos nominais e projeções de rendimento a juros compostos.
   - A alternância entre essas visões é controlada via `sessionStorage('viewAtiva')`, garantindo isolamento de contexto no frontend sem misturar as preocupações contábeis.

2. **Particionamento Temporal por Ano:**
   - Categorias, despesas fixas e locais de investimento pertencem a um ano específico.
   - Contas correntes e metas possuem ciclo de vida contínuo (transcendem os anos individuais).
   - O ano de referência do dashboard é isolado: operações em um ano não contaminam dados de outros anos sem comandos explícitos de duplicação.

---

## 2. Despesas, Categorias e Ciclo Fiscal

### 2.1. Categorias
As categorias agrupam os gastos do ano na tabela de despesas.
- **`inclui_fixas`:** Categoria especial (normalmente uma por ano) que agrega automaticamente despesas fixas órfãs que não possuam `cat_id` explicitamente atribuído.
- **`conta_vinculada_id`:** Quando preenchido com o ID de uma conta corrente, cada despesa lançada nesta categoria cria automaticamente um lançamento de débito correspondente em `depositos_conta`.
- **`is_cartao`:** Identifica que a categoria representa um cartão de crédito. Altera o comportamento visual e operacional para compatibilidade com faturas fechadas e compras parceladas.

---

### 2.2. Despesas Fixas e Exceções Mensais
As despesas fixas (`despesas_fixas_cartao`) representam gastos previsíveis e recorrentes vinculados a um ano e opcionalmente a uma categoria (`cat_id`).

#### A Regra de Ouro: Fatura de Cartão vs. Despesas Fixas (Commit `93d93e3`)
> [!IMPORTANT]
> **Despesas fixas que entram na fatura do cartão já estão somadas nela.**
> Quando o usuário lança o valor de uma fatura de cartão de crédito (ex.: `R$ 4.177,84`) como despesa manual, esse montante **já contém** as despesas fixas daquele cartão (ex.: assinaturas, serviços recorrentes).
> 
> - Nesse cenário, as despesas fixas são registradas em `fixas_excecoes` para aquele mês.
> - No modal de detalhes, elas são apresentadas com estilo riscado: **`Despesas Fixas (Removidas)`**.
> - **O valor das fixas NÃO é somado novamente ao total da célula nem ao cabeçalho do modal.**
> - A linha de texto sintética interna (`"Soma das Despesas Fixas\u200b"`) é mantida no banco para integridade física/histórica, mas é estritamente ocultada e subtraída dos agregados para **nunca gerar contagem dupla**.

#### Ciclo de Vida da Fixa
- **Fixas Ativas:** Fixas cujo dia de vencimento ainda não ocorreu no ciclo de competência vigente.
- **Fixas Expiradas/Aplicadas:** Fixas cujo dia já passou no ciclo vigente. São consideradas aplicadas na fatura/gastos do mês.
- **Fixas Manuais (`fixas_aplicadas_manual`):** Permite ao usuário forçar a aplicação antecipada ou postergada de uma fixa para um mês específico via checkbox de conferência.
- **Exclusão de Fixa por Mês (`fixas_excecoes`):** Ao remover uma fixa em determinado mês, o registro mestre da fixa no ano **não** é apagado; em vez disso, é inserido um par `(ano, mes, cat_id)` na tabela `fixas_excecoes`.

#### Mês Fiscal Customizado (`dia_inicio_mes_fiscal`)
O usuário pode configurar o dia de corte fiscal (padrão: 25).
- Se `dia_atual >= dia_inicio_mes_fiscal`, a competência fiscal já aponta para o fechamento seguinte.
- O cálculo no backend (`_is_fixa_expirada`) e no frontend (`isFixaExpirada`) segue rigorosamente o dia configurado, garantindo que o vencimento das fixas respeite a data de fechamento da fatura e não o dia 31 do calendário civil.

---

### 2.3. Cartão de Crédito e Despesas Ignoradas (`ignorar_total`)
Permite registrar as compras individuais do cartão para conferência e histórico, sem distorcer o fluxo de caixa:
- **Flag `ignorar_total = 1`:** A despesa é gravada na tabela `despesas`, exibe o ícone de cartão 💳 no modal de detalhes, mas seu valor **não é somado no total da categoria no dashboard**, nem no somatório do cabeçalho do modal, nem na exportação CSV.
- **Blindagem de Conta Corrente:** Despesas marcadas com `ignorar_total = 1` **nunca** geram lançamentos automáticos de débito em `depositos_conta`, impedindo que a conta corrente sofra saídas antes do pagamento efetivo da fatura consolidada.

---

### 2.4. Status de Pagamento
O status de pagamento é uma entidade relacional própria (`pagamento_status`).

- **Escopo:** O status pertence à **célula bidimensional `(ano, mes, categoria)`**, e **não** a um lançamento de despesa individual.
- **Valores possíveis:**
  - `0`: Aberto / Não Pago (sem cor de destaque).
  - `1`: Pendente (destaque em amarelo).
  - `2`: Pago (destaque em verde).
- **Materialização Atômica ao Pagar:**
  - Ao transitar uma célula de `0` para `> 0`, o sistema materializa as fixas ativas pendentes daquela categoria criando a linha física `"Soma das Despesas Fixas\u200b"` e gerando o débito correspondente na conta vinculada (se houver).
  - Ao retornar a célula para `0`, a linha sintética materializada e seus débitos bancários vinculados são excluídos atomicamente.
- **Integridade Referencial:** A exclusão de uma categoria no ano remove em cascata todos os registros correspondentes em `pagamento_status`, eliminando células órfãs.

---

## 3. Rendimentos e Consolidação de Patrimônio

### 3.1. Saldo Acumulado
O patrimônio em cada local de rendimento é estritamente cumulativo ao longo dos 12 meses do ano:

$$\text{Saldo}(m) = \text{Saldo}(m-1) + \text{Aporte}(m) - \text{Saque}(m) + \text{Rendimento}(m)$$

- **`Saldo(0)`:** Saldo final herdado do mês 12 do ano anterior (quando houver transição) ou zero.
- **Prejuízos / Rendimentos Negativos:** O sistema suporta rendimentos reais negativos (desvalorização de ativos). Valores negativos reduzem o saldo e são destacados visualmente em vermelho.

---

### 3.2. Normalização Canônica de Sinais (Commit `a93a2a2`)
Para evitar erros humanos no lançamento:
- **Aporte:** Sempre representa acréscimo de capital. Se o usuário digitar um aporte com valor negativo, o backend normaliza automaticamente o tipo para `saque` com valor absoluto positivo.
- **Saque:** Sempre representa retirada de capital. O valor armazenado no banco é estritamente positivo ($> 0$), mas sua exibição no modal e nas tabelas é prefixada com sinal de menos (`-R$ 2.700,00`).

---

### 3.3. Lançamento por Diferença (Saldo Final Informado)
Ao receber o extrato do banco ou corretora, o investidor frequentemente possui apenas o **saldo final consolidado** daquele mês.
A função de diferença calcula o rendimento líquido real expurgando os aportes e retiradas do próprio mês:

$$\text{Rendimento Líquido} = \text{Valor Final Informado} - \text{Saldo Base Anterior} - \text{Aportes}(m) + \text{Saques}(m) - \text{Outros Rendimentos do Mês}$$

---

### 3.4. Projeções e Rendimentos Realizados
- **Taxa de Projeção (`projecao_taxa`):** Percentual mensal configurável por local de investimento (ex.: `0,85%`).
- **Condição de Projeção:** A projeção só é calculada para um mês se:
  1. A taxa de projeção for maior que zero;
  2. Não houver nenhum rendimento real já lançado no mês (`qtd_rendimentos == 0`);
  3. O saldo acumulado daquele ponto for positivo ($> 0$).
- **Saldo Total vs. Saldo Realizado (Commit `41eb2d4`):**
  - **Saldo Total:** Considera o saldo acumulado incluindo as projeções futuras até o final do ano.
  - **Saldo sem Projeções (Realizado):** Considera estritamente o patrimônio concretizado (aportes, saques e rendimentos de fato lançados), permitindo ao investidor enxergar sua posição real atual sem especulação.

---

### 3.5. Reflexo Automático em Conta Vinculada (Visão B)
Locais de rendimento podem ser vinculados a uma conta corrente (`conta_vinculada_id`).

A arquitetura adota a **Visão B (Conta Corrente = Patrimônio Total)**:
- **Aporte:** Gera automaticamente uma movimentação na conta vinculada (`tipo = 'aporte'`), pois o dinheiro permanece sob a custódia patrimonial da entidade.
- **Rendimento:** Gera automaticamente uma movimentação na conta vinculada (`tipo = 'rendimento'`), representando riqueza nova adicionada.
- **Saque:** **Não reflete** na conta vinculada, pois o resgate de um investimento para a própria conta é uma conversão interna de ativos, evitando creditar o saldo duas vezes.
- **Chave Estrangeira de Reflexo (`rendimento_lancamento_id`):** Todas as movimentações geradas por rendimentos guardam o ID do lançamento de origem. Se o lançamento for editado ou apagado, a movimentação refletida na conta é atualizada ou excluída em cascata reversa.

---

## 4. Contas Bancárias e Movimentações

### 4.1. Composição do Saldo das Contas
O saldo de uma conta bancária é calculado de forma perpétua:

$$\text{Saldo Inicial do Ano}(A) = \text{Saldo Inicial de Cadastro} + \sum_{Ano < A} \text{Depósitos}(Ano) + \sum_{Ano < A} \text{Movimentações}(Ano)$$

Para cada mês $m$ (1 a 12) do ano vigente:
$$\text{Saldo}(m) = \text{Saldo}(m-1) + \text{Total Depósitos}(m) + \text{Total Movimentações}(m)$$

---

### 4.2. Tipos de Movimentações Mensais
A tabela `movimentacoes_mensais` suporta três modalidades:
1. **`entrada`:** Créditos na conta (ex.: receitas manuais, saques de rendimentos externos).
2. **`saida`:** Débitos na conta (ex.: despesas avulsas, taxas bancárias).
3. **`outro` (Commit `297c1e1`):** Usado para **ajuste direto e conciliação de saldo**, permitindo retificar o saldo bancário da conta sem categorizar incorretamente como receita ou despesa operacional.

---

### 4.3. Exclusão Mensal com Isolamento por Conta (BUG-21)
A rota `DELETE /api/movimentacao/<ano>/<mes>` exige ou aceita opcionalmente o parâmetro `?conta_id=X`.
- Se `conta_id` for fornecido: apaga **apenas** as movimentações daquela conta específica no mês.
- Se `conta_id` for omitido: mantém o comportamento legado de limpar o mês completo.

---

## 5. Metas e Planejamento

### 5.1. Independência de Ciclo de Anos (Commit `f0bbe8f`)
> [!NOTE]
> Metas financeiras são objetivos estratégicos que frequentemente atravessam múltiplos anos fiscais (ex.: "Comprar Carro até 2030").

- **Colunas Canônicas:** `ano_criacao` (ano de início) e `ano_meta` (ano alvo, opcional/nullable).
- **Sem FK para Anos:** A tabela `metas` **não possui chave estrangeira** para a tabela `anos`.
- **Regra de Visibilidade:** Uma meta aparece em um dashboard de ano $A$ se e somente se:
  $$\text{ano\_criacao} \le A \quad \text{E} \quad (\text{ano\_meta} \ge A \quad \text{OU} \quad \text{ano\_meta IS NULL})$$
- **Idempotência:** Criar, visualizar ou editar uma meta **nunca** insere registros na tabela `anos`.

---

## 6. Administração, Idempotência e Duplicação de Ano

### 6.1. Duplicação de Ano (`duplicate_year`)
Permite clonar a estrutura de um ano para o seguinte mantendo integridade total:
1. **Validação:** O ano de destino deve ser diferente do ano de origem e não pode conter dados prévios.
2. **Categorias:** São clonadas preservando `ordem`, `inclui_fixas`, `conta_vinculada_id`, `tooltip` e a flag `is_cartao`.
3. **Despesas Fixas com Remapeamento:** As fixas são recriadas no ano novo. Como o `cat_id` do ano anterior não existe no ano novo, o sistema busca a categoria de **mesmo nome** no ano destino e reatribui o `cat_id` correspondente.
4. **Despesas Manuais:** São clonadas preservando `mes`, `categoria`, `valor`, `nota` e `ignorar_total`. Compras com `ignorar_total = 1` não geram lançamentos em `depositos_conta`.
5. **Locais de Rendimento:** São clonados preservando `nome`, `ordem`, `conta_vinculada_id` e `projecao_taxa`.
6. **Desempenho no Supabase (Bulk Insert):** Inserções são executadas em lotes agrupados em vez de loops N+1 na rede.

---

### 6.2. Idempotência em Consultas de Leitura
Nenhum endpoint HTTP de método `GET` (como `/api/dados/<ano>`) deve executar operações de escrita no banco de dados. Anos só são criados explicitamente via `POST /api/ano` ou pela rotina de duplicação.

---

## 7. Importação, Exportação e Backup

### 7.1. Exportação e Importação CSV
- **Totais Fiéis:** A exportação de despesas aplica `SUM(CASE WHEN ignorar_total = 1 THEN 0 ELSE valor END)` para que o total do arquivo CSV bata rigorosamente com os valores do dashboard.
- **Blocos Canônicos:** O CSV organiza os dados em seções delimitadas: Categorias, Despesas, Fixas, Receitas, Metas, Contas, Movimentações, Locais de Rendimento e Rendimentos.

### 7.2. Backup e Restauração de Banco
- **Modo SQLite:** Download direto do arquivo binário `.db`.
- **Modo Supabase:** Exportação em formato de dump estruturado com ordenação obrigatória de restauração: tabelas independentes primeiro, depois `rendimentos_lancamentos`, e por último `movimentacoes_mensais` (com `rendimento_lancamento_id` mapeado).

---

## 8. Padrões de Interface (Frontend Vanilla JS)

### 8.1. Lazy Commit em Modais
Modais de detalhamento de células (despesas, movimentações, rendimentos) operam sob o padrão **Lazy Commit**:
- Adições, edições e exclusões realizadas dentro do modal alteram apenas variáveis e filas locais em memória (`deleteQueue`, `undoStack`).
- As requisições HTTP efetivas de escrita e deleção só são disparadas quando o usuário clica em **"Salvar e fechar"** ou fecha o modal.
- Isso permite a funcionalidade de **Desfazer (Undo)** ilimitada durante a sessão de edição.

### 8.2. Proteção Contra Race Conditions na UI
- Requisições assíncronas de atualização de dados (`load()`) utilizam contadores sequenciais de transação (`loadSeq`). Se uma requisição mais antiga responder depois de uma mais recente, sua resposta é descartada para evitar sobrescrita de estado visual.
- Salvamentos de configurações globais (`salvarCfgApp`) são estritamente assíncronos e aguardam (`await`) a persistência no backend antes de acionar o recarregamento dos dados.
