# Correção experimental de persistência escalar pós-preenchimento

O código executado no Windows foi `68f1025526be87c52a5fa8cb8f9368dad06062ca`. O comparativo antes/depois usa o head da evidência do Profit, `bcb09c9d68b672f0121327142235710497d1c8d9`, cujo motor era idêntico a `6aeb1f95d8642f7057b04a0dba9bd1612b6ee5fe`. As sondas da rodada anterior foram introduzidas em `e7921ef9759ffa783c4aba18cc51b81109a17c58`. [Evidência nativa do Profit](../WINZ26_v5_7_persistencia_20261026_v1/profit_sonda_log.csv)

## Regressão da sonda escalar

| Origem | Avaliação extra comprada | Avaliação regular zerada das 13:04 |
|---|---|---|
| Profit, sonda executada pelo usuário | `seq=2`, `depois=1` | `seq=3`, `antes=1` |
| Simulador antes | `seq=2`, `depois=1` | `seq=2`, `antes=0` |
| Simulador corrigido | `seq=2`, `depois=1` | `seq=3`, `antes=1` |

O teste foi executado primeiro com o motor de referência. Falhou com `Fechamento zerado leu antes=0 após a gravação de 1.` O teste da espera sintética também falhou, com a última saída em 0, quando deveria ser 4. Depois da correção, ambos passaram. A sonda do simulador reproduziu os quatro estados de posição e da variável registrados pelo Profit. A hora e o rótulo continuam sendo os do contexto NTSL. Os números absolutos de `CurrentBar` são próprios de cada série de entrada. [Log completo antes/depois](sonda_persistencia_antes_depois.csv)

## Escopo da correção

Em `--avaliacao-pos-preenchimento`, uma entrada a mercado na abertura a partir de posição zerada pode executar a estratégia com a barra fechada anterior como contexto e a posição nova. Após uma avaliação bem-sucedida, o motor conserva as atribuições às variáveis escalares do subconjunto NTSL suportado. As cópias de arrays e janelas móveis são descartadas. As referências históricas continuam lendo o histórico gravado no fechamento de cada barra. Só as novas proteções elegíveis são avaliadas no OHLC da barra de entrada. A avaliação regular recebe a posição resultante.

A regressão de histórico verificou que a primeira barra continuou com o valor escalar `1`, apesar da atribuição adicional na abertura da segunda. O segundo fechamento guardou `3`; o valor de `n[1]` continuou `1`. A média de duas barras sobre `n` foi `2`, e a média sobre `Close` foi `105`. O contador de array avançou uma vez por fechamento. A proteção viva foi renovada pela mesma chave, sem segundo preenchimento. O teste do stop disparado da posição anterior, o teste de níveis calculados pela barra anterior e os casos de sessão, lacuna e entrada mista passaram.

## Caso sintético inspirado na v5.8

A sonda reproduz a transição `v_Estava_Posicionado → v_Barra_Ult_Saida`, com `p_Barras_Espera=3` e o critério `CurrentBar >= v_Barra_Ult_Saida + p_Barras_Espera`. Na barra 4, a avaliação extra, com contexto da barra 3, vê a compra aberta a 100. A proteção zera a 95 ainda na barra 4. O fechamento da barra 4 observa zero com `v_Estava_Posicionado=True` e grava a saída na barra 4. Os fechamentos das barras 4, 5 e 6 impedem a nova solicitação. O fechamento da barra 7 libera a compra, preenchida na abertura da barra 8.

No motor de referência, o fechamento da barra 4 via o estado anterior apagado, deixava a última saída em 0 e reabria na barra 5. O caso usa dados e regras de entrada sintéticos. A v5.8 completa ainda depende de replay no Profit. [Estado por barra](v5_8_espera_sintetica.csv) · [Preenchimentos sintéticos](v5_8_preenchimentos_sinteticos.csv) · [NTSL da sonda](sonda_espera_v5_8_sintetica_v1_0.ntsl) · [Candles sintéticos](candles_espera_sinteticos.csv)

## Seis replays da v5.7

| Pregão | Padrão antes → depois | Proteção legada antes → depois | Pós-preenchimento antes → depois | Cada um dos 8 indicadores |
|---|---:|---:|---:|---:|
| 21/10/2026 | 10/10 → 10/10 | 10/10 → 10/10 | 10/10 → **10/10** | 502/502 |
| 26/10/2026 | 8/12 → 8/12 | 11/12 → 11/12 | 12/12 → **12/12** | 463/463 |

Os denominadores de operações são do Profit. Os arquivos `execucoes.csv`, `candles.csv`, `eventos_ordens.csv` e `console.csv` ficaram idênticos byte a byte aos da rodada anterior em todos os seis replays, incluindo os modos padrão e legado. A #182 coincide no pós-preenchimento em 26/10, com compra de um contrato a 176.815 e saída a 176.465, ambas às 13:05 na exportação. [Matriz de operações](matriz_operacoes.csv) · [Matriz de indicadores](matriz_indicadores.csv)

WINZ26 em OHLC de 1 minuto, barra rotulada na abertura em `America/Sao_Paulo`, v5.7 original, lote 1, tick 5, R$ 0,20/ponto e custo, slippage e latência adicional zero. Volume financeiro e agressão publicada pelo Profit como referência explícita. Estratégia e plots rodaram com `--vwap-continuo-lacunas`. A comparação de indicadores usou `--aquecimento 63 --aquecimento-por-segmento`. Em 21/10, 565 barras de 09:00–18:24, zero duplicatas e 502 elegíveis a partir de 10:03. Em 26/10, 553 barras de 09:03–18:24, zero duplicatas e uma lacuna de 09:30–09:38; 463 elegíveis a partir de 10:42. As entradas preparadas e o CSV privado de operações foram conferidos contra os hashes da rodada anterior. [Configuração e fontes da rodada anterior](../WINZ26_v5_7_persistencia_20261026_v1/README.md)

A matriz de indicadores compara os plots da sonda instrumentada uma vez por pregão, compartilhados pelos três cenários de execução. A agressão injetada e as barras ausentes limitam a validação do pregão inteiro. Os CSVs compartilháveis preservam sequência e rótulos de contexto nas sondas e publicam resultados agregados nos dois replays reais. As exportações privadas e timestamps nativos de ordens continuam sendo as fontes necessárias para reproduzir a matriz ou confirmar a ativação e o cancelamento intrabar.

## Comandos

Windows 10, Python 3.11.3, pandas 3.1.1. O recorte de testes novos teve **2 falhas** antes e **2 aprovados** depois. A suíte no código corrigido teve **58 aprovados** e 12 avisos conhecidos de timezone do pandas.

```powershell
$testes = @(
  'tests/test_replay.py::test_sonda_persistencia_escalar_reproduz_estado_do_profit',
  'tests/test_replay.py::test_espera_sintetica_v5_8_reconhece_zeragem_no_candle_da_entrada'
)
py -3.11 -m pytest -q --tb=short @testes
py -3.11 -m pytest -q

# Para reproduzir as falhas em uma cópia separada da árvore corrigida:
git worktree add --detach $checkoutAnterior 68f1025526be87c52a5fa8cb8f9368dad06062ca
git -C $checkoutAnterior restore --source bcb09c9d68b672f0121327142235710497d1c8d9 --worktree -- estrategia.py
Push-Location $checkoutAnterior
try { py -3.11 -m pytest -q --tb=short @testes } finally { Pop-Location }

$evid = 'docs/colaboracao/evidencias/WINZ26_v5_7_persistencia_escalar_20261026_v2'
$anterior = 'docs/colaboracao/evidencias/WINZ26_v5_7_persistencia_20261026_v1'
py -3.11 estrategia.py --csv "$anterior/candles_sinteticos.csv" `
  --ntsl "$anterior/sonda_persistencia_simulador_v1_0.ntsl" --saida $saidaSonda `
  --segundos 60 --formato ohlc --avaliacao-pos-preenchimento --rastrear-ordens
py -3.11 estrategia.py --csv "$evid/candles_espera_sinteticos.csv" `
  --ntsl "$evid/sonda_espera_v5_8_sintetica_v1_0.ntsl" --saida $saidaEspera `
  --segundos 60 --formato ohlc --avaliacao-pos-preenchimento --rastrear-ordens

# Para cada dia e modo, usar o histórico completo e um destino novo.
# $modo recebe @(), @('--protecao-no-candle-entrada') ou
# @('--avaliacao-pos-preenchimento'). $inputs contém {"p_Lote":1}.
$comum = @('--segundos','60','--formato','ohlc','--tick','5','--valor-ponto','0.2',
           '--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas')
py -3.11 estrategia.py --csv $barrasPreparadas `
  --ntsl estrategias/execucao/Modelo_Unificado_Refatorado_v5_7.ntsl `
  --inputs $inputs --saida $replay @comum @modo --rastrear-ordens
py -3.11 estrategia.py --csv $barrasPreparadas `
  --ntsl estrategias/indicadores/indicador_paridade_modelo_unificado_v5_7_v1_0.ntsl `
  --saida $plotsMotor @comum
py -3.11 tools/comparar_paridade_mesmas_barras.py --profit-barras $barrasProfit `
  --profit-indicadores $plotsProfit --profit-operacoes $operacoesProfit `
  --barras-preparadas $barrasPreparadas --motor-indicadores "$plotsMotor/candles.csv" `
  --motor-candles "$replay/candles.csv" --motor-execucoes "$replay/execucoes.csv" `
  --data $dia --aquecimento 63 --aquecimento-por-segmento --saida $comparacao
```

O [TXT para o Gemini](fontes_gemini.txt) contém este README, os CSVs compartilháveis completos, as sondas usadas e a regressão relevante. [SHA-256 dos arquivos publicados](SHA256SUMS.txt)
