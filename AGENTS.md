# Diretrizes para agentes

Este repositório reúne o simulador local e estratégias NTSL do projeto ProfitRTD.

1. Preserve dados brutos e códigos confirmados no Profit. Nunca altere um arquivo de estratégia publicado; crie uma nova versão.
2. Antes de testar, inventarie arquivos, colunas, período, resolução, duplicidades, ordem temporal, lacunas e cobertura de Negócios, Preços e Ofertas.
3. Separe claramente: compilação no Profit, compatibilidade com o subconjunto NTSL do simulador, replay executado e resultado observado.
4. Não trate replay OHLC como Tick a Tick. Declare custos, slippage, latência, fila e ambiguidades intrabar.
5. Use divisão cronológica. Ajuste, validação e teste final devem usar pregões distintos.
6. Dados originais são imutáveis. Dados derivados precisam de versão, schema, hash da fonte e registro do processamento.
7. Não publique arquivos de mercado reais neste repositório. Use somente schemas e exemplos sintéticos.
8. Toda alteração funcional deve incluir teste de regressão e atualização da documentação.
