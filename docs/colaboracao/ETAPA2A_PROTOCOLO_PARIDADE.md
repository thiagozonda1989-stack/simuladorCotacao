# Etapa 2A — protocolo de paridade Profit Ultra × simulador

Data da primeira execução: 2026-11-19. Este protocolo não otimiza parâmetros, não usa book e não abre a reserva final. O pregão de 26/10/2026 fica reservado para repetição somente depois de estabilizar o procedimento de 21/10/2026.

## Evidência de testes no Windows

O SHA funcional `c534b575a027bc196743391a9674b7a9ed8c824d` foi executado com Python 3.11.3 após remover `PYTHONUTF8` do ambiente. O comando `py -3.11 -m pytest -q` resultou em **27 passed, 12 warnings**. A falha CP1252 anterior foi eliminada com `read_text(encoding="utf-8")`; os avisos restantes são os `Pandas4Warning` de timezone já conhecidos em `integrar_profitrtd.py:30` e `replay_ticks.py:30`.

## Escopo congelado

| Item | Configuração |
|---|---|
| Ativo/contrato | WINZ26, conforme identificação da captura e contrato negociável após o vencimento de outubro |
| Pregão inicial | 21/10/2026 |
| Fuso | `America/Sao_Paulo` (UTC−03:00 nessa data) |
| Candle | 1 minuto; timestamp representa a **abertura** do minuto `[t, t+1min)` |
| Avaliação | uma vez no fechamento do candle; ordens novas elegíveis no candle seguinte |
| Estratégia | `estrategias/execucao/Modelo_Unificado_Refatorado_v5_7.ntsl`, SHA-256 `0cf2d0d90973a46c38af6dd5bbe4cfeba9d97d3b9242f9ad5cc490318395a22a` |
| Quantidade | `p_Lote=1`; demais inputs originais da v5.7 |
| Grade/valor | 5 pontos; R$ 0,20 por ponto por contrato |
| Cenário mecânico | custo R$ 0,00 e slippage 0 tick; não representa desempenho econômico |
| Janela nominal | carregar 09:00–18:31; entradas da estratégia 09:15–17:00, exceto 10:25–10:35 e 14:25–14:35 |
| Aquecimento | mínimo de 63 candles válidos após início/reinício: 14 barras do ATR encadeadas na média de 50 barras (`14 + 50 - 1`); nenhuma ordem do aquecimento entra na comparação |

No Profit, a rodada deve ser feita em **Backtest/Replay**, nunca em automação de conta real: WINZ26, 21/10/2026, período 1 Min, execução OHLC/fechamento do candle, quantidade e quantidade máxima 1, slippage 0, custos 0 e “Executar nos Limites” habilitado. O código da candidata não é alterado; `indicador_paridade_modelo_unificado_v5_7_v1_0.ntsl` é uma instrumentação separada e não envia ordens.

## Fonte local e barras

`tools/preparar_paridade_win.py` lê somente `win_negocios_21102026.csv`, ordena por timestamp e usa `Sequencia` apenas para desempate local. A sequência não é sequência de bolsa. O derivado privado e seu manifesto ficam em `C:\Users\thiag\Documents\ProfitRTD\derivados_etapa2a_20261119` e não são publicados.

Foram obtidos 4.296.230 negócios, 14.879.339 contratos e 563 candles. O campo de agressor classificou 1.498.457 negócios como `Comprador`, 1.456.311 como `Vendedor` e 1.341.462 (31,22%) como RLP/leilão/direto, sem lado utilizável para reproduzir `AgressionVolBalance`. Logo, o saldo de agressão local é parcial e não pode ser considerado equivalente ao Profit sem uma regra comprovada para RLP.

Na janela 09:15–17:45 existem 511 timestamps de candle e 506 candles não marcados como início de lacuna. Isso autoriza comparar OHLC/volume/trades por candle quando a exportação do Profit existir; não autoriza continuidade de indicadores. As sete lacunas maiores que 5 s estão em `ETAPA2A_LACUNAS_WIN_20261021.csv`. A primeira lacuna estrutural é 09:01:29.821–09:05:18.253, portanto antecede a janela de entrada e já contamina VWAP e saldo acumulado às 09:15 se o Profit tiver histórico contínuo.

## Semântica de lacuna

| Estado | Simulador nesta rodada | Regra de comparabilidade |
|---|---|---|
| Ordens pendentes | canceladas automaticamente no primeiro candle pós-lacuna | comparar apenas se o Profit também cancelar no mesmo instante |
| Posição aberta | preservada; a lacuna é registrada | trecho fica não comparável até evidência equivalente no Profit |
| VWAP diário | reinicia no segmento pós-lacuna | não comparar com VWAP contínuo do Profit |
| Saldo de agressão | reinicia no segmento pós-lacuna | não comparar com saldo contínuo; RLP agrava a limitação |
| Médias e desvios | janelas móveis são limpas | exigir novo aquecimento de 63 candles |

Se a série do Profit for contínua onde a captura local tem lacuna, o trecho afetado é marcado **não comparável**; não se preenche o passado e não se carrega VWAP/agressão através da lacuna. A posição não é zerada artificialmente só porque faltaram dados.

## Regras mecânicas de ordem

- Entrada a mercado: o sinal é calculado no fechamento; a ordem preenche na abertura do candle seguinte, sem slippage no cenário mecânico.
- Limite: toque é suficiente (`limite_exige_ultrapassar=false`). Compra preenche pelo menor entre abertura e limite; venda, pelo maior.
- Stop-limit: o extremo do candle aciona o stop. O preço usa o pior entre abertura e gatilho, desde que respeite o limite. Gap além do limite deixa a ordem acionada e pendente; não se presume retorno intrabar.
- OCO: alvo e stop podem ser reenviados enquanto há posição. Se ambos forem possíveis no mesmo OHLC, a barra é ambígua e a regra conservadora escolhe a saída adversa.
- Cancelamento NTSL: `CancelPendingOrders` remove todas as pendentes. A própria estratégia cancela e zera fora do horário/filtro de densidade.
- Zeragem: ao fim do pregão, o simulador cancela pendentes e fecha posição ao fechamento disponível, marcado como fechamento sintético. No caso sintético de dois negócios da Etapa 1, o segundo preenchimento foi exatamente essa zeragem sintética de fim de pregão, não um sinal normal de saída.

## Ordem de comparação e tolerâncias

A comparação é estritamente: **barras → indicadores → sinais → ordens → preenchimentos → posição**. Não se interpreta camada posterior enquanto uma anterior relevante divergir.

1. Barras: timestamp exato, OHLC com tolerância 0 ponto, volume e negócios exatos.
2. Indicadores: VWAP, desvio, ATR, média do ATR, saldo de agressão e z-score com tolerância absoluta 0,01; regime exato. Só após 63 candles válidos.
3. Sinais: compra/venda booleanos exatos no mesmo fechamento.
4. Ordens: lado, tipo, quantidade, gatilho, limite, instante de criação/cancelamento exatos.
5. Preenchimentos: lado/quantidade exatos, timestamp dentro do candle correspondente e preço com tolerância 0 ponto no cenário mecânico.
6. Posição: quantidade exata por candle e preço médio com tolerância 0 ponto.

A matriz parcial, com quantidades locais e campos ainda ausentes do Profit, está em `ETAPA2A_MATRIZ_PARIDADE_20261021.csv`.

## Primeira execução local da candidata

O replay local em candle produziu 563 barras, 2 sinais de compra, 3 de venda, 10 preenchimentos/5 operações, 650 pontos-contrato, R$ 130,00 no cenário sem custos e drawdown de 700 pontos-contrato. Houve sete lacunas, uma com posição aberta e duas ordens canceladas. Esses números são somente uma referência operacional; não são resultado de paridade nem validação de estratégia.

Comandos:

```powershell
py -3.11 tools\preparar_paridade_win.py `
  --entrada C:\Users\thiag\Documents\ProfitRTD\win_negocios_21102026.csv `
  --saida <privado>\WINZ26_20261021_1min_paridade.csv `
  --manifesto <privado>\WINZ26_20261021_1min_paridade.manifesto.json `
  --lacuna-ms 5000

py -3.11 estrategia.py --csv <privado>\WINZ26_20261021_1min_paridade.csv `
  --ntsl estrategias\execucao\Modelo_Unificado_Refatorado_v5_7.ntsl `
  --saida <privado>\simulador_v5_7_20261021 --segundos 60 --formato ohlc `
  --tick 5 --valor-ponto 0.2 --custo-por-contrato-lado 0 `
  --slippage-ticks 0 --inputs <privado>\inputs_v5_7_paridade.json
```

## Exportações ainda necessárias do Profit

Para concluir a matriz, exportar sem editar os dados:

1. `profit_WINZ26_20261021_barras_1min.csv`: timestamp da abertura, abertura, máxima, mínima, fechamento, volume e número de negócios, de 09:00 a 18:31.
2. `profit_WINZ26_20261021_indicadores_v5_7.csv`: timestamp e os oito plots do indicador instrumentado, na ordem VWAP, desvio-padrão, ATR, média ATR, saldo de agressão, z-score de volume, regime e sinal.
3. `profit_WINZ26_20261021_ordens_operacoes.csv`: criação, alteração, cancelamento e execução, com timestamp, lado, tipo, quantidade, gatilho, limite e preço executado.
4. `profit_WINZ26_20261021_posicao.csv`: timestamp, quantidade da posição e preço médio por candle.

Sem o primeiro arquivo, nem a camada de barras pode ser fechada. A primeira divergência candidata é a ausência local dos candles 09:02–09:04; ela só pode ser afirmada depois de verificar se o Profit contém esses candles.
