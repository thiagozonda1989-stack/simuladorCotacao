# Paridade WINZ26 v5.7 — avaliação pós-preenchimento

Código executado no Windows em `6aeb1f95d8642f7057b04a0dba9bd1612b6ee5fe`, a partir do [plano em a3b524d](../../ETAPA2A_PROXIMA_RODADA_PARIDADE.md). Simulador v0.14.0 em pesquisa no PR #2, Python 3.11.3, pandas 3.1.1, Windows 10. A v5.7 original permaneceu no mesmo arquivo e tem SHA-256 `0cf2d0d90973a46c38af6dd5bbe4cfeba9d97d3b9242f9ad5cc490318395a22a`.

## Operações

| Pregão | Profit | Padrão | Proteção legada | Pós-preenchimento |
|---|---:|---:|---:|---:|
| 2026-10-21 | 10 | 10 no motor, **10/10 exatas** | 10 no motor, **10/10 exatas** | 10 no motor, **10/10 exatas** |
| 2026-10-26 | 12 | 10 no motor, **8/12 exatas** | 11 no motor, **11/12 exatas** | 12 no motor, **12/12 exatas** |

Exata exige igualdade de minuto de entrada e saída, lado, quantidade e preços. Padrão e proteção legada produziram os mesmos arquivos de execuções, candles, console e eventos de ordens, byte a byte, que a reexecução no SHA `4a5792440f7f9ea281e977e6f49a43a7f70e3709`, em ambos os dias. O experimento teve 10 avaliações adicionais em 21/10 e 12 em 26/10, uma por entrada elegível. [Matriz](matriz_operacoes.csv) · [Referência anterior](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7046668140)

Em 26/10, no padrão, o stop da #181 fica elegível às 13:05 e preenche às 14:01 a 177.210. Na proteção legada, a #181 zera a 177.215 às 13:04, depois da avaliação regular. A #182 fica ausente. No experimento, o fechamento de 13:04 já vê zero e solicita uma nova compra. A abertura de 13:05 preenche um contrato a 176.815. A avaliação pós-preenchimento lê a barra de 13:04 e solicita alvo 177.265 e stop 176.465/176.460. O motor executa o stop a 176.465 e avalia o fechamento de 13:05 zerado. [Recorte de ordens](rastreio_181_182.csv)

O recorte associa as avaliações 7–11 do Profit e as operações #181 e #182 pela sequência, quantidade, direção e preços já publicados. Na compra #182, o rótulo de contexto NTSL é 13:04 e a abertura/saída da operação são 13:05 na exportação do Profit. As colunas preservam os relógios, sem deslocamento global. Linhas de disparo do simulador deixam vazios os campos de eventos do Profit, que registra a solicitação e a posição observada. [Eventos publicados do Profit](../../captura_paridade_win_20261026_eventos.csv) · [Metodologia dos preços](../../logs_paridade/paridade_console_metodologia.md)

## VWAP, ATR e regime em 26/10

O diagnóstico variou só a VWAP e o corte de aquecimento. Os três modos da matriz de operações usaram a VWAP com reinício e a comparação histórica de 63 barras por dia. Para os indicadores, rodamos duas séries com o mesmo NTSL de plots, uma com VWAP reiniciada e outra com `--vwap-continuo-lacunas`. Avaliamos cada série com o corte histórico por dia e com o corte por segmento. O comparador manteve fixo o replay de operações ao variar essas duas escolhas.

| VWAP após lacuna | Corte de 63 barras | Primeira barra | VWAP | ATR | Média do ATR | Regime | Candidato |
|---|---|---|---:|---:|---:|---:|---:|
| Reinicia | Por dia | 10:15 | 0/490 | 490/490 | 463/490 | 487/490 | 490/490 |
| Reinicia | Por segmento | 10:42 | 0/463 | 463/463 | 463/463 | 463/463 | 463/463 |
| Contínua | Por dia | 10:15 | 490/490 | 490/490 | 463/490 | 488/490 | 490/490 |
| Contínua | Por segmento | 10:42 | 463/463 | 463/463 | 463/463 | 463/463 | 463/463 |

Tolerância de 0,01 ponto para VWAP, ATR e média do ATR. Regime e candidato exigem igualdade. O primeiro segmento tem 27 barras (09:03–09:29) e fica integralmente fora do corte por segmento. O segundo começa às 09:39, exclui as próximas 63 barras observadas, de 09:39 a 10:41 inclusive, e conserva 463. O corte antigo comparava 27 barras com médias ainda em aquecimento após o reinício.

Na mesma amostra de 463 barras, o erro máximo da VWAP caiu de 33,307032 para 0,004998 ponto ao manter o acumulado de antes da lacuna. A média do ATR e o regime passaram integralmente após o corte por segmento, inclusive na VWAP com reinício. Com ambas as escolhas, os oito plots coincidiram no trecho elegível. A camada de indicadores de 26/10 é **parcial** no pregão inteiro. O resultado se restringe ao trecho observado após aquecimento, com agressão exportada do Profit injetada. A lacuna de 09:30–09:38 continua sem barras e o início do pregão anterior a 09:03 continua fora da exportação. [Matriz de indicadores e erros](matriz_indicadores_20261026.csv)

## Origem, cobertura e transformações

| Pregão | Barras Profit usadas | Período | Timestamps duplicados | Minutos ausentes no período |
|---|---:|---|---:|---:|
| 21/10 | 565 | 09:00–18:24 | 0 | 0 |
| 26/10 | 553 | 09:03–18:24 | 0 | 9 (09:30–09:38) |

WINZ26, OHLC de 1 minuto rotulado na abertura em `America/Sao_Paulo`. As barras e os plots vêm das exportações privadas do Profit, com as entradas preparadas e verificadas contra os hashes dos manifestos da rodada anterior. O CSV local de operações foi conferido contra o SHA-256 do [relatório da captura](../../CAPTURA_PARIDADE_WINZ26_20261026.md). Os preços e quantidades deste recorte já constam nas evidências publicadas da captura. Os originais, OHLC, séries de plots, identificações de conta e titular, caminhos locais e os rastreamentos completos ficam no Windows. O recorte conserva a ordem do motor e as referências aos eventos publicados do Profit. Os agregados registram apenas contagens e erros.

Parâmetros da v5.7 no experimento: ATR 14, média do ATR 50, desvio VWAP 2,1, z-score 1,5, `Trades > 100`, lote 1, alvo 450, stop 350, offset 5. O simulador usa tick 5, R$ 0,20/ponto, custos, slippage e latência adicional zero. O Volume financeiro é explícito, a VWAP por barra é aproximada a partir de Volume e Quantity, e a agressão vem do plot exportado. Os parâmetros da estratégia correspondem ao cenário de paridade. As configurações completas do motor do Profit dependem da exportação original.

| Arquivo publicado neste recorte | Linhas de dados | SHA-256 |
|---|---:|---|
| [matriz_indicadores_20261026.csv](matriz_indicadores_20261026.csv) | 20 | `741676c17da0b31f24b205a100c07b34bda72e69ad44b93d1e7cbe88ffbe8bcb` |
| [matriz_operacoes.csv](matriz_operacoes.csv) | 6 | `51e99d56a7d30df8bd682608cf5a55efe3343b02224cae3bb80f8c4a2636d429` |
| [rastreio_181_182.csv](rastreio_181_182.csv) | 17 | `5f3b363c1d6d8a2dff2782122205cc2e1dbe1b96c87d112b6db974df8613b7e6` |

## Comandos

Execute por pregão com a entrada preparada correspondente e um diretório de destino novo para cada modo. O JSON de inputs contém somente `{"p_Lote": 1}`. Os parâmetros restantes vêm do NTSL.

```powershell
git switch --detach 6aeb1f95d8642f7057b04a0dba9bd1612b6ee5fe
$comum = @('--segundos','60','--formato','ohlc','--tick','5','--valor-ponto','0.2',
           '--volume-financeiro-ntsl','--agressao-referencia-injetada')
$estrategia = 'estrategias/execucao/Modelo_Unificado_Refatorado_v5_7.ntsl'
$indicador = 'estrategias/indicadores/indicador_paridade_modelo_unificado_v5_7_v1_0.ntsl'

# Para cada modo, $modo recebe @(), @('--protecao-no-candle-entrada')
# ou @('--avaliacao-pos-preenchimento').
py -3.11 estrategia.py --csv $barrasPreparadas --ntsl $estrategia `
  --inputs $inputs --saida $replay --rastrear-ordens @comum @modo

# Para 26/10, cruzar as duas opções de $vwap com as duas de $corte
# na comparação. O caminho $replay permanece fixo no modo pós-preenchimento.
# $vwap recebe @() ou @('--vwap-continuo-lacunas').
py -3.11 estrategia.py --csv $barrasPreparadas --ntsl $indicador `
  --saida $plotsMotor @comum @vwap
# $corte recebe @() ou @('--aquecimento-por-segmento').
py -3.11 tools/comparar_paridade_mesmas_barras.py --profit-barras $barrasProfit `
  --profit-indicadores $plotsProfit --profit-operacoes $operacoesProfit `
  --barras-preparadas $barrasPreparadas --motor-indicadores "$plotsMotor/candles.csv" `
  --motor-candles "$replay/candles.csv" --motor-execucoes "$replay/execucoes.csv" `
  --data $dia --aquecimento 63 --saida $comparacao @corte

py -3.11 -m pytest -q
```

## Testes e limites

A prova de quatro barras foi criada e executada antes da implementação. Padrão e proteção legada passaram as asserções. A parte experimental falhou pela opção ausente. Após a implementação, os quatro preenchimentos esperados passaram, com a primeira saída na barra 2 e a segunda na barra 3. A suíte completa passou com **56 testes e 12 avisos conhecidos de timezone do pandas**. As regressões verificam dados anteriores, persistência única de histórico, arrays e médias, renovação por chave, descarte de stop já disparado numa posição anterior, lacuna, início de sessão, saída a mercado no fechamento, entradas mistas e aquecimento por segmento.

O experimento supõe preenchimento a mercado na abertura e ativação das novas proteções conforme a elegibilidade do simulador. O preço igual à abertura sustenta essa hipótese para a #182. Os arquivos compartilhados permitem revisar a ordem observada e as diferenças agregadas. A reprodução com o Profit exige barras, plots e operações privados. Confirmar o instante nativo de ativação, o disparo, o preenchimento e os cancelamentos vinculados ainda exige o histórico de ordens com resolução subminuto. A coincidência em dois pregões mede paridade neste cenário, sem validação fora da amostra.
