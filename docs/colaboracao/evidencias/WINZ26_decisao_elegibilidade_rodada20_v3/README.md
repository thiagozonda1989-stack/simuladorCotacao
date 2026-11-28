# Rodada 20 · conferência subminuto de WINZ26 em 23/11/2026

**Decisão em 28/11/2026: OHLC fechado de 18:14 corroborado. Piloto de 24/11 ainda bloqueado pela abertura de 23/11.** Nenhum replay da reserva foi executado. O motor permanece em `db9ace693c9396d87198e0973d9708ddeb7668d4` e os perfis, flags e critérios são os do [protocolo congelado](../WINZ26_decisao_elegibilidade_rodada20_v2/protocolo.json). A avaliação formal exige 20 pregões inéditos completos e pelo menos 80 operações por perfil. [Decisão anterior](../WINZ26_decisao_elegibilidade_rodada20_v2/README.md)

## Cobertura e reconciliação

A captura do Profit fornecida por Thiago contém 10.106 linhas de 23/11, com OHLC e os cinco campos do coletor. São 171 rótulos distintos, sem linhas idênticas nem campos vazios. Apesar do gráfico em segundos, a coluna `Data` termina no minuto. O CSV tem dois recortes físicos, cada um em ordem decrescente, com um salto entre eles. O primeiro vai de 09:05 a 09:03. O segundo vai de 18:15 a 15:28. As 9.935 repetições do rótulo de minuto correspondem a várias barras no mesmo minuto. Nenhum segundo foi reconstruído a partir da posição da linha.

O cruzamento usou o minuto como chave. Dentro de cada bloco contíguo, a última linha física fornece a abertura, a primeira fornece o fechamento, os extremos vêm de todas as linhas e as séries aditivas são somadas. Dos 165 minutos com 60 linhas, os 165 coincidem em OHLC, Trades, Quantity, volume financeiro e agressão com a coleta de 1 minuto. O manifesto contém contagens e diferenças, com os três hashes de entrada na ordem dos respectivos papéis. Os originais ficam no Windows. [Manifesto agregado](manifesto.json)

| Janela de São Paulo | Linhas subminuto | Resultado |
|---|---:|---|
| 09:00–09:02 | 0 | Os dois CSVs de 1 minuto e a captura subminuto começam em 09:03. Thiago observou o gráfico começar a formar candles às 09:03:32. O arquivo não preserva o segundo exato nem traz a lista de negócios para confirmar a ausência de negociações antes de 09:03. |
| 09:03 | 30 | O agregado coincide com OHLC, quatro séries aditivas e VWAP de 1 minuto. |
| 09:04 | 60 | O agregado coincide em todos os campos. |
| 09:05 | 6 | Recorte parcial. |
| 18:13 | 60 | OHLC e séries aditivas coincidem. |
| 18:14 | 60 | OHLC e séries aditivas coincidem. A baixa e o fechamento contestados aparecem na última barra em ordem cronológica do recorte. |
| 18:15 | 33 | Recorte parcial. |

Às 18:14, a captura histórica de 1 minuto é a referência para o OHLC fechado. Em relação à referência anterior, a mínima cai 10 pontos e o fechamento cai 45 pontos, com abertura e máxima iguais. A referência anterior termina nesse candle. A coincidência do agregado e o extremo na última barra subminuto são compatíveis com uma captura anterior feita antes do fechamento.

A VWAP nativa do gráfico subminuto difere em 164 dos 165 minutos com 60 linhas, com diferença de −9,79 pontos às 18:14. A VWAP da coleta de 1 minuto coincide, dentro de 0,01 ponto, com volume financeiro acumulado dividido por quantidade acumulada × R$ 0,20 em todas as 562 barras de 23/11 e as 565 de 24/11. Esse controle valida a consistência interna da série de 1 minuto. A origem da diferença entre as periodicidades segue indeterminada e a série subminuto não entra no aquecimento.

## Pendência para o piloto

O pregão de 23/11 tem as 86 barras finais consecutivas necessárias ao aquecimento. Para completar a auditoria da abertura, falta confirmar em **Negócios / Times & Trades** de **WINZ26 em 23/11/2026, 09:00:00–09:03:59** o primeiro negócio e a ausência ou existência de registros anteriores. A exportação precisa preservar timestamp com segundos, preço e quantidade. Uma captura da consulta histórica com ativo, data, faixa e primeira linha visíveis também documenta o que o Profit mostra. O horário de 09:03:32 permanece identificado como observação do operador. O cruzamento independente de 24/11 com a exportação histórica de 1 minuto continua pendente para a auditoria formal. [Parecer Claude](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7152416269) · [Parecer Gemini](https://github.com/thiagozonda1989-stack/simuladorCotacao/pull/2#issuecomment-7152494885)

## Reprodução

```powershell
py -3.11 -m tools.conferir_subminuto_rodada20 --subminuto $barrasSegundos --minuto $coletaMinuto --referencia $referenciaMinutoAnterior --cache $cacheLocal --saida $manifesto
py -3.11 -m pytest -q
```

A auditoria lê somente fontes identificadas pelo conjunto de hashes. Entradas já processadas reutilizam o resultado agregado do cache local. A suíte local teve 143 testes aprovados. Os novos testes cobrem a ordem física, o OHLC reconstruído, a divergência de VWAP e a rejeição de duplicata exata. [Hashes dos artefatos](SHA256SUMS.txt)
