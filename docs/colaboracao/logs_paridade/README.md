# Logs de paridade da v5.7

Três CSVs gerados a partir das capturas de console autorizadas para publicação nesta pasta.

| Arquivo | Conteúdo |
|---|---|
| [log_paridade_v5_7.csv](log_paridade_v5_7.csv) | Captura inicial normalizada. 633 mensagens. |
| [paridade_console_varios_dias.csv.gz](paridade_console_varios_dias.csv.gz) | CSV integral compactado sem perdas. 30.155 mensagens em 54 datas, de 13/08 a 19/11/2026. |
| [paridade_console_resumo_por_dia.csv](paridade_console_resumo_por_dia.csv) | Contagens por data, arquivo de origem e tipo de evento. |

Os CSVs usam UTF-8 com BOM, delimitador ponto e vírgula, datas ISO e horas HH:MM. Os anexos se sobrepõem. As contagens são de mensagens. Para análise, preserve a ordenação de origem dentro de cada arquivo e bloco. No caso de 26/10, preserve os horários distintos de avaliação NTSL e execução.

## Extração no Windows

Na pasta deste README, com Python 3.11 ou posterior:

```powershell
py -3 -c "import gzip, shutil; src=gzip.open('paridade_console_varios_dias.csv.gz','rb'); dst=open('paridade_console_varios_dias.csv','xb'); shutil.copyfileobj(src,dst); dst.close(); src.close()"
Get-FileHash .\paridade_console_varios_dias.csv -Algorithm SHA256
```

SHA-256 do CSV descompactado: `8c02666ff28d4467d5764efb1d4702ac23ebe595a47718d9dd0c66214a9d8cd0`.

[Metodologia e caso de 26/10](paridade_console_metodologia.md) · [Formato da captura inicial](LEIA-ME_log_paridade_v5_7.md).
