# Dados de entrada do ProfitRTD

## Situação no commit de origem do catálogo

O repositório não contém dados reais de mercado. Os arquivos brutos locais são grandes e permanecem fora do Git. O simulador atual recebe um único CSV por execução e não relaciona automaticamente arquivos separados de Negócios, Preços e Ofertas.

## Fontes locais conhecidas

| Fonte | Papel | Granularidade típica |
|---|---|---|
| Negócios | preço e quantidade efetivamente executados | evento/tick |
| Preços | atualizações de preços e estado da cotação | evento/tick |
| Ofertas | alterações do livro e quantidades ofertadas | evento/tick |
| VAP | volume financeiro ou quantidade por preço | agregado |
| Indicador Profit | OHLC e features calculadas pelo NTSL | barra/plot |

Pregões observados no workspace original: 16/09/2026, 28/09/2026, 21/10/2026, 26/10/2026 e 04/11/2026, além de capturas de indicadores posteriores. A nomenclatura do contrato pode refletir o contrato atual/futuro usado pelo Profit e não prova que o símbolo já existia na data histórica.

## Schema canônico proposto

Cada registro integrado deve ter:

- `timestamp_evento`: ISO 8601 com milissegundos;
- `sequencia_fonte`: desempate determinístico dentro do timestamp;
- `pregao` e `ativo_origem`;
- OHLC quando o registro for uma barra;
- último negócio, quantidade e número de negócios;
- bid, ask, quantidades do topo, spread;
- quantidades agregadas de compra e venda no book;
- agressão compradora, vendedora e saldo;
- idade em milissegundos de cada snapshot usado;
- flags de qualidade, lacuna e fonte ausente.

O contrato completo está em `schemas/dados_integrados_v1.schema.json`.

## Relacionamento temporal

1. Preserve a ordem original e a sequência de cada fonte.
2. Normalize timezone para `America/Sao_Paulo` sem descartar o timestamp original.
3. Use Negócios como eixo de eventos quando o objetivo for Tick a Tick.
4. Relacione Preços e Ofertas por junção temporal para trás (`as-of backward`): somente informação conhecida até o instante do negócio.
5. Registre a idade do snapshot. Não carregue book antigo através de uma lacuna sem marcar baixa qualidade.
6. Nunca faça junção com o evento futuro mais próximo.
7. Para barras, agregue somente depois da integração dos eventos.

## Validações obrigatórias

- timestamp inválido, ausente ou fora do pregão;
- duplicidade exata e conflito na mesma chave;
- inversão temporal;
- lacunas e reinício de sequência;
- preço fora da grade mínima do WIN;
- máxima/mínima incompatíveis com abertura/fechamento;
- spread negativo ou bid maior que ask;
- quantidade negativa;
- cobertura e idade de Preços/Ofertas em relação aos Negócios.

Os exemplos em `dados/exemplos` são sintéticos e existem somente para documentar o contrato.

## Inventário incremental

O utilitário `tools/inventariar_dados.py` lê somente CSVs novos ou alterados e mantém um registro JSON do que já foi processado. Ele informa tamanho, colunas, período, inversões temporais, timestamps consecutivos repetidos e lacunas acima de um limite configurável.

```powershell
python tools/inventariar_dados.py --origem C:\dados\ProfitRTD --saida inventario.csv --registro inventario.json --lacuna-segundos 5
```

Uma lacuna é apenas um alerta: em dados orientados a eventos, a ausência de negócios ou mudanças no book pode ser legítima.

## Integração disponível a partir da v0.13.0

O comando `integrar` recebe três CSVs **normalizados**, separados por ponto e vírgula.
Todas as fontes precisam de `timestamp_evento`, `sequencia_fonte`, `pregao` e `ativo_origem`.
O timestamp sem fuso é interpretado em America/Sao_Paulo. Use ISO 8601 com fuso na preparação dos dados para evitar ambiguidades.

| Fonte | Demais colunas |
|---|---|
| Negócios | `preco_ultimo`, `quantidade_negocio`. Opcionais em conjunto: `agressao_compra`, `agressao_venda`. |
| Preços | `preco_snapshot`. |
| Ofertas | `bid`, `ask`, `qtd_bid`, `qtd_ask`, `qtd_compra_book`, `qtd_venda_book`. |

```powershell
SimuladorCotacao-CLI.exe integrar --negocios negocios.csv --precos precos.csv --ofertas ofertas.csv --saida integrado.csv --idade-maxima-ms 1000 --lacuna-ms 5000
```

O integrador agrupa por ativo e pregão. Por padrão, um snapshot precisa ter timestamp estritamente anterior ao negócio.
Use `--sequencia-compartilhada` somente quando as três fontes tiverem uma mesma sequência causal. Nesse modo, um snapshot com
timestamp igual pode ser usado se sua sequência for menor ou igual. Duplicatas exatas são colapsadas e chaves conflitantes são rejeitadas.
As idades ficam registradas mesmo quando o snapshot é descartado por antiguidade. Após uma lacuna, o integrador exige
uma atualização posterior ao negócio que precedeu a lacuna. Campos sem cobertura ficam vazios.
A saída inclui um manifesto com hashes de origem e saída, versão, parâmetros e contagens de qualidade.
O replay aceita o formato **Eventos ProfitRTD integrados** e agrega os eventos causalmente em candles de um único ativo.
O topo do book do último negócio do candle só entra na avaliação de fechamento. Código que exige book sem cobertura recebe erro em vez de valores fictícios.
A exportação não reconstrói níveis individuais nem normaliza automaticamente arquivos RTD brutos fora do contrato.
