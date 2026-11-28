# Etapa 2A — diagnóstico da proteção em 26/10/2026

Referências: matriz de 26/10 no commit `1318a0e27157127f8b418f346d2eaf8ade095325` e logs publicados no commit `0df2ebe9be10057f4d0520e22d60cc7616131244`. O recorte permanece WINZ26, 26/10/2026, v5.7 original, um contrato, candles OHLC de um minuto e custos e slippage zerados. Não houve ajuste dos parâmetros da estratégia.

## Fontes e limites

O arquivo principal é [`logs_paridade/paridade_console_varios_dias.csv.gz`](logs_paridade/paridade_console_varios_dias.csv.gz). Ele foi lido diretamente com `gzip.open(..., "rt", encoding="utf-8-sig", newline="")` e `csv.DictReader(..., delimiter=";")`. Foram confirmadas 30.155 mensagens e o SHA-256 `8c02666ff28d4467d5764efb1d4702ac23ebe595a47718d9dd0c66214a9d8cd0` do conteúdo descompactado.

Para evitar somar capturas sobrepostas, a análise usa apenas `Texto colado (2).txt`, bloco 4, linhas 3542–3552. A ordem de `linha` foi preservada. As linhas 3543–3546 registram, sob a avaliação 13:03, solicitação de compra, posição observada +1 a 177.565, alvo 178.015 e stop 177.215/177.210. A linha 3547 registra posição zerada às 13:04; as linhas 3548–3551 iniciam o segundo ciclo, e a linha 3552 registra nova zeragem às 13:05. Outros blocos e a outra origem repetem esse trecho e não foram contados novamente.

As exportações privadas de barras, indicadores e operações permanecem no Windows. O relatório de operações registra a primeira compra e a saída às 13:04, respectivamente a 177.565 e 177.215. O relógio de avaliação do console e o relógio de execução do relatório são mantidos em colunas conceitualmente distintas; não foi aplicado deslocamento global de um minuto.

O console prova o estado visível ao NTSL e a solicitação de proteção, mas não prova aceitação, disparo, cancelamento OCO nem a ordem dos negócios dentro do minuto. OHLC também não contém a sequência intrabar.

## Rastreamento no motor antes da correção

O novo modo `--rastrear-ordens` grava `eventos_ordens.csv` com solicitação, primeira barra elegível, posição vista na avaliação NTSL, gatilho e preenchimento. No cenário congelado:

| Etapa | Rótulo da barra do motor | Evidência |
|---|---|---|
| sinal e solicitação de entrada | 13:03 | `BuyAtMarket(1)` solicitada, primeira barra elegível 13:04 |
| preenchimento da entrada | 13:04 | abertura 177.565, posição +1 |
| posição visível e reavaliação NTSL | 13:04 | NTSL vê +1 e preço médio 177.565 |
| solicitação de proteção | 13:04 | alvo 178.015 e stop 177.215/177.210 |
| primeira barra elegível do stop | 13:05 | regra anterior adiava toda ordem nova para a barra seguinte |
| disparo | 13:05 | abertura 176.815, já abaixo de gatilho e limite |
| preenchimento | 14:01 | retorno ao limite 177.210 |

Assim, a primeira divergência demonstrada está entre **solicitação da proteção** e **primeira barra elegível**. Entrada, posição vista pelo NTSL e preços da proteção já coincidiam.

## Teste sintético e menor correção

O teste `test_protecao_no_candle_da_entrada_e_opt_in` cria uma entrada a mercado em 100 e uma barra de entrada que cruza o stop 95. No comportamento padrão, a proteção só pode preencher na barra seguinte. Com `protecao_no_candle_entrada`, alvo e stop enviados na primeira avaliação posicionada tornam-se elegíveis na própria barra da entrada e o stop preenche em 95.

O teste independente `test_stop_limit_ja_ativo_nao_depende_da_nova_regra` deixa a proteção ativa antes do cruzamento. Os dois modos preenchem o mesmo stop no mesmo preço e barra. Isso separa a elegibilidade da proteção da regra OHLC de stop-limit. O teste já existente de gap através do limite continua cobrindo o caso em que o stop dispara, mas não pode preencher abaixo do limite.

A menor alteração foi uma regra de execução OHLC **opt-in**, `protecao_no_candle_entrada`, desativada por padrão. Ela não altera a v5.7 nem o comportamento dos demais usuários. Quando uma entrada a mercado é preenchida no início da barra e a avaliação posicionada envia alvo/stop, somente essas proteções são reavaliadas no OHLC da barra. Como essa avaliação reutiliza o OHLC inteiro, o resultado continua indeterminado quando alvo e stop, ou eventos anteriores e posteriores à entrada, não podem ser ordenados sem negócios intrabar.

### Correção de escopo após revisão

A revisão do SHA `ef66db0c2365602273e9c4e27fd05deb077bf44a` mostrou que a primeira implementação selecionava qualquer saída nova e chamava a segunda passagem para todas as ordens elegíveis. Isso poderia preencher retroativamente na abertura uma saída a mercado decidida com o fechamento, aplicar a hipótese a uma entrada limite/stop ocorrida no meio da barra ou reprocessar uma ordem antiga já disparada.

O escopo corrigido exige simultaneamente: posição anterior igual a zero; abertura da posição por preenchimento de entrada `market` na passagem inicial; proteção enviada nessa mesma avaliação; lado de saída compatível com a posição; e tipo `limit` ou `stop`. A segunda passagem recebe somente as chaves dessas proteções. Saídas a mercado, entradas limite/stop, ordens antigas e quaisquer outras ordens preservam sua elegibilidade original.

As regressões cobrem: saída a mercado motivada pelo fechamento; entrada limite e entrada stop; ordem antiga já disparada; gap através do limite; e alvo e stop tocados na mesma barra. Uma decisão baseada no fechamento não é preenchida retroativamente na abertura.

A hipótese OHLC continua restrita. Para uma entrada a mercado preenchida na abertura, alvo e stop calculados imediatamente a partir do preço de entrada podem usar a máxima e a mínima posteriores. Se o nível da proteção usar `Close`, máxima, mínima ou outro dado que só fique definitivo no fechamento, testar esse nível contra toda a barra incorpora informação futura e o resultado deve ser marcado como indeterminado. Quando alvo e stop são tocados na mesma barra, o motor mantém o desfecho adverso e registra uma ambiguidade; o caminho real exige negócios intrabar.

## Resultados antes e depois

| Pregão | Profit | Motor antes | Exatas antes | Motor depois | Exatas depois | Primeira pendência depois |
|---|---:|---:|---:|---:|---:|---|
| 21/10 | 10 | 10 | 10 | 10 | 10 | nenhuma operação divergente |
| 26/10 | 12 | 10 | 8 | 11 | 11 | segunda compra 13:05, 176.815 → 176.465 |

Após a correção de escopo, a repetição com a v5.7 original manteve exatamente esses resultados: 10/10 em 21/10 e 11 correspondências entre as 11 operações do motor e as 12 do Profit em 26/10. O primeiro stop permaneceu 177.215 às 13:04. Portanto, a correção eliminou os efeitos retroativos possíveis sem mudar os dois cenários controlados.

Em 26/10, a compra 177.565 → 177.215 passa a coincidir exatamente. A operação de controle 14:04–14:06, 177.775 → 178.225, continua idêntica antes e depois porque nem alvo nem stop foram tocados na barra de entrada.

A segunda compra permanece ausente. Na avaliação 13:04 o motor ainda estava comprado e, portanto, a v5.7 apenas enviou as saídas; a zeragem ocorre na etapa OHLC posterior à única avaliação NTSL daquela barra. O console do Profit, em contraste, observa zero, solicita outra compra, observa +1 e solicita nova proteção sob o mesmo rótulo de avaliação. Reproduzir esse ciclo exigiria uma nova avaliação após o preenchimento dentro da barra. Isso não foi implementado: com apenas OHLC, a quantidade e a ordem dessas reavaliações e preenchimentos seriam especulativas.

## Comandos reproduzíveis

```powershell
py -3.11 estrategia.py `
  --csv <privado>\WINZ26_20261026_profit_1min_privado.csv `
  --ntsl estrategias\execucao\Modelo_Unificado_Refatorado_v5_7.ntsl `
  --saida <privado>\20261026_depois `
  --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --inputs <privado>\inputs_v5_7_paridade.json `
  --volume-financeiro-ntsl --agressao-referencia-injetada `
  --rastrear-ordens --protecao-no-candle-entrada

py -3.11 tools\comparar_paridade_mesmas_barras.py <argumentos privados> `
  --data 2026-10-26 --aquecimento 63 `
  --motor-candles <privado>\20261026_depois\candles.csv `
  --motor-execucoes <privado>\20261026_depois\execucoes.csv `
  --saida <privado>\comparacao_20261026_depois.json

py -3.11 -m pytest -q
```

## Evidência ainda necessária

Para decidir se o motor deve executar múltiplas avaliações NTSL dentro do mesmo candle OHLC, falta o histórico nativo de ordens do Profit com timestamp subminuto e identificador da ordem para: preenchimento do primeiro stop 177.215, criação e aceitação da segunda compra 176.815, preenchimento dessa compra, criação/disparo/preenchimento do stop 176.465 e cancelamentos OCO. Essa sequência resolveria se houve nova avaliação efetiva após a primeira zeragem e quantas transições ocorreram dentro do minuto. Até lá, a segunda operação permanece indeterminada em OHLC.
