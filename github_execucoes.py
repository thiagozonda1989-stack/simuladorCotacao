"""Publicação opt-in de pacotes como anexos de pré-releases do projeto."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

REPOSITORY = "thiagozonda1989-stack/simuladorCotacao"
API = f"https://api.github.com/repos/{REPOSITORY}"
PREFIX = "execucao-simulador-"


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and redirected.host != req.host:
            redirected.remove_header("Authorization")
        return redirected


def request(url, method="GET", data=None, headers=None):
    token = os.environ.get("SIMULADOR_GITHUB_TOKEN", "").strip()
    req = Request(url, data=data, method=method, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "simuladorCotacao",
        "X-GitHub-Api-Version": "2022-11-28", **(headers or {}),
    })
    if token:
        req.add_unredirected_header("Authorization", f"Bearer {token}")
    try:
        return build_opener(SafeRedirect()).open(req, timeout=45)
    except HTTPError as error:
        status = error.code
        error.close()
        raise ValueError(f"GitHub retornou HTTP {status}. Confira o acesso ao repositório e as permissões do token.") from None


def api(url, method="GET", data=None):
    with request(url, method, json.dumps(data).encode() if data is not None else None,
                 {"Content-Type": "application/json"} if data is not None else None) as result:
        return json.load(result)


def publish(package, summary):
    if not os.environ.get("SIMULADOR_GITHUB_TOKEN", "").strip():
        raise ValueError("Configure SIMULADOR_GITHUB_TOKEN com acesso de escrita ao repositório do projeto.")
    size = package.stat().st_size
    if size >= 2*1024**3:
        raise ValueError("O ZIP excede o limite de 2 GiB por anexo do GitHub.")
    tag = PREFIX + uuid4().hex
    keys = ("schema", "id", "versao", "modo", "inicio", "fim", "estado", "parada", "segundos", "indicadores")
    metadata = {key: summary[key] for key in keys if key in summary}
    release = api(API + "/releases", "POST", {
        "tag_name": tag, "name": "Execução " + summary["id"], "draft": True, "prerelease": True,
        "body": json.dumps(metadata, ensure_ascii=False), "make_latest": "false",
    })
    release_id = int(release["id"])
    # O rascunho só é publicado depois de o ZIP estar completo.
    url = f"https://uploads.github.com/repos/{REPOSITORY}/releases/{release_id}/assets?"
    with package.open("rb") as stream, request(url + urlencode({"name": "execucao.zip"}), "POST", stream,
                                               {"Content-Type": "application/zip",
                                                "Content-Length": str(size)}) as response:
        asset = json.load(response)
    if asset.get("state") != "uploaded" or asset.get("size") != size:
        raise ValueError("O GitHub não confirmou o upload completo.")
    published = api(f"{API}/releases/{release_id}", "PATCH", {"draft": False, "make_latest": "false"})
    return published["html_url"]


def catalog(page):
    entries = api(f"{API}/releases?per_page=30&page={page}")
    results = []
    for release in entries:
        if release.get("draft") or not release.get("tag_name", "").startswith(PREFIX):
            continue
        try:
            summary = json.loads(release["body"])
            asset = next(item for item in release["assets"]
                         if item["name"] == "execucao.zip" and item["state"] == "uploaded")
            results.append(summary | {"download": asset["browser_download_url"], "github": release["html_url"]})
        except (ValueError, TypeError, KeyError, StopIteration):
            continue
    return {"execucoes": results, "mais": len(entries) == 30}
