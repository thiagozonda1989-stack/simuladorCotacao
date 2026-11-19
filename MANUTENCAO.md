# Manutenção do simuladorCotacao

> A versão 0.5.0 adiciona documentação, schemas e estratégias NTSL. Ainda não há pacote executável 0.5.0 publicado; os hashes abaixo continuam correspondendo aos pacotes anteriores.

- Use a branch `main` como base para mudanças.
- Registre alterações relevantes no `CHANGELOG.md`. Em cada lançamento, atualize `VERSION` e `windows/version.rc`.
- Guarde os fontes, configurações, documentação e exemplos sintéticos pequenos no Git. Os CSVs brutos de captura ficam fora do repositório.
- O README contém os passos de execução e de geração do pacote Windows. O script de empacotamento usa as dependências fixadas em `windows/requirements.lock`.
- O replay OHLC é um simulador local. As limitações de compatibilidade com o Profit estão no README.

## Padrão de versionamento e publicação

1. Antes de alterar o programa, confira o estado de `main` no GitHub e preserve as mudanças locais em andamento.
2. Use versionamento semântico. Incremente a revisão para correções, a versão menor para funcionalidades compatíveis e a versão maior para mudanças incompatíveis. Atualize `VERSION`, `windows/version.rc`, `CHANGELOG.md` e as instruções afetadas no README.
3. Rode a verificação rápida e teste os fluxos modificados. Registre o resultado, o ambiente e o que depender de Windows ou Profit.
4. Gere o ZIP Windows a partir do código que será publicado. Confira o manifesto `SHA256SUMS.txt` e acrescente o hash do ZIP à tabela abaixo.
5. Faça um commit da versão e crie uma tag anotada `vX.Y.Z` nesse commit. Publique `main` e a tag no repositório oficial. Use atualização fast-forward.
6. Confira no GitHub se `main:VERSION` e a tag correspondem ao commit publicado. Ao entregar a versão, informe o link do código marcado e o link do ZIP.

```bash
versao="$(cat VERSION)"
git tag -a "v$versao" -m "simuladorCotacao v$versao"
git push --atomic origin main "refs/tags/v$versao"
git ls-remote origin refs/heads/main "refs/tags/v$versao" "refs/tags/v$versao^{}"
```

## Verificação rápida

A partir desta pasta, com as dependências do `requirements.txt` instaladas:

```bash
python -m pip install -r requirements.txt pytest
python -m pytest -q
python -m compileall -q .
python app.py --cli otimizar --csv exemplos/otimizacao_ntsl/candles.csv --ntsl exemplos/otimizacao_ntsl/estrategia.ntsl --config exemplos/otimizacao_ntsl/config.json --saida ../resultado-exemplo
```

## Pacotes originais

Os hashes identificam os ZIPs originais gerados para cada versão. O código e os scripts de build estão neste repositório. Os ZIPs com os binários são distribuídos à parte.

| Versão | Arquivo | SHA-256 |
|---|---|---|
| 0.1 | `simuladorCotacao-v0.1.zip` | `0abad8ddbc9685e3b9219cc631e13032ceca9dbcb3fa0e81ff0ebe9e5e72418c` |
| 0.2.0 | `simuladorCotacao-v0.2.0-win64.zip` | `713b91a3cbe9896d2d6c98b9762b8fed6d41bf2d7790d064c9625a35f1f35cbc` |
| 0.2.1 | `simuladorCotacao-v0.2.1-win64.zip` | `0db950b376db8f1c29479a0d19b0503d9a9c467d3e931dba869c408a5f894bc4` |
| 0.3.0 | `simuladorCotacao-v0.3.0-win64.zip` | `f7ba0a0a28ddaf15eae63ab51dc37ca6647d2a6e0fa4a87e8be59e2e383e1698` |
| 0.4.0 | `simuladorCotacao-v0.4.0-win64.zip` | `f4b3a1b84b0715cabfd8610ba7133304564fd5e1365fc5bedc9df07432c659cd` |
| 0.5.0 | `simuladorCotacao-v0.5.0-win64.zip` | `d6a3b2275d3a2fc5f8b930a56707832d2a035bffb643ab4e84b1c700535c416e` |
| 0.5.1 | `simuladorCotacao-v0.5.1-win64.zip` | `a54bf22952609891497afc16e315afc36d6db2b0068a41109e0c11ae346a9770` |
| 0.5.2 | `simuladorCotacao-v0.5.2-win64.zip` | `432ed173e2dfe1babcfc0362ac4c9d8d6171a6b1cd4d58423431058266f5c543` |
| 0.5.3 | `simuladorCotacao-v0.5.3-win64.zip` | `28f30032b9018977d45a395501c37fd77cfda80cef326a89f07c3516378d56f2` |
| 0.6.0 | `simuladorCotacao-v0.6.0-win64.zip` | `6c34b25f0e0461e5492a83a484c9eae2c48d92d84715e89ea521a14f11b2f1d9` |
| 0.7.0 | `simuladorCotacao-v0.7.0-win64.zip` | `ab94526cc662d4137fced7e43539e079876fc05666cecc906859ef911c139167` |
| 0.8.0 | `simuladorCotacao-v0.8.0-win64.zip` | `547b5bf2b652f5d99b660e64eda6499c0124a5fc9b05f3a0eb31d5f9a1330b2c` |
| 0.9.0 | `simuladorCotacao-v0.9.0-win64.zip` | `fde138b841cfe6347cbe707381f9cd003ff941ec043804aec7001b384ffa27f8` |
| 0.10.0 | `simuladorCotacao-v0.10.0-win64.zip` | `e68abd070780c692f7c42bcfe45a1244209271ebf61a96152e569af8e2be2196` |
| 0.11.0 | `simuladorCotacao-v0.11.0-win64.zip` | `23b670dd37056ada0a421599fb4c06f0f1aecd218a9cc30714320f6eebe068fe` |
| 0.12.0 | `simuladorCotacao-v0.12.0-win64.zip` | `7fcfaa9af0c2b74a2c2dcc042c2bf334ac8a01c872140b3b96c7c9dfc0883b99` |
