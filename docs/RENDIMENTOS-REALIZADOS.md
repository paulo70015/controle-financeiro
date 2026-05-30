# Rendimentos Realizados

## Objetivo

Marcar automaticamente, na visao de **Rendimentos**, os meses que ja terminaram no **calendario real** usando o mesmo destaque visual verde (`pg-2`) ja existente em despesas pagas.

Nos rendimentos, esse status significa **realizado** ou **encerrado**.

## Regra de negocio

- **Ano passado:** meses `1..12` ficam realizados.
- **Ano atual:** meses anteriores ao mes atual ficam realizados.
- **Ano futuro:** nenhum mes fica realizado.
- A regra usa o **fim do mes real**, sem relacao com mes fiscal de cartao.
- O status e **persistido no banco**.

## Persistencia

Foi criada a tabela `rendimentos_realizados`, com granularidade por **ano + mes**:

```sql
CREATE TABLE IF NOT EXISTS rendimentos_realizados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ano, mes),
    FOREIGN KEY (ano) REFERENCES anos(ano) ON DELETE CASCADE
);
```

Versao Supabase/PostgreSQL:

```sql
CREATE TABLE IF NOT EXISTS rendimentos_realizados (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    data_alteracao TIMESTAMP DEFAULT NOW(),
    UNIQUE (ano, mes),
    FOREIGN KEY (ano) REFERENCES anos(ano) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rendimentos_realizados_ano_mes
    ON rendimentos_realizados(ano, mes);
```

## Carga automatica do status

Ao carregar `GET /api/dados/<ano>`, o backend sincroniza a tabela:

1. calcula quais meses devem estar realizados;
2. faz upsert dos meses obrigatorios com `status = 1`;
3. remove meses que nao devem mais estar marcados naquele ano.

## Payload do dashboard

O endpoint agregado `/api/dados/<ano>` passou a incluir:

```json
{
  "rendimentos_realizados": {
    "1": 1,
    "2": 1,
    "3": 1
  }
}
```

Convencao:

- chave = mes (`1..12`)
- valor `1` = mes realizado
- chave ausente = mes ainda em aberto

## Comportamento na UI Web

Na tela de rendimentos, o frontend aplica `pg-2`:

- na celula do local daquele mes;
- na linha **Aportes**;
- na linha **Rendimentos**;
- na linha **Saldo acumulado**.

Isso reaproveita o mesmo verde visual usado em despesas, mas com semantica de **mes encerrado**.

## Adaptacao para Flutter

Se o app Flutter usa a mesma base e uma grade mensal parecida, a adaptacao minima e:

### 1. Criar o modelo

```dart
class RendimentoRealizadoMes {
  final int ano;
  final int mes;
  final bool realizado;

  RendimentoRealizadoMes({
    required this.ano,
    required this.mes,
    required this.realizado,
  });

  factory RendimentoRealizadoMes.fromJson(Map<String, dynamic> json) {
    return RendimentoRealizadoMes(
      ano: json['ano'],
      mes: json['mes'],
      realizado: (json['status'] ?? 0) == 1,
    );
  }
}
```

### 2. Ler o campo agregado do dashboard

Se o Flutter consome `/api/dados/{ano}`, basta mapear:

```dart
final realizados = Map<int, int>.from(
  (json['rendimentos_realizados'] ?? {}).map(
    (key, value) => MapEntry(int.parse(key), value as int),
  ),
);

final mesRealizado = (realizados[mes] ?? 0) > 0;
```

### 3. Aplicar o destaque visual

Ao montar cada celula mensal de rendimentos:

```dart
Container(
  color: mesRealizado ? Colors.green.shade200 : null,
  child: ...
)
```

Ou, se houver tema proprio, usar a mesma cor/semantica ja utilizada para status equivalente no app.

## SQL de migracao para app Flutter

### SQLite

```sql
CREATE TABLE IF NOT EXISTS rendimentos_realizados (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (ano, mes),
    FOREIGN KEY (ano) REFERENCES anos(ano) ON DELETE CASCADE
);
```

### Supabase/PostgreSQL

```sql
CREATE TABLE IF NOT EXISTS rendimentos_realizados (
    id SERIAL PRIMARY KEY,
    ano INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    status INTEGER DEFAULT 0,
    data_alteracao TIMESTAMP DEFAULT NOW(),
    UNIQUE (ano, mes),
    FOREIGN KEY (ano) REFERENCES anos(ano) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rendimentos_realizados_ano_mes
    ON rendimentos_realizados(ano, mes);
```

## Observacoes importantes

- Nao reutilizar `pagamento_status`, porque o conceito aqui nao e pagamento por categoria, e sim **fechamento mensal da visao de rendimentos**.
- A chave correta e **ano + mes**, nao `local_id`.
- Se o Flutter tiver repositorio proprio para dashboard, ele deve devolver `rendimentos_realizados` junto com `rendimentos_locais` e `rendimentos`.
