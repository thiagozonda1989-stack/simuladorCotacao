# Prompt para a IA responsável pelo simulador

Copie o conteúdo abaixo para iniciar o trabalho com outra IA.

---

Você é responsável pela evolução do repositório `thiagozonda1989-stack/simuladorCotacao`.

O repositório agora também contém as estratégias NTSL desenvolvidas no projeto ProfitRTD em `estrategias/execucao` e os indicadores de diagnóstico/dataset em `estrategias/indicadores`. Leia primeiro `AGENTS.md`, `DIRETRIZES_PROJETO.md`, `estrategias/README.md`, `estrategias/catalogo_estrategias.csv`, `docs/DADOS_ENTRADA_PROFITRTD.md` e `docs/ARQUITETURA_UNIFICACAO.md`.

Contexto:

- O objetivo é validar operações curtas no mini-índice com preço, volume, agressão, negócios e livro.
- Os dados reais permanecem fora do Git. O schema canônico está em `schemas/dados_integrados_v1.schema.json` e os CSVs publicados são sintéticos.
- As fontes reais são separadas em Negócios, Preços e Ofertas e precisam ser relacionadas sem informação futura.
- O simulador atual executa NTSL por candle, não por tick, e não reproduz custos, fila, latência ou reprocessamento intrabar.
- O leitor identifica segmentos/lacunas, mas o `Engine` NTSL hoje reinicia estado apenas na mudança de pregão. Isso permite que histórico ou ordem atravesse uma lacuna.
- Parte das estratégias não compila no subconjunto do simulador por falta de `VWAP`, `CalcTime`, `AgressionVolBalance`, funções de book, `Plot5+`, `PlotText` e `SetPlotColor`.
- As estratégias de indicadores usam muitos plots para exportar colunas; não enviam ordens.

Sua missão é propor e implementar a unificação incremental sem alterar silenciosamente a semântica das estratégias confirmadas no Profit.

Ordem obrigatória:

1. Faça inventário de arquivos, schemas, períodos, colunas e estratégias.
2. Execute os testes existentes e registre a linha de base.
3. Crie testes para lacunas, duplicidades, stop/target na mesma barra, stop-limit com gap, posição parcial, reversão e mudança de pregão.
4. Corrija o uso de `segmento` no motor antes de ampliar a otimização.
5. Implemente as funções NTSL faltantes com testes unitários e exemplos de paridade.
6. Crie um pipeline versionado para integrar Negócios, Preços e Ofertas por junção temporal causal, registrando idade dos snapshots e qualidade.
7. Adicione custos, slippage e latência configuráveis ao replay por candle.
8. Projete um motor event-driven separado para Tick a Tick; não misture seus resultados com o replay OHLC.
9. Adicione walk-forward com múltiplas janelas e teste final intocado.
10. Gere um relatório de paridade entre Profit e simulador por sinal, ordem, execução e posição.

Restrições:

- Preserve os arquivos NTSL publicados. Mudanças criam novas versões.
- Não use informação futura em joins, features, targets ou preenchimentos.
- Não publique dados reais de mercado.
- Não declare compatibilidade ou teste que não tenha sido executado.
- Resultado bruto, resultado líquido, drawdown e ambiguidades devem aparecer separadamente.
- Uma estratégia que compila no simulador ainda precisa de validação no Profit.

Entregue inicialmente um plano por etapas, uma matriz de compatibilidade por estratégia, os testes de regressão propostos e a menor alteração segura para impedir ordens e indicadores de atravessarem lacunas.

---
