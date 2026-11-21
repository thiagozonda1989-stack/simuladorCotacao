"""Publica a branch local do piloto e encontra ou cria sua Issue e seu PR."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

REPO = "thiagozonda1989-stack/simuladorCotacao"
BRANCH = "research/piloto-ias-etapa1"
BASELINE = "b4c18d86aac2ce4ffc352957e56a29ce30fe63f1"
ISSUE = "ProfitRTD Etapa 1 — validar referência e cobertura WIN"
PR = "ProfitRTD Etapa 1 — piloto de colaboração e evidências"


def run(*args):
    return subprocess.check_output(args, encoding="utf-8").strip()


def find_issue():
    result = json.loads(run("gh", "issue", "list", "--repo", REPO, "--state", "all", "--limit",
                            "100", "--search", '"ProfitRTD Etapa 1" in:title', "--json", "title,url,number"))
    return next((item for item in result if item["title"] == ISSUE), None)


def find_pr():
    results = json.loads(run("gh", "pr", "list", "--repo", REPO, "--head", BRANCH,
                             "--base", "main", "--state", "all", "--json", "url,state"))
    return next((item for item in results if item["state"] == "OPEN"), None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--publicar", action="store_true")
    args = parser.parse_args()
    root = Path(run("git", "rev-parse", "--show-toplevel"))
    docs = root/"docs"/"colaboracao"
    try:
        if run("git", "branch", "--show-current") != BRANCH:
            parser.error(f"Selecione a branch {BRANCH}.")
        subprocess.run(["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"], check=True)
        if run("git", "status", "--porcelain"):
            parser.error("Use um clone limpo para evitar que arquivos locais sejam confundidos com a entrega.")
        issue_body = docs/"ETAPA1_ISSUE.md"
        evidence = (docs/"ETAPA1_EVIDENCIAS.md").read_text(encoding="utf-8")
        if not issue_body.is_file():
            parser.error("O texto da Issue está ausente.")
        if not args.publicar:
            print(f"Pronto para publicar {BRANCH} em {REPO} e abrir a Issue e o PR de rascunho.")
            return
        run("gh", "auth", "status", "--hostname", "github.com")
        # O destino é o repositório oficial, inclusive quando origin ainda aponta para um bundle.
        subprocess.run(["git", "push", f"https://github.com/{REPO}.git",
                        f"HEAD:refs/heads/{BRANCH}"], check=True)
        issue = find_issue()
        if issue is None:
            url = run("gh", "issue", "create", "--repo", REPO, "--title", ISSUE, "--body-file", str(issue_body))
        else:
            url = issue["url"]
        print(f"Issue: {url}", flush=True)
        existing = find_pr()
        if existing:
            print(f'PR: {existing["url"]}')
            return
        with tempfile.TemporaryDirectory() as tmp:
            body = Path(tmp)/"pr.md"
            body.write_text(f"Acompanha {url}\n\n{evidence}", encoding="utf-8")
            print("PR:", run("gh", "pr", "create", "--repo", REPO, "--head", BRANCH, "--base", "main",
                             "--draft", "--title", PR, "--body-file", str(body)))
    except (OSError, subprocess.CalledProcessError, ValueError) as error:
        parser.exit(1, f"Publicação interrompida: {error}\n")


if __name__ == "__main__":
    main()
