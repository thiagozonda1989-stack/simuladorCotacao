# G1 e G2 · ajuste à grade de preços no Profit

Protocolo para **WINZ26, 26/10/2026, 1 minuto, Backtest OHLC**. A compilação e a execução de G1 e G2 no Profit estão pendentes. O motor de referência `d67a8731bfa1597b0bdfe4cc4064e6502822f81a` e os NTSLs anteriores foram preservados. [Revisão Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7116808762) · [Revisão Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7116822127)

## Aceite da prioridade experimental

A prioridade de zeragem integral de `--protecoes-ate-cancelar` fica **aceita no escopo experimental testado**. Nas rodadas 02 e 04, havia uma proteção elegível, limite ou stop-limit, e uma solicitação a mercado que zerava a posição. Houve uma venda de 1 contrato a +220 pontos, na abertura da barra de 10:55, com posição e pendências zeradas. O seletor OHLC/Tick a Tick não aparece nos prints anteriores, e os anexos não comprovam tipo da execução nativa, sequência subminuto ou cancelamento OCO. [Evidência nativa `7fca1200`](../WINZ26_v5_8_prioridade_protecao_profit_20261026_v1/README.md)

No motor, a zeragem na abertura retorna de `process_orders` antes de examinar outras ordens elegíveis na mesma barra. Por exemplo, uma entrada limite já elegível pode deixar de ser examinada antes da avaliação regular e ficar sujeita à política de validade existente. As sondas anteriores não incluem outra ordem além da proteção e da zeragem. A prioridade nessas combinações permanece pendente de caso próprio. G1 e G2 investigam somente a grade de preços de uma proteção isolada.

## Configuração no Profit

1. Abra **WINZ26**, período **1 min**, no Editor de Estratégias. Compile o NTSL correspondente como estratégia de execução.
2. Na aba **Backtest**, em **Execução**, selecione **OHLC**. Defina o período de análise de **26/10/2026 a 26/10/2026**, quantidade **1**, máxima **1**, custos **0**, slippage **0 ticks** e **Executar nos Limites** ativo. Deixe desativados o filtro de horário e a zeragem externa na janela de 10:51 a 10:58. Comece cada execução zerado e sem pendências.
3. Rode **G1 e G2 separadamente** no Backtest. Confira os valores no painel antes de rodar, pois o Profit pode carregar valores diferentes dos padrões do editor. Use o console Debug.

| Parâmetro | G1 | G2 |
|---|---:|---:|
| `p_Data` | 1261026 | 1261026 |
| `p_Entrada` | 1051 | 1051 |
| `p_Protecao` | 1052 | 1052 |
| `p_Cancela` | 1056 | 1056 |
| `p_Zera` | 1057 | 1057 |
| `p_Fim` | 1058 | 1058 |
| `p_Alvo` | **447** | — |
| `p_Gatilho` | — | **877** |
| `p_Limite` | — | **1000** |

A compra é solicitada no contexto **10:51** e a entrada de referência é a abertura registrada às **10:52**. Com posição comprada, o contexto **10:52** envia uma única proteção. G1 usa `SellToCoverLimit(BuyPrice + 447, 1)`. G2 usa `SellToCoverStop(BuyPrice - 877, BuyPrice - 1000, 1)`. O console registra `BuyPrice`, os preços solicitados e OHLC, posição e presença de pendência por avaliação. Não há saída a mercado concorrente. A limpeza só pode pedir cancelamento em **10:56** e zeragem em **10:57**. [NTSL G1](g1_alvo_grade_profit_v1_0.ntsl) · [NTSL G2](g2_stop_grade_profit_v1_0.ntsl)

## Como classificar a barra de 10:55

As barras de 10:51 a 10:58 são consecutivas. Os 32 valores OHLC conferem entre `barras_v58.csv` e a série privada preparada, com os hashes da rodada anterior. Nos rótulos 10:52–10:54, a maior máxima é +405 e a menor mínima é −425, insuficientes para tocar os preços em disputa. Em 10:55, a **abertura é +220**, a **máxima +445**, a **mínima −875** e o fechamento −260, em pontos desde a entrada. A abertura fica entre as duas proteções e coincide com o fechamento anterior. As barras de 10:56–10:58 também ficam fora dos níveis em disputa. [Barras relativas](barras_referencia.csv) · [Hashes das fontes privadas](../WINZ26_v5_8_prioridade_protecao_profit_20261026_v1/fontes_barras.csv)

| Hipótese | G1 · limite de venda +447 | G2 · gatilho −877 e limite −1000 |
|---|---|---|
| Tick mais próximo | +445 é tocado, previsão de saída +445 | −875 é tocado, previsão de saída −875 |
| Ajuste direcional em direção ao mercado | +445 é tocado | −875 é tocado |
| Ajuste direcional para longe do mercado | +450 fica acima da máxima | −880 fica abaixo da mínima |
| Preço bruto preservado | +447 fica acima da máxima | −877 fica abaixo da mínima |

Os preenchimentos previstos pressupõem execução por toque exato, com “Executar nos Limites” ativo. Confirme posição +1 e `HasPendingOrders=1` nas avaliações de 10:53 e 10:54. Se o CSV registrar venda às 10:55 e a avaliação já estiver zerada, compare o preço com o nível da hipótese. Se 10:55 ainda mostrar posição +1 e pendência 1, classifique como pendente sem execução observada nessa barra. Se a pendência desaparecer sem venda, investigue rejeição, expiração ou cancelamento pelo registro de ordens. O console só comprova a presença da pendência. Registre separadamente qualquer preenchimento tardio e as solicitações de limpeza. No simulador, a limpeza gera saída às 10:58, a −375 pontos.

Um preenchimento no extremo é compatível com ajuste ao tick mais próximo e com ajuste em direção ao mercado nesta janela. Compare com os controles nativos anteriores (+428 → +430 e −793 → −795) antes de inferir uma regra geral. A ausência de execução em 10:55 não distingue, sozinha, preço bruto de ajuste para longe do mercado. Para confirmar se o próprio toque exato é executável no Profit, rode controles separados com `p_Alvo=445` (G1) e `p_Gatilho=875, p_Limite=1000` (G2), especialmente se a sonda principal ficar pendente. Mantenha separados os rótulos do console e os horários exportados das execuções. [Matriz por hipótese](matriz_hipoteses.csv) · [Sete replays de controle no simulador](replays_simulador.csv)

## Exportações

Para cada execução, use um prefixo distinto, como `G1_447` ou `G2_877_1000`, e exporte:

1. Console Debug completo com `GRADE_G1` ou `GRADE_G2`, incluindo avisos e todos os blocos, na ordem original.
2. CSV de operações com ativo, horários de entrada e saída, preços, lados, quantidades e resultado. Exporte também o PDF do relatório.
3. CSV de barras de 26/10, cobrindo **10:51–10:58**, com data, hora e OHLC.
4. **Print de cada configuração com o seletor OHLC/Tick a Tick inteiro e OHLC selecionado**, junto do ativo, período de 1 min, data, quantidade, máxima, slippage, “Executar nos Limites” e parâmetros. Role até o topo do painel de Execução. Se não couber, faça dois prints da mesma execução e inclua o seletor no primeiro. A captura privada anterior `SONDA_S1_STOP_config.png` serve de exemplo para localizar o seletor.
5. Se disponível no próprio Backtest, histórico com ID, lado, quantidade, tipo, preços solicitados e aceitos, estado e horários de envio, disparo, preenchimento e cancelamento. Preserve os timestamps em sua resolução original.

**Teste específico do limite −894.** Em execução separada no Profit Replay, use o NTSL G2 com `p_Gatilho=793` e `p_Limite=894`. Se a interface fornecer a lista de ordens com o campo de limite aceito, exporte-a antes e depois do disparo quando possível, junto do console e das operações. Identifique os arquivos como **Replay** e calcule o limite relativo a `BuyPrice` dessa execução. Compare −894 solicitado com o limite aceito exibido, por exemplo −895 ou −890. Se a exportação expuser apenas preço médio executado ou uma ordem convertida sem o campo original, o limite aceito permanece indeterminado. O resultado de Replay caracteriza aquele ambiente.

## Conferência no simulador

Foram executados sete controles no motor de referência com `--protecoes-ate-cancelar` e `--avaliacao-pos-preenchimento`. Os dois níveis brutos e os dois níveis mais distantes ficaram pendentes em 10:55 e saíram por limpeza em 10:58. Os dois controles com o nível no extremo fecharam às 10:55. O teste local com limite bruto −894 exercita a configuração separada, sem evidência sobre o limite aceito no Profit. A conversão local adapta somente a formatação de `ConsoleLog`. Para reproduzir um perfil, use a série privada `WINZ26_20261026_profit_1min_privado.csv` e um destino novo:

```powershell
$fonte = [IO.File]::ReadAllText($arquivoNtslProfit)
$fonte = $fonte -creplace 'FloatToString\((\w+), 0\)', '($1)' -creplace ', clYellow\);', ');'
[IO.File]::WriteAllText($arquivoNtslLocal, $fonte)
# $inputs contém os parâmetros do perfil, por exemplo {"p_Gatilho":875,"p_Limite":1000}.
py -3.11 estrategia.py --csv $barrasPreparadas --ntsl $arquivoNtslLocal --inputs $inputs `
  --saida $saida --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --avaliacao-pos-preenchimento --rastrear-ordens --protecoes-ate-cancelar
py -3.11 -m pytest -q
```

A suíte local passou com 108 testes e 12 avisos de fuso do pandas já conhecidos. A coleta nativa será publicada após receber as exportações. [Manifesto dos arquivos](SHA256SUMS.txt) · [Fontes para o Gemini](fontes_gemini.txt)
