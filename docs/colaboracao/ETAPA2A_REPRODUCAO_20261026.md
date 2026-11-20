# Etapa 2A — reprodução de 26/10/2026

Referência metodológica: `e3f474453e4186c9df83392af9f6fd7284a3e234`. Recorte congelado: WINZ26, 26/10/2026, candles fechados de 1 minuto avaliados em OHLC, timestamp na abertura em `America/Sao_Paulo`, v5.7 original, um contrato, custos e slippage zerados. Não houve ajuste orientado pelo resultado.

Os CSVs originais e todos os derivados com preços permanecem privados no Windows. Este documento e `ETAPA2A_MATRIZ_PARIDADE_20261026.csv` contêm somente método e agregados autorizados.

## Execução e testes

O checkout de execução partiu exatamente de `e3f474453e4186c9df83392af9f6fd7284a3e234`. As únicas alterações funcionais desta rodada estão nos validadores e comparadores versionados, acompanhadas de testes. A suíte foi executada no Windows com Python 3.11, sem `PYTHONUTF8=1`: **38 testes passaram**, com 12 avisos conhecidos de compatibilidade futura do pandas nos testes de fuso. O SHA publicado da rodada fica registrado no histórico do PR e no retorno da execução, evitando uma referência circular dentro do próprio commit.

## Fontes e limitações antes da estratégia

Os três arquivos privados, apesar de conservarem `20261021` no nome, contêm também 26/10:

| Fonte | Conteúdo filtrado de 26/10 | SHA-256 |
|---|---:|---|
| `profit_WINZ26_20261021_barras_1min.csv` | 553 barras, 09:03–18:24 | `3726e7dd9a821a109120765e4115e6eb352079e9402d9370ae7565ac9555bb2a` |
| `profit_WINZ26_20261021_indicadores_v5_7.csv` | 553 linhas e os oito plots | `76b79ef839ab6b142a0976c7c3ef1a6b7bb7dc2d013434551e861c892a56b946` |
| `profit_WINZ26_20261021_posicao.csv` | 12 operações completas | `549e22dea388e5f4e272bc906ac3309e9e88a1de7f53e6184ded5796dbe64479` |

O arquivo de operações identifica o ativo como WINZ26. Os CSVs de barras e plots não possuem coluna de ativo; neles a identificação depende do arquivo e da exportação. Não há timestamps duplicados. OHLC está em pontos WIN, `Trades` em negócios inteiros, `Quantity` em contratos inteiros e `Volume` em reais. O comparador mantém `Quantity` e Volume financeiro em campos distintos.

A cobertura do Profit começa às 09:03 e contém uma ausência contínua de 09:30 a 09:38. Não há evidência suficiente no CSV agregado para distinguir minutos sem negócios de histórico não exportado. A mesma janela é uma lacuna de 607,998 segundos na captura de negócios local, portanto o estado acumulado que atravessa esse intervalo deve ser tratado com cautela.

## Cenário controlado: mesmas barras do Profit

O motor recebeu exatamente as 553 barras do Profit. A entrada privada preparada tem SHA-256 `adace8f7c2ab691c3686e9e85533e2094b4bfd957ff7d377b3854fcb90fd92b9`. Os parâmetros são os mesmos do recorte de 21/10: ATR 14, regime 50, desvio VWAP 2,1, z-score 1,5, stop 350, alvo 450, mínimo de 100 negócios, lote 1 e offset 5.

O z-score usa Volume financeiro no modo explícito de paridade. A VWAP do motor é derivada de `Volume/(Quantity*R$ 0,20)` e, portanto, aproximada. O saldo de agressão é o plot do Profit injetado como referência diagnóstica; esta rodada não prova reconstrução independente da agressão.

Após excluir 63 candles de aquecimento, foram comparadas 490 barras, a partir de 10:15:

| Série | Dentro da tolerância | Primeira diferença |
|---|---:|---|
| VWAP | 0/490 | 10:15; Profit 170349,07, motor 170286,265095 |
| Desvio padrão | 490/490 | nenhuma |
| ATR | 490/490 | nenhuma |
| Média ATR | 463/490 | 10:15; Profit 635,35, motor 657,358648 |
| Saldo de agressão | 490/490 | nenhuma, com referência Profit injetada |
| Z-score de Volume | 490/490 | nenhuma |
| Regime | 487/490 | 10:20; Profit 0, motor 1 |
| Sinal candidato | 490/490 | nenhuma |

A diferença da VWAP é compatível com estado anterior não presente na exportação iniciada às 09:03 e com a aproximação por Volume financeiro, mas o CSV não permite separar essas causas. Apesar das diferenças em VWAP, Média ATR e três regimes, os candidatos coincidiram integralmente: sete vendas, nove compras e 474 zeros.

O motor emitiu dez ordens de entrada e produziu dez operações. O Profit exportou 12 operações. Oito viagens de ida e volta coincidiram exatamente:

| Entrada | Saída | Lado | Entrada pts | Saída pts |
|---|---|:---:|---:|---:|
| 11:27 | 11:28 | C | 171435 | 171885 |
| 12:38 | 12:40 | V | 178070 | 178420 |
| 12:59 | 13:03 | V | 178020 | 177570 |
| 14:04 | 14:06 | C | 177775 | 178225 |
| 14:41 | 14:43 | V | 177280 | 176830 |
| 14:47 | 14:48 | C | 176820 | 176470 |
| 14:52 | 14:55 | C | 177275 | 176925 |
| 16:28 | 16:30 | C | 179605 | 180055 |

A primeira diferença verificável de preenchimento é a compra das 13:04: ambos entram em 177565, mas o Profit sai no mesmo minuto em 177215 e o motor sai às 14:01 em 177210. Esses valores correspondem, respectivamente, ao gatilho de stop e ao limite de stop da v5.7. Sem o histórico nativo de ordens do Profit não é possível afirmar se a causa é a regra de preenchimento stop-limit, a sequência intrabar ou outro evento de ordem. Como o motor permaneceu posicionado, as operações seguintes também deixam de ser alinháveis uma a uma até a saída.

As posições foram apenas reconstruídas das execuções e divergem a partir dessa operação. Não existe série nativa da posição por candle no material exportado.

## Cenário separado: captura local de negócios

A fonte imutável `win_negocios_26102026.csv` tem SHA-256 `1d89701275b3ecb247303961d643a6c33641638de5fd0f804ad3b9a4e77941e4`. Foram lidos 4.676.480 negócios e 9.458.490 contratos; três linhas são inválidas. O agregado possui 551 barras, de 09:03 a 18:31, 18 minutos ausentes, 152 lacunas acima de cinco segundos e 88 barras afetadas. Existem 809.711 negócios sem lado agressor reconhecido, 17,31% do total, e 174 barras têm evidência de ambiguidade no primeiro ou último milissegundo. `Sequencia` ordena a captura, mas não prova ordem de bolsa.

Contra o Profit há 550 minutos comuns. O Profit tem exclusivamente 11:23, 11:29 e 11:31; a captura local tem exclusivamente 18:31. `Trades` e `Quantity` já divergem às 09:03. A primeira divergência de OHLC aparece às 09:40: abertura 166950/166990 e fechamento 166845/166915, Profit/local. Apenas 24 de 550 contagens de `Trades` e `Quantity` coincidem.

Somente 95 barras locais pertencem a segmentos contínuos com novo aquecimento de 63 barras. Nelas, o primeiro candidato divergente ocorre às 14:40, Profit venda e local zero. O cenário local produziu oito operações, contra 12 no Profit, e nenhuma coincidência exata. A primeira operação local é uma venda de 10:01–10:03; a primeira do Profit é uma compra de 11:27–11:28. Esse resultado não deve ser usado para diagnosticar execução antes de resolver cobertura, contagens e OHLC.

## Comandos reproduzíveis

```powershell
py -3.11 tools\preparar_paridade_profit_barras.py `
  --barras <privado>\profit_WINZ26_20261021_barras_1min.csv `
  --indicadores <privado>\profit_WINZ26_20261021_indicadores_v5_7.csv `
  --data 2026-10-26 `
  --saida <privado>\WINZ26_20261026_profit_1min_privado.csv `
  --manifesto <privado>\manifesto_preparacao.json

py -3.11 estrategia.py `
  --csv <privado>\WINZ26_20261026_profit_1min_privado.csv `
  --ntsl estrategias\execucao\Modelo_Unificado_Refatorado_v5_7.ntsl `
  --saida <privado>\execucao_v5_7_referencia `
  --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --inputs <privado>\inputs_v5_7_paridade.json `
  --volume-financeiro-ntsl --agressao-referencia-injetada

py -3.11 estrategia.py `
  --csv <privado>\WINZ26_20261026_profit_1min_privado.csv `
  --ntsl estrategias\indicadores\indicador_paridade_modelo_unificado_v5_7_v1_0.ntsl `
  --saida <privado>\indicadores_motor_referencia `
  --segundos 60 --formato ohlc --tick 5 --valor-ponto 0.2 `
  --volume-financeiro-ntsl --agressao-referencia-injetada

py -3.11 tools\comparar_paridade_mesmas_barras.py <argumentos privados> `
  --data 2026-10-26 --aquecimento 63 `
  --saida <privado>\comparacao_mesmas_barras_v2.json

py -3.11 tools\preparar_paridade_win.py `
  --negocios <privado>\win_negocios_26102026.csv `
  --data 2026-10-26 --saida <privado>\WINZ26_20261026_local_1min.csv `
  --manifesto <privado>\manifesto_preparacao.json

py -3.11 tools\comparar_paridade_profit_win.py <argumentos privados> `
  --data 2026-10-26 --aquecimento 63 `
  --saida <privado>\comparacao_profit_local_v2.json

py -3.11 -m pytest -q
```

## Conclusão e evidência mínima pendente

O procedimento de 21/10 foi reproduzido sem otimização. Com as mesmas barras, sinais candidatos continuam equivalentes, mas somente 8 de 12 operações do Profit coincidem exatamente com 8 das 10 do motor. A primeira divergência operacional ocorre no stop da compra das 13:04. Na captura local, zero operações coincidem e a primeira divergência já está nos dados da barra inicial.

A menor evidência capaz de decidir a causa da divergência controlada é o histórico nativo de ordens do Profit para 13:04, contendo criação, tipo, gatilho, limite, horário do disparo, preço e horário do preenchimento, cancelamentos e vínculo OCO. Para fechar posição, falta também a série nativa por candle; até lá ela permanece explicitamente derivada.

## Adendo — proteção no candle da entrada

Os logs de console publicados depois desta matriz permitiram isolar a primeira divergência na elegibilidade da proteção. O contrafactual opt-in passa de 8 para 11 correspondências exatas em 26/10, sem alterar as 10 de 10 de 21/10. O diagnóstico, os testes e a pendência da segunda avaliação intrabar estão em [ETAPA2A_DIAGNOSTICO_PROTECAO_20261026.md](ETAPA2A_DIAGNOSTICO_PROTECAO_20261026.md) e [ETAPA2A_MATRIZ_PROTECAO_20261026.csv](ETAPA2A_MATRIZ_PROTECAO_20261026.csv).
