# Cronograma de entrega · 25/11 a 04/12/2026

**Prazo inicial: 10 dias corridos, de 25/11 a 04/12/2026, contando 25/11 como dia 1. Entrega até 21:00 de 04/12.** Horários de Brasília. A agenda de 23 horas é uma estimativa de trabalho humano, sujeita à disponibilidade. Replays, CI e revisões podem correr em paralelo. As publicações anteriores registram marcos e verificações, sem apontamento suficiente para estimar horas históricas.

## Estado inicial · rodada 20

- **Simulador 65/100.** 141 testes locais aprovados e CI aprovado no último fechamento consultado. A lacuna intradiária pode reiniciar o contador de entradas da v5.8 e deixar o aquecimento global ativo enquanto as médias locais ainda estão incompletas. O controle por data escalar preservou os fills da v5.8 original nos 20 conhecidos. Qualquer correção deve ser comparada separadamente, com testes em dados conhecidos.
- **Estratégias 35/100.** A v5.8 original e a Scalper v1.1 otimizada são os perfis congelados. Nos 20 conhecidos, tiveram respectivamente +R$ 1.902 e −R$ 58 líquidos. A v5.8 otimizada fica como diagnóstico. O resultado nativo de R$ 5.745 da v5.7 permanece pendente da exportação correspondente.
- **Dados 60/100.** 24/11 tem 565 barras WINZ26 de 1 minuto e é candidato ao piloto. O último parecer registra zero replays inéditos. O bloqueio é a cobertura de 23/11 para aquecimento, com divergência na mínima e no fechamento às 18:14. A abertura também está pendente para uso de 23/11 como sessão avaliada.

[Decisão da rodada 20](https://github.com/thiagozonda1989-stack/simuladorCotacao/blob/a80ca00f50914dcacc624f1a2068b00c963f51b4/docs/colaboracao/evidencias/WINZ26_decisao_elegibilidade_rodada20_v2/README.md) · [Painel interativo](https://thiagozonda1989-stack.github.io/simuladorCotacao/colaboracao/ACOMPANHAMENTO_INTERATIVO.html)

## Agenda diária

Em dias úteis, 18:30–19:00 para triagem e insumos, 19:00–20:30 para execução ou revisão e 20:30–21:00 para registro e próximos passos. No fim de semana, 10:00–11:30 para revisão e documentação. A captura deve usar candles fechados e pode ser feita no primeiro horário disponível no Profit.

| Dia | Data | Horário | Entrega verificável |
|---:|---|---|---|
| 1 | 25/11 · qua | 18:30–21:00 | Thiago exporta WINZ26 de 23/11, candles fechados de 1 min e Time & Sales nos recortes 09:00:00–09:03:59 e 18:14:00–18:14:59. Codex inventaria os arquivos locais. |
| 2 | 26/11 · qui | 18:30–21:00 | Codex cruza as fontes e hashes, confere 86 barras de aquecimento e publica elegibilidade. Claude revisa lacunas e Gemini revisa cobertura e amostra. |
| 3 | 27/11 · sex | 18:30–21:00 | Fechar a decisão pré-replay. Se elegível, executar uma comparação descritiva em 24/11 com perfis congelados e excluir a sessão examinada da validação formal. Se bloqueado, registrar a evidência faltante e seguir com as entregas independentes. |
| 4 | 28/11 · sáb | 10:00–11:30 | Auditar os logs do piloto ou o bloqueio, revisar os testes de contador e aquecimento e atualizar painel e manifesto. |
| 5 | 29/11 · dom | 10:00–11:30 | Revisar checklist de instalação e reprodução, custos, limitações do motor e rastreabilidade das fontes. |
| 6 | 30/11 · seg | 18:30–21:00 | Consolidar dados inéditos elegíveis, hashes e separação entre aquecimento, piloto e avaliação formal. Manter quaisquer correções como cenários independentes em dados conhecidos. |
| 7 | 01/12 · ter | 18:30–21:00 | Executar a validação formal se a lista de 20 pregões completos puder ser congelada. Caso contrário, publicar cobertura e contagem faltante com a reserva preservada. |
| 8 | 02/12 · qua | 18:30–21:00 | Revisar os resultados ou o bloqueio. Relatar líquido, acerto com denominador, operações, drawdown, pior dia e concentração. Fechar também o status da execução nativa v5.7. |
| 9 | 03/12 · qui | 18:30–21:00 | Rodar a suíte e o replay sintético, conferir CI, instruções e pacote Windows conforme MANUTENCAO.md. Revisar a publicação e o painel. |
| 10 | 04/12 · sex | 18:30–21:00 | Entregar versão, pacote, hashes e relatório com entregas e pendências, confirmar links e registrar decisão sobre aprovação formal. |

## Critérios de fechamento

- **Entrega técnica em 04/12.** Versão identificada, instruções reproduzíveis, suíte e CI registrados, pacote Windows conferido, hashes, relatório e painel publicados. Decisões sobre release e integração à main devem constar no PR.
- **Validação formal.** O protocolo exige 20 sessões inéditas completas e ao menos 80 operações por perfil. Sessões de piloto ficam fora. O prazo de entrega não muda o corte amostral. Se não houver histórico elegível suficiente, entregar o resultado descritivo disponível ou o bloqueio, com o protocolo congelado e a validação formal explicitamente pendente.
- **Metas de desempenho.** Reportar a distância até 45% de acerto e R$ 3 mil líquidos por pregão. Marcar as notas do painel apenas quando houver evidência de avanço.
- **Revisão diária.** Registrar horário real, tempo investido, marco, descoberta, impacto no prazo, responsável e evidência no fechamento. Thiago cuida das capturas no Profit, Codex executa e publica, Claude revisa o motor, Gemini revisa os dados e o protocolo, e ChatGPT consolida as decisões.
