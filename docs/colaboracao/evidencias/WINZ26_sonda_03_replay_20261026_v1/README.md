# Sonda 03 · preços aceitos no Profit Replay

**Parecer aprovado para a execução no Replay.** A ordem de venda stop-limit de WINZ26 ajustou ambos os preços ao ser registrada em 26/10/2026. Em pontos relativos à entrada desta execução, o gatilho solicitado de **−793** foi registrado a **−795**, e o limite solicitado de **−894** foi registrado a **−895**. A ordem executou 1 contrato a **−795**. O Backtest OHLC anterior já confirmava esse resultado relativo de execução; os níveis aceitos naquele modo continuam sem registro nativo.

## Fontes e associação

- `SONDA_03_LOGS_REPLAY.png` mostra o ConsoleLog e os eventos nativos da automação simulada da mesma sonda. As horas das avaliações são os rótulos NTSL de barras de 1 minuto. Os horários da coluna Eventos têm milissegundos. A captura mostra avaliações de 10:51 a 10:58, com duas avaliações no primeiro rótulo. O recorte textual preserva a ordem visual. [Eventos transcritos](eventos_replay.csv)
- `SONDA_03_ORDENS_REPLAY.csv` cobre o pregão de 26/10/2026. Tem 26 colunas e duas ordens executadas de 1 contrato, com identificadores distintos. A ordem de venda aparece como `Limite` no registro final e com `Preço Stop` vazio. A ordem nativa `Venda Stop Criada` no print registra os dois níveis. A associação usa o modo simulador, ativo, lado, quantidade, sequência, limite e preço médio. [Derivado da lista de ordens](ordens_replay.csv)
- Os originais permanecem no Windows. O inventário registra os hashes, e os derivados mostram preços relativos à entrada do Replay. Foram removidos os valores absolutos, a identificação da conta e do operador, os identificadores de ordem e o nome da carteira. [Inventário](inventario_anexos.csv)

## Comparação com o Backtest OHLC

| Campo | Replay · ordem simulada | Backtest OHLC anterior · controle 03 |
|---|---:|---:|
| Gatilho solicitado | −793 | −793 |
| Limite solicitado | −894 | −894 |
| Gatilho registrado na criação | −795 | — |
| Limite registrado na criação | −895 | — |
| Preenchimento relativo à entrada | −795 | −795 |
| Quantidade executada | 1 | 1 |
| Hora de execução na fonte | 10:55:51.381 no painel Eventos | 10:55:00 no CSV de operações |

Em pontos relativos à compra de cada rodada. A compra do Replay ocorreu 95 pontos acima da compra do Backtest. No Replay, a distância entre gatilho e limite passou de 101 pontos solicitados para 100 pontos registrados. Os dois preços coincidem com os ticks de 5 pontos mais próximos neste exemplo. Como ambos os ajustes foram para baixo, esta sonda isolada também é compatível com arredondamento para baixo. O registro nativo comprova que ambos os valores já estavam na grade no evento de criação, sem identificar qual componente aplicou a transformação. [Backtest OHLC de referência](../WINZ26_grade_precos_g3_g4_03_profit_20261026_v1/README.md)

O ConsoleLog solicitou a proteção às **10:53:02.024**, sob o rótulo **10:52**, com posição comprada de 1 contrato. Às **10:53:02.524**, a linha `Venda Stop Criada` mostra o limite no campo Preço e o gatilho na mensagem. A lista final registra **10:53:02.671** na coluna Criação da venda e conserva o mesmo limite. A posição e a pendência ficaram em 1 nas avaliações com rótulos 10:53 e 10:54, e em 0 na avaliação de 10:55, que foi logada às 10:56:02.130. O preenchimento de saída a −795 consta do painel às 10:55:51.381 e confere com o preço médio exportado. A notificação nativa de posição zerada aparece às 10:55:51.081. A diferença entre horários e ordenação do painel e do CSV não estabelece a ordem interna entre notificações. A coluna Última Atualização da lista usa 23/11/2026 e não foi usada como hora de execução; não há registro isolado do instante do disparo.

## Conclusão

A evidência fecha a captura pedida para a sonda 03 no **Replay**. A coincidência a −795 em ambos os modos deixa em aberto o limite aceito pelo **Backtest OHLC**. A flag experimental do simulador conserva o limite bruto nesse modo e a captura nova não exige alteração do motor. Outra execução idêntica no Replay só repetiria a mesma evidência. Para confirmar o valor em OHLC seria necessário o detalhe da ordem do próprio Backtest. [Fonte NTSL de referência](../WINZ26_v5_8_protecoes_ate_cancelar_20261026_v1/sonda_prioridade_mercado_protecao_profit_v1_0.ntsl) · [Fontes para o Gemini](fontes_gemini.txt) · [Manifesto](SHA256SUMS.txt)
