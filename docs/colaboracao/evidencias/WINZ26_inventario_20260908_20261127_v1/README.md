# Inventário WINZ26 · 08/09 a 27/11/2026

A exportação do coletor contém **30.001 candles de 1 minuto em 56 pregões**, entre **08/09/2026 10:51** e **27/11/2026 18:24**, no horário de São Paulo. O original tem 2.351.452 bytes, usa Windows-1252 e separador ponto e vírgula. O SHA-256 é `146dcab678fcc9a6259333bf526693ec7fd758518d581bef01847ce12446826b`. [Manifesto](manifesto.json) · [Cobertura por pregão](pregoes.csv)

| Mês de 2026 | Pregões | Janela completa | Só diferença na borda | Com lacuna interna |
|---|---:|---:|---:|---:|
| Setembro | 17 | 0 | 0 | 17 |
| Outubro | 21 | 10 | 1 | 10 |
| Novembro | 18 | 10 | 8 | 0 |
| **Total** | **56** | **20** | **9** | **27** |

A janela de referência é **09:00–18:24**, inclusive. Lacuna interna é um minuto ausente entre a primeira e a última barra observada. Há **1.269 minutos faltantes internamente**, com máximo de **9 consecutivos** em 26/10. Uma diferença na borda pode refletir horário real da primeira barra ou recorte da exportação. As contagens descrevem o conteúdo exportado. Ausência de barra, por si só, não comprova ausência de negócios.

## Colunas e integridade

O cabeçalho repete o nome do coletor nos cinco plots. O script identifica as colunas pela ordem do indicador NTSL versionado: **Trades**, **Quantity** em contratos, **Volume** financeiro, **saldo de agressão** e **VWAP diária**. A desambiguação ocorre em memória. As cinco séries coincidem na comparação por timestamp com a coleta anterior. O nome do indicador sugere WINZ26, e a sobreposição corrobora essa identificação no trecho comum. As linhas do CSV não carregam ticker. [Fonte do indicador](../../../../estrategias/indicadores/indicador_coleta_reserva_winz26_1min_v1_0.ntsl)

A ordem física é decrescente. Não houve timestamps inválidos ou duplicados, linhas duplicadas, campos ausentes, OHLC inconsistentes ou preços fora da grade de 5 pontos. Em todas as barras, Trades foi menor ou igual a Quantity e o preço médio implícito pelo volume financeiro ficou dentro do OHLC. A VWAP diária bate com o acumulado calculado a partir dos candles, dentro de 0,01 ponto, em 29.679 barras. As 322 exceções estão em **06/10**, quando a nova fonte só começa às **12:37**. A VWAP desse trecho coincide com a fonte anterior na sobreposição e depende do acumulado anterior ao recorte.

## Comparação com a coleta anterior

Os **19.786 timestamps comuns** coincidem em OHLC e nas cinco séries. Há **10.215 barras exclusivas** na nova fonte, incluindo 154 adicionais em 01/10 e 20 datas que não constavam na exportação anterior, sendo 17 de setembro e os pregões de **25, 26 e 27/11**. As **215 barras exclusivas da fonte anterior** pertencem a 06/10. Preserve as duas fontes para manter a cobertura disponível.

Em 25–27/11, cada pregão tem **562 barras consecutivas, de 09:03 a 18:24**. Esses dias têm dados disponíveis para auditoria de elegibilidade. O inventário ainda não confirma a abertura histórica de cada um. A janela completa nesta tabela indica completude temporal no CSV, sem atribuir elegibilidade para validação formal. **Nenhum replay foi executado**. As datas já expostas no piloto de 23–24/11 continuam excluídas da futura amostra formal. [Resultado e regras do piloto](../WINZ26_piloto_rodada20_v1/README.md)

O cruzamento usa minuto e fuso da exportação para uma fonte com contrato identificado. O CSV agrega a contagem e quantidade de negócios por barra. Uma junção com negócios individuais exige identificar o contrato e agregar os eventos por minuto. O arquivo não traz ofertas ou timestamps de eventos para uma junção com o livro de ofertas.

## Reprodução

```powershell
py -3.11 -m tools.inventariar_coletor_win --fonte $coletaNova --referencia $coletaAnterior --cache $cacheLocal --saida $pastaAgregados
py -3.11 -m pytest -q
```

O cache local reutiliza resultados quando os dois SHA-256 já foram processados. A suíte passou com 147 testes, incluindo o mapeamento do cabeçalho repetido e o cruzamento de lacunas, bordas e diferenças entre campos. O GitHub recebe o inventário e os agregados por pregão. Os CSVs originais ficam no Windows. [SHA-256 dos artefatos](SHA256SUMS.txt)
