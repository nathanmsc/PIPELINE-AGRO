"""
Scraper do Portal de Informações Agropecuárias (CONAB).

Lê a página de downloads e extrai, de forma 100% dinâmica, a lista de
datasets disponíveis (categoria, nome da tabela, url e extensão do arquivo).
Nenhum nome de categoria/tabela fica hardcoded — se a CONAB adicionar um
novo dataset amanhã, ele aparece automaticamente na próxima execução.
"""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

PORTAL_URL = "https://portaldeinformacoes.conab.gov.br/download-arquivos.html"
DOWNLOAD_PATH_MARKER = "/downloads/arquivos/"


def normalize(nome: str) -> str:
    """Normaliza nomes para uso seguro como namespace/tabela no Iceberg."""
    nome = unicodedata.normalize("NFKD", nome)
    nome = nome.encode("ascii", "ignore").decode()
    nome = nome.lower()
    nome = re.sub(r"[^a-z0-9]+", "_", nome)
    return nome.strip("_")


def scraper_conab(url: str = PORTAL_URL) -> list[dict]:
    """
    Retorna uma lista de dicts no formato:

    {
        "categoria": "armazenamento_logistica",
        "tabela": "armazenagem",
        "nome_original": "Armazenagem",
        "url": "https://.../ArmazensCadastrados.txt",
        "extensao": "txt",
    }
    """
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()

    # o servidor às vezes não manda charset no header Content-Type, e o
    # requests cai no default ISO-8859-1 do HTTP para text/*, o que
    # corrompe acentuação (ex.: "Café" -> "CafÃ©"). O portal serve UTF-8,
    # então forçamos aqui em vez de confiar na detecção automática.
    resp.encoding = "utf-8"

    soup = BeautifulSoup(resp.text, "html.parser")

    datasets: list[dict] = []
    categoria_atual: str | None = None

    # percorre h4 (categorias) e a (links de download) na ordem em que
    # aparecem no documento, sem depender de estrutura de div/wrapper
    for el in soup.find_all(["h4", "a"]):
        if el.name == "h4":
            categoria_atual = normalize(el.get_text(strip=True))
            continue

        if el.name == "a" and categoria_atual:
            href = el.get("href", "")
            if DOWNLOAD_PATH_MARKER not in href:
                continue

            nome_original = el.get_text(strip=True).lstrip("-").strip()
            if not nome_original:
                continue

            url_absoluta = urljoin(url, href)
            extensao = url_absoluta.rsplit(".", 1)[-1].lower() if "." in url_absoluta else ""

            datasets.append(
                {
                    "categoria": categoria_atual,
                    "tabela": normalize(nome_original),
                    "nome_original": nome_original,
                    "url": url_absoluta,
                    "extensao": extensao,
                }
            )

    if not datasets:
        raise RuntimeError(
            "Nenhum dataset encontrado — o HTML do portal pode ter mudado "
            "de estrutura. Verifique o scraper."
        )

    return datasets


if __name__ == "__main__":
    import json

    print(json.dumps(scraper_conab(), indent=2, ensure_ascii=False))
