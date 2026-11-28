# Continuidade histórica da v5.8 e saída das 10:15

PR #2, código executado `0d2f19a47307d5390f5d89bb53d70e6c87a37856`, base `c9ddc63f0ac983688061114f4d1b393b0d14e761`. A rodada usa WINZ26, barras de 1 minuto, fuso America/Sao_Paulo, `p_Exec_Tick=0`, lote 5, alvo 400 pontos, stop 350 pontos, folga stop-limit 50 pontos, tick 5, R$ 0,20/ponto, custos e slippage zero. Os replays da v5.8 usam avaliação pós-preenchimento, VWAP contínua, Volume NTSL financeiro e agressão de referência. O histórico prefixado é de 20/10 para 21/10 e de 23/10 para 26/10. A comparação mantém um corte de 63 barras por segmento e confere solicitações no pregão inteiro. [Inputs completos e configuração do Profit](../WINZ26_v5_8_validacao_20261021_20261026_v1/README.md) · [Evidências anteriores](../WINZ26_v5_8_captura_profit_20261021_20261026_v2/README.md)

## Saída das 10:15 em 26/10

Em 10:14 no console do Profit, a avaliação 635 vê posição zero, tem sinal de compra e solicita cinco contratos. No mesmo rótulo de contexto, a avaliação 636 vê posição comprada de cinco e solicita alvo em +400, gatilho do stop em −350 e limite em −400 pontos em relação à entrada. A exportação registra entrada e saída às 10:15, com saída a +400. A avaliação regular 637, rotulada 10:15, já vê posição zerada. O rastreio do simulador registra as mesmas solicitações e o stop a −350. [Rastreio por camada](eventos_10h15.csv) · [Níveis de referência](../WINZ26_v5_8_captura_profit_20261021_20261026_v2/ambiguidade_10h15.csv)

Na captura de Negócios, o primeiro registro às **10:15:00.000** tem o preço de entrada da exportação e quantidade de um contrato. Ele marca o início observado do minuto, sem vínculo com o preenchimento de cinco do backtest. Depois desse registro, o primeiro negócio na faixa do alvo ocorre às **10:15:12.283** (sequência da captura 268564). O preço exato do alvo aparece no mesmo milissegundo (268582). O primeiro negócio na faixa do gatilho do stop ocorre às **10:15:43.810** (274300), com o preço exato no mesmo milissegundo (274311). O primeiro preço na faixa do limite do stop ocorre às **10:15:44.720** (274806). Os primeiros toques de alvo e gatilho estão separados por **31,527 s** no relógio de mercado. [Primeiros negócios observados](toques_10h15.csv)

O minuto observado vai de 10:15:00.000 a 10:15:59.999, tem registros em 57 dos 60 segundos e intervalo máximo de 2.966 ms entre timestamps, com até 1.076 ms entre registros até o primeiro alvo. Há 12.352 negócios e 22.974 contratos no CSV, equivalentes a **64,84%** dos 19.050 Trades e **65,93%** dos 34.844 contratos das barras de referência. A abertura, máxima e fechamento reconstituídos coincidem. A mínima da captura fica 15 pontos acima da mínima da barra. A referência de Trades é a série Profit já conferida no console. A referência de quantidade é a exportação privada usada para preparar o replay. A exportação nova de OHLC tem apenas preços. [Cobertura e comparação de totais](cobertura_negocios_10h15.csv)

Há 4.773 timestamps distintos, 1.996 milissegundos com mais de um negócio, zero repetições de `Sequencia` e 4.731 inversões de timestamp entre linhas físicas adjacentes. A análise ordena por horário de mercado (`Coluna_1`) e usa `Sequencia` como desempate de apresentação. A sequência pertence à captura ProfitRTD, sem confirmação de ser o sequencial da bolsa. O relógio do coletor `DataHora_PC` pertence à coleta posterior. Os dados sustentam **alvo antes do stop entre os negócios capturados**. Os registros ausentes permitem que o mercado tenha tocado um nível em outro instante.

Busquei exportações de histórico de ordens no workspace, Documentos, Downloads, Área de Trabalho e nas pastas Nelogica e OneDrive disponíveis. Os arquivos de ciclo de ordem encontrados são do simulador. O Debug do Profit registra solicitações e observações de posição. A exportação de operações registra a saída no alvo com resolução de minuto. Continuam indeterminados o horário subminuto de entrada, a ativação do alvo e do stop, o instante e a sequência dos eventos de disparo e preenchimento e o cancelamento da perna OCO. Para fechar esse vínculo, é necessário um histórico nativo do mesmo backtest com IDs das ordens, vínculo OCO, status e timestamps subminuto e, para a sequência de mercado completa, os negócios faltantes ou uma captura equivalente. A regra adversa continua valendo no OHLC. [Rastreio por camada](eventos_10h15.csv)

## Cobertura de outros duplos toques

A varredura usa os replays com continuidade e conserva somente operações associadas por hora de entrada, hora de saída, direção, quantidade e preço de entrada. Em cada passagem de ordens, verifica o alvo e o stop ainda por disparar que estão elegíveis para a posição naquele momento. Inclui a avaliação extra de proteção na abertura. Conta barras únicas de operações pareadas. Esta cobertura é de OHLC e proteções do simulador com solicitações conferidas no Profit. A disponibilidade de negócios foi medida no único minuto de duplo toque.

| Pregão | Operações associadas e protegidas | Barras com as duas proteções elegíveis | Barras com duplo toque |
|---|---:|---:|---:|
| 21/10 | 7/7 | 149 | 0 |
| 26/10 | 10/10 | 26 | 1 |
| Total | 17/17 | 175 | 1 |

O único caso é 10:15. Nenhuma regra de trajetória foi inferida de um caso. [Censo de proteções](censo_duplo_toque.csv)

## Opção de replay e resultados

`--historico-continuo-lacunas` preserva janelas móveis, `TrueRange` e referências históricas `[n]` das barras existentes ao retomar uma lacuna intradiária. O padrão reinicia esse contexto. `CurrentBar` avança uma unidade por barra recebida nos dois modos. O identificador de segmento, a flag de lacuna, `BarrasNoSegmento` e o corte da comparação continuam marcando a retomada. A opção conserva escalares e posição como no padrão, cancela ordens pendentes na lacuna e mantém as regras de sessão. A acumulação da VWAP usa a opção própria, e a agressão injetada usa o valor exportado. Cada replay consome somente os candles disponíveis. Em 26/10, a lacuna do pregão alvo vai de 09:30 a 09:38, com retomada às 09:39. O histórico de 23/10 também tem uma retomada às 17:55. As duas fronteiras ficaram registradas no replay com continuidade, sem posição exposta ou ordens canceladas nessa amostra.

| Pregão | Reinício padrão | Continuidade explícita |
|---|---:|---:|
| 21/10 | 7/7 | 7/7 |
| 26/10 | 8/10 | 9/10 |

Em 21/10, os dois modos registram 306 solicitações coincidentes e 509 avaliações comparáveis sem divergência nas camadas de sinal, filtro, indicadores, posição e estado. Em 26/10, a primeira solicitação divergente no padrão é às 09:50 e a primeira execução sem par ocorre às 09:51. Com a opção, as 62 solicitações, as 472 avaliações comparáveis e as dez entradas coincidem. A primeira diferença de preenchimento é a saída das 10:15. Os candles e eventos de ordens da nova continuidade em 26/10 reproduzem byte a byte o diagnóstico anterior. As execuções são iguais após interpretar a coluna de custos como número. [Matriz v5.8](matriz_v5_8.csv)

A sonda v2 permanece uma pendência do motor para arrays e histórico de estado gravado na avaliação extra. No fechamento zerado de contexto 13:04, Profit e simulador leram Boolean 1. O array e `estado[1]` retornaram 17 e 23 no Profit e 0 e 0 no simulador. [Sonda v2](../WINZ26_v5_8_captura_profit_20261021_20261026_v2/sonda_v2_profit_simulador.csv)

## Testes e reprodução

Python 3.11.3, Windows, pandas 3.1.1. Passaram **75 testes**, com 12 avisos de timezone do pandas que já ocorriam na base. Os controles novos cobrem referências de preço e estado, médias, `TrueRange`, `CurrentBar`, `BarrasNoSegmento`, configuração de sessão, cancelamento de pendentes mesmo com posição aberta, rejeição do modo tick e ambiguidade de toques no mesmo milissegundo. Os seis replays da v5.7 e os dois de plots reproduziram 26 arquivos byte a byte. A v5.7 manteve 10/10 em 21/10 nos três modos e 8/12, 11/12 e 12/12 em 26/10. A #182 ficou exata em pós-preenchimento. [Matriz v5.7](regressao_v5_7.csv)

Em cada pregão, use o histórico privado preparado na rodada anterior. Rode uma vez com `$lacunas = @()` e outra com `$lacunas = @('--historico-continuo-lacunas')`. Use destinos inéditos em cada execução.

```powershell
$evid = 'docs/colaboracao/evidencias/WINZ26_v5_8_validacao_20261021_20261026_v1'
$auditoria = "$evid/Modelo_Unificado_v5_8_Auditoria_simulador_v1_0.ntsl"
$inputs = "$evid/inputs_v5_8.json"
$comum = @('--segundos','60','--formato','ohlc','--tick','5','--valor-ponto','0.2',
           '--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas')
py -3.11 estrategia.py --csv $barrasComHistorico --ntsl $auditoria --inputs $inputs `
  --saida $replay @comum --avaliacao-pos-preenchimento --rastrear-ordens @lacunas
py -3.11 tools/comparar_v5_8.py --data $dia --aquecimento 63 `
  --console-profit $consoleProfit --operacoes-profit $operacoesProfit `
  --barras-profit $barrasProfit --barras-preparadas $barrasComHistorico `
  --console-simulador "$replay/console.csv" --candles-simulador "$replay/candles.csv" `
  --execucoes-simulador "$replay/execucoes.csv" --saida $comparacao
py -3.11 -m tools.investigar_protecoes_v5_8 --data $dia --barras $barrasComHistorico `
  --ntsl $auditoria --inputs $inputs --negocios $negocios `
  --operacoes-profit $operacoesProfit --saida $auditoriaIntrabar
py -3.11 -m pytest -q
```

A regressão da v5.7 usa `p_Lote=1`, o NTSL original, as barras de cada pregão, VWAP contínua e os três modos anteriores, com a opção nova desativada. O comparador de indicadores mantém o corte de 63 barras por segmento. [Comandos da v5.7](../WINZ26_v5_7_persistencia_escalar_20261026_v2/README.md#comandos)

O manifesto registra os arquivos compartilhados. Os CSVs contêm contagens, horários de diagnóstico, níveis relativos e resultados de paridade. Os CSVs brutos e preparados, identificadores de participantes e cotações absolutas ficam no Windows. [Inventário de fontes privadas](fontes_privadas.csv) · [SHA-256 dos artefatos](SHA256SUMS.txt) · [Fontes completas para o Gemini](fontes_gemini.txt)
