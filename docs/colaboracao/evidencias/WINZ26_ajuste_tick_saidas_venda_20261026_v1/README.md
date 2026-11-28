# Ajuste experimental ao tick em saídas de venda OHLC

Motor executado `db9ace693c9396d87198e0973d9708ddeb7668d4`. Motor de referência `d67a8731bfa1597b0bdfe4cc4064e6502822f81a`. Evidências G1/G2 `723838af659a8a1e3145ba22e00468dd8feae6d8`. [Revisão Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7117613311) · [Revisão Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7117647718)

## Escopo do motor

`--ajuste-tick-saidas-venda` é experimental, exclusiva do OHLC e desligada por padrão. Com ela ligada, `Engine.place` ajusta ao `--tick` mais próximo o preço do alvo limite e o gatilho do stop somente quando a ação cadastrada é `exit_long`. O limite do stop-limit, as entradas, as saídas de posição vendida e as ordens genéricas `SendOrder` com ação `net_long` ou `net_short` conservam os preços brutos. Isso inclui uma ordem genérica que venha a reduzir posição ao preencher. O ajuste incide sobre o preço absoluto e a grade parte de zero.

A comparação usa frações exatas a partir da representação decimal do preço e do tick. Um nível já na grade conserva o valor. No empate exato de meio tick, o preço solicitado é mantido e o caso entra no contador `empate_meio_tick`. Com `--rastrear-ordens`, há também um evento explícito. Um arredondamento que levaria a preço zero é rejeitado, respeitando a exigência de nível positivo. O gatilho ajustado e o limite bruto continuam sujeitos à regra de execução existente.

O ajuste ocorre no cadastro, antes de comparar se o reenvio corresponde à mesma ordem. Se nível efetivo, limite bruto e quantidade forem iguais, o motor conserva `eligible_at` e `triggered`. Se mudar o nível efetivo, a substituição recebe nova elegibilidade e reinicia o estado de disparo. Isso é uma hipótese do simulador. As sondas do Profit mostram o comportamento efetivo no toque e no preenchimento. A etapa interna do ajuste e a semântica de renovação nativa seguem em aberto.

Com a regra ligada, `eventos_ordens.csv` acrescenta `nivel_solicitado`, `nivel_efetivo`, `limite_solicitado`, `limite_efetivo` e `ajuste_tick`. As métricas registram as contagens `ajustado` e `empate_meio_tick` por solicitação, inclusive reenvios. Com a regra desligada, o formato anterior dos relatórios é preservado.

## Sondas nativas de venda e controles

| Caso | Solicitado | Profit | Simulador desligado | Simulador ligado |
|---|---:|---:|---:|---:|
| Controle 01 · alvo | +428 | 10:55, +430 | 10:55, +428 | 10:55, +430 |
| G1 · alvo | +447 | 10:55, +445 | 10:58, −375, limpeza | 10:55, +445 |
| Controle 03 · gatilho | −793 | 10:55, −795 | 10:55, −793 | 10:55, −795 |
| G2 · gatilho | −877 | 10:55, −875 | 10:58, −375, limpeza | 10:55, −875 |

Preços em pontos relativos à entrada. Os dois controles de saída a mercado permaneceram em +220 pontos, na abertura de 10:55, com ambos os modos da flag. Nos testes, a normalização funciona com proteção persistente e avaliação pós-preenchimento. A prioridade de zeragem na abertura continua executando uma única saída a mercado. [Matriz com horários, estado e níveis brutos/efetivos](matriz_sondas.csv)

As barras de WINZ26 em 26/10/2026, 1 minuto, fuso America/Sao_Paulo, conferem no recorte 10:51–10:58. A abertura de 10:52 é a referência de entrada. Às 10:55, a abertura é +220, a máxima +445, a mínima −875 e o fechamento −260. [OHLC relativo](barras_referencia.csv) · [Insumos e hashes](insumos_privados.csv)

## Regressões executadas no Windows

Foram executados **32 replays privados** em 16 cenários pareados, com a opção desligada e ligada. Todos usaram a persistência de proteções e as mesmas bases preparadas, parâmetros e configuração de cada cenário anterior. A v5.7 foi rodada em padrão, proteção legada, pós-preenchimento, pós-preenchimento com continuidade e pós-preenchimento com continuidade/entrada pela lacuna. A v5.8 foi rodada em reinício, continuidade e continuidade/entrada pela lacuna, com o pregão anterior no histórico e corte de 63 barras por segmento na comparação de auditoria. [Matriz privada agregada](regressoes.csv)

| Estratégia | 21/10 | 26/10 |
|---|---|---|
| v5.7 | 10/10 nos cinco cenários | 8/12 no padrão, 11/12 no legado e 12/12 nos três cenários pós-preenchimento, com a #182 exata |
| v5.8 | 7/7 nos três cenários | 8/10 no reinício e 9/10 com continuidade, incluindo a combinação com entrada pela lacuna |

Nenhuma solicitação em escopo precisou de ajuste e houve zero empates nesses 16 cenários. Com a opção desligada, os sete arquivos por cenário ficaram idênticos à referência (112 comparações). Com ela ligada, execuções, candles, console e NTSL ficaram idênticos byte a byte. O rastreio difere apenas pelas cinco colunas novas e as métricas JSON e HTML diferem apenas pela configuração e contadores. Os seis relatórios privados de comparação v5.8 ficaram idênticos com a opção ligada ou desligada. O replay mínimo da referência também foi executado e repetido nos dois modos, com o mesmo padrão de equivalência. [Replay mínimo](replay_minimo.csv)

A saída v5.8 de 10:15 permanece ambígua no OHLC. O caso 2 da lacuna continua como divergência conhecida. A suíte local passou com **130 testes**, incluindo 22 novos casos, e os 12 avisos de fuso já conhecidos. O CLI rejeitou tick a tick com código 2. [Testes](../../../../tests/test_ajuste_tick_saidas_venda.py)

## Reprodução

Use destinos novos. As bases, parâmetros e estratégias são as da rodada anterior. Para as sondas, use os NTSLs do protocolo e transforme somente a formatação de console. Os controles 01 e 03 usam a sonda de prioridade com o painel 428/793/101. [Rodada da persistência das proteções](../WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1/README.md#reprodução) · [NTSLs G1/G2](../WINZ26_grade_precos_g1_g2_20261026_v1/README.md)

```powershell
$base = @('--formato','ohlc','--segundos','60','--tick','5','--valor-ponto','0.2','--rastrear-ordens','--protecoes-ate-cancelar')
$paridade = @('--volume-financeiro-ntsl','--agressao-referencia-injetada','--vwap-continuo-lacunas')
$flag = @('--ajuste-tick-saidas-venda') # Repetir com $flag = @().
# $modo contém uma das configurações da matriz, incluindo --avaliacao-pos-preenchimento quando aplicável.
py -3.11 estrategia.py --csv $barras --ntsl $ntsl --inputs $inputs --saida $saida @base @paridade @modo @flag
py -3.11 -m tools.comparar_v5_8 --data $dia --aquecimento 63 --barras-profit $barrasProfit `
  --operacoes-profit $operacoesProfit --console-profit $consoleProfit --barras-preparadas $barras `
  --candles-simulador "$saida/candles.csv" --console-simulador "$saida/console.csv" `
  --execucoes-simulador "$saida/execucoes.csv" --saida "$saida.comparacao.json"
# Para sondas, omita @paridade, use --avaliacao-pos-preenchimento e copie a formatação de console para a versão local.
py -3.11 estrategia.py --csv exemplos/replay_minimo/candles.csv --ntsl exemplos/replay_minimo/estrategia.ntsl `
  --saida $saidaMinimo --segundos 5 --formato ohlc --tick 5 --rastrear-ordens @flag
py -3.11 -m tools.publicar_ajuste_tick_saidas_venda --replays $replays --referencia $referencia `
  --operacoes-v57 $operacoesV57 --evidencias-grade $grade --evidencias-prioridade $prioridade --saida $publicavel
py -3.11 -m pytest -q
```

O extrator usa os nomes da matriz anterior para as pastas de referência. Use `${dia}-v57-${modo}-${off|on}`, `v58-${dia}-${modo}-${off|on}`, `minimo-ref`, `minimo-off`, `minimo-on`, `g1-off/on`, `g2-off/on`, `prioridade-${perna}-${mercado}-${off|on}`, `g3-bruto/grade` e `g4-bruto/grade` na rodada atual. Para a conversão de console local, substitua `FloatToString(expr, 0)` por `(expr)` e retire o argumento de cor `clYellow` das chamadas. Os dados brutos e os artefatos completos dos replays ficam no Windows.

## Sondas de compra

G3 e G4 estão prontas para compilar no Profit. A compilação e execução nativas ficam pendentes. O controle do gatilho e limite aceitos da sonda 03 está documentado à parte no procedimento de captura. [G3](g3_alvo_compra_grade_profit_v1_0.ntsl) · [G4](g4_stop_compra_grade_profit_v1_0.ntsl) · [Passo a passo de captura](captura_profit.md) · [Fontes para o Gemini](fontes_gemini.txt) · [Manifesto](SHA256SUMS.txt)
