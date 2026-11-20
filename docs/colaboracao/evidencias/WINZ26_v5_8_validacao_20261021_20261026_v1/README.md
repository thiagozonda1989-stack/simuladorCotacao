# Validação da v5.8 completa em WINZ26

Código e testes da rodada `e54a729150b736173c4fdea16d65579759df6dde`. O motor continua no código validado em `68f1025526be87c52a5fa8cb8f9368dad06062ca`. O ponto de partida do PR é `2c080c654e1782727e2ea8bea4ad30c7004e9a96`. Windows 10, Python 3.11.3, pandas 3.1.1. [Parecer Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7049423271) · [Parecer Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7049722151)

## Resultado medido

A v5.8 completa foi executada nos dois pregões no simulador. A cópia instrumentada do simulador produziu os mesmos `execucoes.csv`, `candles.csv` e `eventos_ordens.csv` que o fonte original, byte a byte nos dois dias. A execução nativa foi reservada ao usuário. Nenhum log ou relatório nativo da v5.8 estava disponível para comparação nesta rodada. O primeiro evento divergente entre motores permanece indeterminado.

| Pregão | Compra/venda candidatas, trecho elegível | Solicitações de compra/venda, dia inteiro | Operações fechadas no simulador | Profit v5.8 |
|---|---:|---:|---:|---|
| 21/10/2026 | 11 / 13 | 3 / 3 | 6 | Aguardando exportação |
| 26/10/2026 | 10 / 7 | 6 / 4 | 10 | Aguardando exportação |

Um candidato é o sinal confirmado na avaliação regular, antes dos filtros e das ordens. A camada de solicitações usa as chamadas de entrada. A contagem de operações fechadas vem dos preenchimentos. A posição vem da avaliação observada e das execuções do simulador. [Matriz v5.8](matriz_v5_8.csv) · [Cobertura dos cenários](cobertura_v5_8.csv)

## Fonte, parâmetros e barras

O [fonte completo original](../../../../estrategias/execucao/Modelo_Unificado_v5_8.ntsl) preserva os 7.891 bytes da versão local `Modelo_Unificado_v5_8.txt`, SHA-256 `16ee74d277add73798e26cd9d2653d26b7b375eac37c9d23455dd64b3662b20a`. As duas cópias instrumentadas adotam `p_Exec_Tick=0` como padrão e acrescentam somente o registro de estado e solicitações. O [JSON](inputs_v5_8.json) enumera os 22 inputs dos dois lados. A rodada usa os defaults da v5.8 com `p_Exec_Tick=0`: lote 5, stop 350, alvo 400, offset 50, espera 3, máximo de 10 entradas por dia, `p_Modo_Banda=0`, ATR 14, média ATR 50 e desvio 20, entre os demais inputs publicados.

Simulador em `--avaliacao-pos-preenchimento`, OHLC, 1 minuto, tick 5, R$ 0,20/ponto, custos, slippage e latência adicional zero, limites ao toque. Usados os mesmos derivados privados da exportação de barras do Profit e saldo de agressão de referência injetado. Volume financeiro no NTSL e VWAP contínua entre lacunas. O corte de 63 barras por segmento se aplica à comparação; o replay recebe todo o histórico exportado. O aquecimento interno da v5.8 continua usando seu próprio `CurrentBar > 86` com os inputs desta rodada.

| Pregão | Janela de entrada | Barras | Duplicatas | Lacuna | Elegíveis para comparação |
|---|---|---:|---:|---|---:|
| 21/10 | 09:00–18:24 | 565 | 0 | Nenhuma | 502, desde 10:03 |
| 26/10 | 09:03–18:24 | 553 | 0 | 09:30–09:38 | 463, desde 10:42 |

Os timestamps das barras são de abertura em `America/Sao_Paulo`. SHA-256 dos derivados privados: `7b1e173400d7bd68f6198fbda51e0ef2026c3f289b7ea51e956e4c8d04066e60` em 21/10 e `adace8f7c2ab691c3686e9e85533e2094b4bfd957ff7d377b3854fcb90fd92b9` em 26/10. Os originais, caminhos privados, identificações e logs completos de mercado ficam no Windows. A publicação contém agregados, código e rastreamentos sintéticos. A validação integral depende da mesma história carregada no Profit e da ordem intrabar quando relevante.

## Sonda de estado v2

A [sonda anterior v1](../WINZ26_v5_7_persistencia_20261026_v1/sonda_persistencia_profit_v1_0.ntsl) continua versionada. A v2 grava, na avaliação extra comprada, Boolean verdadeiro, `v_Array[1]=17` e `v_Estado=23`. Na avaliação regular zerada seguinte, o simulador lê `boolean_antes=1`, `array_antes=0` e `estado_1=0`. O log explicita a sequência, o rótulo, a posição e a leitura antes da atribuição. A leitura nativa para os três tipos permanece pendente. [Sonda v2 para o Profit](sonda_persistencia_profit_v2_0.ntsl) · [Sonda v2 para o simulador](sonda_persistencia_simulador_v2_0.ntsl) · [Log do simulador](sonda_v2_simulador.csv)

## Cobertura da v5.8 e controles

| Cenário | Replays locais | Resultado do controle com a estratégia completa |
|---|---|---|
| Espera após stop na barra de entrada | 0 casos em 21/10, 2 em 26/10 | Entrada e stop na barra 10, saída gravada no fechamento e nova solicitação na 13 |
| Uma entrada por candle | 0 solicitações duplicadas por rótulo em ambos | Extra comprada com contexto da barra 9 vê `ultima_entrada=9` e `pode=0` |
| Limite diário | Máximos de 6 e 10; em 26/10, dois candidatos em posição zerada e no horário com contador já no teto | Dois pedidos em cada pregão no caso de limite 2, com primeira barra da segunda sessão fora da janela de entrada |
| Reinício do limite | Cada execução real contém um único pregão | Reinício normal em duas sessões e caso de risco com solicitação na primeira barra |
| Cancelamento de pendente com posição zerada | Nenhuma solicitação de cancelamento nos dois dias | Ordem limite sintética pré-carregada é cancelada na barra 1, sem preenchimento |
| Stop-limit com gap e `Abs(Position)` | 2 e 5 disparos; todos com saída no mesmo candle de disparo | Entrada 1.005 × 2, stop 655 com limite 605, abertura abaixo do limite na barra 11 e saída de dois contratos a 605 na 12 |
| `Power`, modo banda 1 e referências `[1]` | Banda 0 e `p_Exec_Tick=0` na rodada real | Modo 1 confere raiz da média do quadrado da distância até VWAP. `Trades[1]` auditado como leitura. Média e desvio de Volume no Z-score conferidos sobre as 20 barras anteriores. |

**Achado controlado do simulador:** se a primeira barra da sessão solicita uma entrada, o preenchimento na abertura seguinte dispara uma avaliação extra com o contexto da primeira barra. Nesse contexto, `Date <> Date[1]` continua verdadeiro. A v5.8 volta a escrever zero no contador, embora a solicitação anterior tenha incrementado a contagem. Com limite sintético de dois, o segundo pregão chegou a três solicitações. O primeiro evento relevante é a avaliação extra de contexto 19, com posição 2 e `entradas=0` após a solicitação da barra 19. Os dois pregões reais não cobriram essa sequência. A equivalência com o Profit e uma eventual correção dependem de confirmação nativa. [Recortes sintéticos em ordem de emissão](controles_v5_8.csv)

## Execução manual no Profit e exportações

1. No Editor de Estratégias, abra como estratégia de execução a [auditoria v5.8 para o Profit](Modelo_Unificado_v5_8_Auditoria_profit_v1_0.ntsl). Compile e execute no **Backtest OHLC**, ativo **WINZ26**, **1 minuto**, slippage e custo zero, quantidade padrão e máxima **5**, e execução nos limites. Confira todos os inputs no [JSON](inputs_v5_8.json). Use uma execução para cada pregão, iniciando com posição zerada. Registre a versão do Profit, modo, período de análise, começo do histórico efetivamente carregado e inputs aplicados. Se a janela nativa carregar histórico adicional, preserve a exportação desse histórico. O motor deve repetir a mesma entrada e o mesmo aquecimento para atribuir divergências. [Editor do Profit](https://ajuda.nelogica.com.br/hc/pt-br/articles/9165042993691-Editor-de-Estrat%C3%A9gias-Crie-estrat%C3%A9gias-pr%C3%B3prias-atrav%C3%A9s-do-Profit) · [Backtest OHLC](https://ajuda.nelogica.com.br/hc/pt-br/articles/12742147789851-Backtest-OHLC)
2. Para **21/10** e **26/10**, guarde privadamente estes arquivos, trocando `AAAAMMDD` pela data:
   - `v58_AAAAMMDD_console.txt` com todas as linhas `V58;` de uma única execução Debug, sem reordenar, deduplicar ou alterar números pt-BR. São as avaliações e solicitações com o rótulo de contexto da estratégia.
   - `v58_AAAAMMDD_operacoes.csv` exportado da aba Operações do Backtest, com número da operação, ativo, abertura, fechamento, lado, quantidade de compra/venda e preços de compra/venda. Mantenha o cabeçalho original para o comparador.
   - `v58_AAAAMMDD_barras.csv` com `Data;Abertura;Máxima;Mínima;Fechamento;Trades;Quantity;Volume` do mesmo ativo, período e histórico. Se o insumo mudar, guarde também `v58_AAAAMMDD_agressao.csv` com `Data;v_Saldo_Agressao` da referência Plot ou da avaliação regular para preparar as barras com a mesma agressão.
   - `v58_AAAAMMDD_config.txt` ou captura dos parâmetros e configuração efetiva. Se disponível, acrescente o histórico de ordens com ID, criação, gatilho, preenchimento, cancelamento e timestamp subminuto. O console instrumentado permite conferir pedidos e estado. A confirmação de ativação e cancelamento nativos usa o histórico de ordens.
3. Em uma execução separada de **26/10**, abra a [sonda v2 do Profit](sonda_persistencia_profit_v2_0.ntsl), use quantidade e máximo **1** e preserve as linhas `PERSISTENCIA_V2;` em `sonda_v58_20261026_profit.txt`. No fechamento zerado após a extra comprada, confronte `boolean_antes`, `array_antes` e `estado_1` com o log local. [Modo Debug](https://ajuda.nelogica.com.br/hc/pt-br/articles/27698808373019-Modo-Debug)

## Comandos locais e comparação nativa

Use um destino novo para cada execução. O comparador separa as camadas, usa a ordem de emissão dentro do rótulo de contexto NTSL e registra a primeira diferença de cada camada. Para preenchimentos usa os horários da exportação, sem deslocamento global. Empates no minuto do Profit são organizados pelo número de operação, com entrada antes da saída. Essa ordenação serve à comparação por minuto.

```powershell
$evid = 'docs/colaboracao/evidencias/WINZ26_v5_8_validacao_20261021_20261026_v1'
$comum = @('--segundos','60','--formato','ohlc','--tick','5','--valor-ponto','0.2',
  '--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas',
  '--avaliacao-pos-preenchimento','--rastrear-ordens')
py -3.11 estrategia.py --csv $barrasPreparadas `
  --ntsl estrategias/execucao/Modelo_Unificado_v5_8.ntsl `
  --inputs "$evid/inputs_v5_8.json" --saida $original @comum
py -3.11 estrategia.py --csv $barrasPreparadas `
  --ntsl "$evid/Modelo_Unificado_v5_8_Auditoria_simulador_v1_0.ntsl" `
  --inputs "$evid/inputs_v5_8.json" --saida $auditoria @comum

# Quando as exportações v5.8 do Profit chegarem:
py -3.11 tools/comparar_v5_8.py --data $dia --aquecimento 63 `
  --console-profit $consoleProfit --operacoes-profit $operacoesProfit `
  --barras-profit $barrasProfit --barras-preparadas $barrasPreparadas `
  --console-simulador "$auditoria/console.csv" --candles-simulador "$auditoria/candles.csv" `
  --execucoes-simulador "$auditoria/execucoes.csv" --saida $comparacao

$antes = 'docs/colaboracao/evidencias/WINZ26_v5_7_persistencia_20261026_v1'
py -3.11 estrategia.py --csv "$antes/candles_sinteticos.csv" `
  --ntsl "$evid/sonda_persistencia_simulador_v2_0.ntsl" --saida $sonda `
  --segundos 60 --formato ohlc --avaliacao-pos-preenchimento --rastrear-ordens
py -3.11 -m pytest -q tests/test_v5_8_paridade.py
py -3.11 -m pytest -q
```

**Suíte** 66 aprovados e 12 avisos de timezone do pandas. Os seis replays de regressão v5.7 repetiram 10/10 em 21/10 e 8/12, 11/12 e 12/12 em 26/10. A #182 seguiu exata no pós-preenchimento. Os oito plots mantiveram 502/502 e 463/463, com VWAP contínua e corte por segmento. Execuções, candles, console e eventos de ordens da v5.7 são idênticos aos da rodada escalar. [Matriz v5.7](regressao_v5_7.csv) · [Comandos da regressão anterior](../WINZ26_v5_7_persistencia_escalar_20261026_v2/README.md)

[TXT com fontes completas para o Gemini](fontes_gemini.txt) · [Manifesto SHA-256](SHA256SUMS.txt)
