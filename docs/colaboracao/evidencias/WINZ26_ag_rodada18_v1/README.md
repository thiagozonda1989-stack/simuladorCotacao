# Rodada 18 · busca genética de estratégias WINZ26

**Data:** 24/11/2026, America/Sao_Paulo. Pesquisa local no Windows. PR #2 em rascunho.

O protocolo e as bases preparadas foram congelados antes da seleção. A rodada compara estratégias dentro do mesmo grupo de amostra, quantidade, granularidade e regras de replay. Os parâmetros foram selecionados usando somente o desenvolvimento. O grupo de um minuto tem 20 pregões para comparação exploratória. Os grupos rápidos têm um pregão exploratório cada. A reserva final permaneceu fechada.

## Versões e rastreabilidade

| Referência | SHA |
|---|---|
| Motor que executou as ordens OHLC | `db9ace693c9396d87198e0973d9708ddeb7668d4` |
| Base do PR e fonte das versões do piloto | `d2429a4549b497fcdbdb0cfef04e02c01d6be997`, branch `research/piloto-ias-etapa1` |
| Fonte das versões Pullback e dos perfis publicados | `3e2720016e83436c7a648eac51f134de4e68393a`, branch `research/estrategia-fora-amostra-sintetico` |
| Primeiro congelamento | `abc426fac7bc53ced271a9d161e35fb41f5697ce` |
| Roteiro executado e orçamento congelado | `c86d30918571839c00e1e8033360d8f5fa811a02` |

O AG é o de `simulador.optimize`. O roteiro habilitou a busca financeira isolada e aplicou as restrições ao calcular aptidão. Ele exporta os candidatos sem rodar a validação automaticamente. A regra de ordens permanece em `estrategia.py`. O inventário mantém SHA-256 bruto e SHA-256 do texto normalizado para LF. As correspondências de conteúdo evitam repetir a mesma versão das duas branches ou uma cópia de replay do Windows. Os NTSLs de produção permanecem preservados. [Inventário das estratégias](inventario_estrategias.json) · [Protocolo](protocolo.json).

## Dados e adequação

- **1 minuto.** A captura de barras WINZ26 tem 30.964 registros em 59 pregões, com OHLC, Trades, contratos e volume financeiro. O saldo de agressão vem do indicador nativo, unido apenas por timestamp e OHLC idênticos. A VWAP foi reconstruída com o preço médio aproximado por barra, calculado do volume financeiro dividido por contratos e R$ 0,20. A série nativa de VWAP do indicador permanece como referência externa. A base congelada cobre os 19 pregões de desenvolvimento da rodada 16 e os 20 conhecidos posteriores. As datas completas e as lacunas por pregão estão no protocolo e na cobertura. O dia 19/11 possui 461 barras nessa fonte e uma discrepância entre suas exportações às 16:40. Os dias 21 e 26/10 já eram recortes dedicados à paridade e ficaram fora da comparação desta rodada.
- **5 segundos.** A fonte nativa `indicadorv7_claude.csv` tem 30.001 barras em cinco dias. Entraram 11 e 13/11 no desenvolvimento e 16/11 na comparação. O dia 10/11 começa às 13:53 e o 12/11 às 09:26. A fonte traz OHLC, Trades e agressão compradora/vendedora por barra. Falta Volume nativo por barra para a v4.1. A profundidade válida aparece em duas barras do trecho de 16/11 e em nenhuma dos dois dias de desenvolvimento. A v4.2 e a v4.3 foram avaliadas com seu caminho original de book opcional.
- **1 segundo.** A fonte nativa `indicadorv6_claude.csv` tem 133.685 barras em cinco dias. Entraram 29/10 e 03/11 no desenvolvimento e 04/11 na comparação. 28/10 começa às 16:48 e 30/10 tem 445 minutos. A profundidade válida ocupa de 0 a 3,1% das barras dos pregões selecionados. O topo está disponível em praticamente todo o recorte. A v4.0 depende de book profundo e ficou bloqueada. As duas estratégias 1C usam o caminho de book opcional da configuração original. O saldo da v3.0 foi reconstruído pelo engine a partir da agressão compradora e vendedora exportadas.
- **Relógio subminuto.** As fontes têm minuto e ID ordinal de barra. 2.199 minutos completos da fonte de 1 segundo e 2.499 da fonte de 5 segundos coincidem integralmente com o OHLC de 1 minuto do WINZ26. O pareamento corrobora o contrato. O replay usa barras OHLC na sequência de IDs. Nas bordas de minutos parciais, duração em segundos é aproximada. A sequência dos negócios dentro de uma barra e a prioridade de fila continuam indeterminadas.
- **Negócios, Preços e Ofertas.** A cobertura publicada de cinco pregões de negócios identifica 21/10 e 26/10 como elegíveis após segmentar lacunas. Os relatos registram empates de milissegundo e inversões na ordem física. O número de captura resolve a ordem do arquivo, com evidência insuficiente para garantir a ordem de bolsa de todos os empates. Preços e Ofertas retroativos carecem de carimbo útil para sincronizar todo o book. Somente a informação contemporânea ao negócio pode alimentar um cruzamento causal. Nenhum preço ou oferta retroativos foram injetados nas bases da busca.
- **Outros contratos.** A saída do ranking é restrita a WINZ26. A busca no Windows e nas exportações inventariadas ficou sem um grupo WDO com fonte e cobertura comparáveis. O último pregão de cada grupo rápido e os 20 pregões de um minuto já tinham uso anterior no projeto. Não há avaliação inédita publicada nesta rodada.

[Cobertura, cabeçalhos e hashes](cobertura.json) · [Cobertura anterior dos negócios](../../ETAPA1_COBERTURA_WIN_PREGOES.csv) · [Auditoria de sincronização](../../ETAPA1_EVIDENCIAS.md).

## Baselines, seleção e métricas

1. O baseline usa os inputs originais no modo do replay, com lote 2 quando o NTSL expõe essa configuração. A v5.8 usa `p_Exec_Tick=0` em OHLC. O lote original ficou em perfil separado. Pullback v1.0–v1.3 fixa um contrato nas ordens e tem ranking próprio. Os perfis publicados foram reavaliados como controle separado quando havia parâmetros comparáveis à versão. O arquivo comparativo usa a classe `padronizado_lote_modo` quando o perfil apenas repete o original com o lote fixado. A leitura do perfil publicado da Pullback v1.0 foi complementada na consolidação, com o replay controlado separado e sem mudar a seleção já congelada. A opção de falha de rompimento da v1.7 ficou desligada por decisão da rodada 16.
2. Todas as comparações principais usam R$ 0,50 por contrato e lado, 1 tick de slippage conforme o tipo de ordem, grade de 5 pontos, R$ 0,20 por ponto e contrato e zero latência adicional. Ordens são elegíveis na próxima barra. A regra OHLC de stop-limit, o preenchimento conservador quando ambas as proteções tocam e o encerramento de posição no fim do pregão seguem o motor. Os modos experimentais de proteção e avaliação pós-preenchimento ficam desligados no ranking principal.
3. Os grupos de 1 minuto e 5 segundos receberam até 24 candidatos por geração por três gerações. No grupo de 1 segundo, o custo do replay 1C motivou orçamento pré-definido de oito candidatos por duas gerações para todas as versões do grupo. A semente foi 18024 e a probabilidade de mutação por gene foi 0,28. A reutilização de genótipos reduz avaliações únicas. Os valores fixos e grades vêm dos inputs efetivamente usados por cada fonte. Uma configuração fica apta a partir de uma operação fechada por pregão de desenvolvimento em média, com drawdown da curva líquida do AG até R$ 1.500 no grupo de um minuto ou R$ 1.000 nos grupos rápidos. Dentro desses limites, a aptidão maximiza líquido após custos. O ranking exploratório usa o candidato já escolhido e serve para diagnóstico; os resultados exploratórios não voltam para o AG.
4. O relatório usa P/L líquido por operação encerrada, taxa de acerto com numerador de resultados positivos e denominador de todos os encerramentos, fator de lucro líquido, pior dia, drawdown realizado desde equity zero, duração mediana e P90. A média por pregão inclui dias sem operações. O drawdown reportado soma operações fechadas; o filtro do AG usa a curva de eventos agregados por barra e inclui o débito da entrada quando ocorre. Dias com posição ou preenchimentos fora do lote são checados pelo pareador. Distância para 45% é em pontos percentuais. Distância para R$ 3 mil é por dia.

A referência específica de **R$ 5.745, fator 2,22 e 43 operações** da v5.7 continua sem exportação nativa vinculada. Nesta rodada a v5.7 foi executada com o perfil disponível do simulador, dois contratos e custos declarados. O baseline inclui também lote 5 e o perfil separado de pós-preenchimento de um contrato. [Relatório anterior](../WINZ26_v5_7_otimizacao_rodada17_v1/README.md).

## Resultado da rodada

Foram executadas 20 versões, com 1.228 avaliações únicas por versão somadas na busca principal. Dezenove versões selecionaram candidato dentro dos limites do desenvolvimento. A Scalper Micro HFT v3.0 executou o baseline e 15 combinações em 1 segundo, mas ficou sem operação encerrada elegível para seleção. O inventário tem também 180 registros de cópia, 34 de coleta, instrumentação ou exemplo fora do ranking e 14 fontes bloqueadas.

| Grupo | Líder entre os candidatos congelados | Líquido | Média/dia | Acertos | Drawdown | Δ original |
|---|---|---:|---:|---:|---:|---:|
| 1 min · 2 contratos · 20 pregões | Scalper v1.1 | −R$ 58 | −R$ 2,90 | 49/83 (59,0%) | R$ 456 | +R$ 1.740 |
| 1 min · 1 contrato · 20 pregões | Pullback v1.0 | R$ 766 | R$ 38,30 | 38/84 (45,2%) | R$ 129 | +R$ 744 |
| 5 s · 2 contratos · 1 pregão | Scalper v2.3 | R$ 66 | R$ 66 | 7/30 (23,3%) | R$ 72 | +R$ 174 |
| 1 s · 2 contratos · 1 pregão | 1C Antecipado v1.0 | −R$ 306 | −R$ 306 | 8/31 (25,8%) | R$ 306 | −R$ 4 |

Na tabela de todos os perfis de 1 minuto com 2 contratos, a v5.8 original em OHLC liderou o recorte conhecido com **R$ 1.902**, 76/147 acertos (51,7%), R$ 95,10 por pregão e drawdown de R$ 2.352. A v5.8 otimizada liderou o desenvolvimento com R$ 2.764, contra R$ 342 da original. Nos 20 conhecidos, a otimizada teve **−R$ 2.022**, 36/86 acertos e drawdown de R$ 2.056. A diferença para o baseline passou de +R$ 2.422 no desenvolvimento para −R$ 3.924 na comparação.

Todos os candidatos de 1 minuto com 2 contratos ficaram no negativo na comparação exploratória. A Scalper v1.1 reduziu a frequência de 14,55 para 4,15 operações por dia e o drawdown de R$ 2.152 para R$ 456. Apesar de 14,04 pontos percentuais acima da referência de acerto, ficou R$ 3.002,90 abaixo do objetivo líquido diário. A Pullback v1.0 de um contrato ficou 0,24 p.p. acima da referência de acerto e R$ 2.961,70 abaixo da referência diária. Nenhum perfil atingiu R$ 3 mil líquidos em um pregão. A diferença entre grupos de tamanho e resolução distintos não entra na seleção. Não há ranking validado fora da amostra nesta rodada.

Os recursos registraram pico de **1.916,6 MiB** de RSS somado por busca e mínimo de **41.031,9 MiB** de RAM disponível. A CPU total média ficou entre 26,5% e 64,8% conforme a versão e a concorrência entre grupos. O maior tempo de busca foi 171,03 s para a 1C v1.0, com 5,26 avaliações/minuto. A soma dos tempos de busca foi 540,96 s e o relógio registrou cerca de 11 min 55 s desde o congelamento final até o último resultado, incluindo replays e sobreposição dos processos. Os logs registram contadores de paginação da máquina e a variação de uso do arquivo de paginação.

A suíte passou com **133 testes** e 12 avisos preexistentes de pandas. O teste novo verificou que a busca financeira isolada respeita o filtro de aptidão e não executa a fase de teste. O motor de ordens, o compilador NTSL e as 20 fontes de estratégia ficaram idênticos aos respectivos SHAs de referência.

## Recursos e comandos

A máquina tem 12 núcleos físicos, 24 lógicos e aproximadamente 63,9 GiB de RAM. O piloto mediu 4/8/12 processos para 5 segundos e 8/16/24 para 1 minuto; oito tiveram a maior vazão nos dois recortes. O piloto de 1 segundo mediu 4/8 sobre a v3.0. O replay reutiliza arrays de séries e o buffer de histórico em cada processo. Foram enviados apenas campos necessários à coorte de desenvolvimento. O checkpoint do AG grava estado, semente e dados no Windows por geração e a cada minuto. Ao repetir o comando no mesmo destino, o roteiro procura pelo checkpoint do mesmo perfil e pula versões com resultado consolidado. Os logs registram RSS somado do processo e filhos, memória livre, CPU percentual da máquina, contadores de páginas do sistema e tempo. O pico somado pode contar páginas compartilhadas mais de uma vez.

```powershell
git worktree add --detach <pesquisa> 3e2720016e83436c7a648eac51f134de4e68393a
git worktree add --detach <rodada> c86d30918571839c00e1e8033360d8f5fa811a02
Set-Location <rodada>
$base = @('--dados', <pasta-privada>, '--pesquisa', <pesquisa>,
          '--saida', <saida-privada>, '--fontes-extras', <pasta-local-opcional>)
py -3.11 -m pytest -q
py -3.11 tools/rodada18_ag.py preparar @base
py -3.11 tools/rodada18_ag.py baseline @base
py -3.11 tools/rodada18_ag.py piloto @base --filtro Modelo_Unificado_Refatorado_v5_7 --workers 8 16 24
py -3.11 tools/rodada18_ag.py piloto @base --filtro modelo_scalper_v2_1 --workers 4 8 12
py -3.11 tools/rodada18_ag.py piloto @base --filtro modelo_scalper_micro_hft_v3_0 --workers 4 8
py -3.11 tools/rodada18_ag.py busca @base --workers 8
py -3.11 tools/consolidar_rodada18_ag.py --privado <saida-privada> --pesquisa <pesquisa> --evidencias docs/colaboracao/evidencias/WINZ26_ag_rodada18_v1
```

As planilhas e os logs completos de preenchimento ficam no Windows. Os agregados versionados contêm métricas de coorte e de pregão, intervalos de parâmetros, candidatos, sementes e estatísticas de recursos. [Resultados por perfil](comparativo.csv) · [Ranking por grupo](ranking.json) · [Logs sanitizados](recursos.json).
