# Rodada 16 · Protocolo congelado antes do replay histórico

Referência v1.5 em `521f96e2574f501e6d1598ef154fcd30baa77517`. O perfil escolhido está no `v1_5.json` de `5de205abcaec295953c43476d7ee071529a78d39`. Relatório das rodadas 14/15 em `ea1a11e1892b6d4b4e9d51957a824ba784e3c5a1`. Motor OHLC `db9ace693c9396d87198e0973d9708ddeb7668d4`, com os mesmos arquivos de execução presentes no head inicial `ff79ee0b189d1f1933ec69f96e2525b970a1bc8a`. [Rodadas 14/15](../estrategia_pullback_adaptativo_v1/README.md)

## Decisão de consenso

[Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7141228984) propôs começar a checar em K ≥ J e reenviar após lacunas com uma trava. [Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7141228499) propôs checar até J e bloquear após lacunas, com duas formulações para a igualdade de 1 tick. Thiago aprovou janela máxima inclusiva, fim do adendo após lacuna para a posição corrente e desigualdade estrita além da margem.

- Em S, o fechamento que emite a entrada, grave **High[1]** para compra e **Low[1]** para venda, pois são os níveis que a referência rompe. Se o histórico não os disponibilizar, a posição segue sob gestão v1.5. O nível fica congelado até a saída.
- A ordem de entrada a mercado preenche na abertura de E. Em E, **K=1 apenas no fechamento**. Avaliação extra com rótulo S tem K=0 e não pode emitir o adendo. A grade ensaia J ∈ {1,2} e tolerância T ∈ {0,1} tick. Use apenas os fechamentos 1 ≤ K ≤ J. Compra falha com `Close < nível − T × 5`. Venda falha com `Close > nível + T × 5`.
- Lacuna ou troca de pregão entre S e o fechamento observado encerra o adendo para a posição. Se a ordem a mercado solicitada antes da lacuna for cancelada na retomada, a estratégia retoma a gestão original no fechamento da próxima barra observada enquanto houver posição. A candidata não reenvia a decisão cancelada.
- No candle de decisão, alvo e stop já elegíveis são processados antes da avaliação do fechamento. A regra adversa do motor permanece quando ambos tocam, assim como a execução de stop-limit em gap. Se seguir posicionado, horário e prazo da v1.5 têm prioridade sobre o adendo na classificação. Um fechamento marcado como falha cancela pendências de proteção e solicita somente a zeragem de 2 contratos, com preenchimento elegível na abertura seguinte e 1 tick de slippage. As proteções não são renovadas nesse fechamento. A espera, o limite diário e as entradas originais continuam na v1.5.

### Casos discriminantes executados em série sintética

| Cenário | Leituras que dão resultados diferentes | Resultado aprovado |
|---|---|---|
| Compra, nível 1.000, J=2, fechamentos 995, 1.010, 1.010 | A janela máxima pede saída no primeiro fechamento. A janela que começa em K=2 não pede saída nesse percurso. | Solicita após K=1. |
| Compra, nível 1.000, J=2, fechamentos 1.015, 1.010, 995 | K ≥ J pede saída após o terceiro fechamento. A janela máxima terminou em K=2. | Nenhuma saída por adendo. |
| Compra, nível 1.000, T=1, fechamento 995 | A fronteira inclusiva dispara a −5. A estrita só dispara em 990 ou abaixo na grade. | Mantém a posição a 995. A venda é o espelho, com 1.005 e 1.010. |
| Compra, fechamento adverso, próxima barra ausente e fechamento da retomada recuperado | O motor cancela a solicitação anterior na lacuna. A trava reenviaria e zeraria a 985 no exemplo. | Retoma a gestão v1.5, sem reenvio pelo adendo. |
| Máxima rompida 1.000, máxima do sinal 1.030, fechamento de entrada 1.010 | Usar nível da barra do sinal dispara. Usar o nível efetivamente rompido mantém a posição. | Usa 1.000. |

## Amostra, seleção e métricas

- A/B em WINZ26, OHLC de um minuto, 2 contratos, R$ 0,20 por ponto/contrato, R$ 0,50 por contrato/lado e slippage 1 tick de 5 pontos. Ordem só na barra seguinte e demais regras padrão da rodada 15. As opções de pós-preenchimento e persistência de proteções ficam desligadas na comparação principal. Trace de ordens ligado para auditoria. O manifesto fixa as datas a partir do perfil publicado. Nenhum candle de pregão adicional entra como aquecimento acidental.
- Controle obrigatório `v1.7 desativada × v1.5`, com igualdade de preenchimentos, requisições/eventos, trace e métricas, conferência do perfil da v1.5 e sem alteração no motor ou na fonte v1.5.
- Uma variante só passa o desenvolvimento se tiver delta líquido total, delta pareado e delta nas saídas antecipadas pareadas estritamente positivos, resultado médio da referência negativo nas operações cortadas, e drawdown não superior ao da referência. Variantes sem saídas antecipadas pareadas ficam fora. Se mais de uma passar, maior delta total, menor drawdown e depois menor janela e menor tolerância. Se nenhuma passar, registre a rejeição e use a referência como controle dos 20 conhecidos. O confronto dos 20 é exploratório sem reseleção. Uma melhoria exploratória exige o mesmo sinal nos deltas total e pareado e drawdown até o da v1.5. A reserva, se elegível e ainda inédita para essa estratégia, é um relatório separado, com candidato congelado antes de qualquer replay.
- Conte vitórias como líquido positivo e inclua pregões zerados no denominador. Use drawdown da curva líquida por saída em ordem cronológica desde zero, mediana e percentil 90 linear de saída menos entrada, contagens, média por operação, líquido total e por pregão. Reporte 45% de acerto e R$ 3 mil líquidos por dia como referências, com contagem de dias que atingem a segunda.
- Pareie data, candle da entrada, direção, quantidade e preço de entrada. Nas antecipadas pareadas, perda evitada ou amenizada é a redução da parte negativa. Vencedora cortada é a redução da parte positiva da referência. O delta das operações sem par é o efeito de composição/frequência, com contagens e líquidos separados para novas e suprimidas. Bootstrap por pregão com os parâmetros da rodada de referência.

Os preços de mercado, os fills completos e os CSVs privados permanecem no Windows. A comparação mede a estratégia no motor OHLC. A semântica nativa de prioridades simultâneas da v1.7 no Profit continua sem validação própria.
