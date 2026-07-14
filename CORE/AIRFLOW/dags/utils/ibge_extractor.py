"""
Extrator genérico de dados da API de Agregados do IBGE (SIDRA).

Diferente de utils/ibge_agregados_client.py (que lista QUAIS agregados
existem) e spark/ingest_agregados.py (que grava os METADADOS de cada
agregado), este módulo busca os DADOS de fato — a série numérica — de
um agregado, descobrindo automaticamente suas variáveis, classificações
e nível territorial a partir do próprio endpoint de metadados, em vez de
precisar codificar isso manualmente por agregado (como no exemplo do
agregado 74 com classificacao=80[2682] fixo pra "Leite").

Fluxo:
1. GET /agregados/{id}/metadados -> descobre variaveis, classificacoes
   (com suas categorias) e níveis territoriais suportados.
2. Monta UMA consulta pedindo TODAS as variáveis e TODAS as categorias
   de cada classificação de uma vez (usando o "all" da própria API do
   SIDRA), em vez de gerar uma combinação por categoria — a API já
   devolve tudo separado em "resultados", então não precisa de uma
   requisição por categoria.
3. Normaliza a resposta (estrutura profundamente aninhada: variável ->
   resultados -> classificações + séries por localidade/período) num
   DataFrame plano, com uma coluna por dimensão de classificação.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime

import requests

log = logging.getLogger(__name__)

METADADOS_URL_TMPL = "https://servicodados.ibge.gov.br/api/v3/agregados/{agregado_id}/metadados"
PERIODOS_URL_TMPL = "https://servicodados.ibge.gov.br/api/v3/agregados/{agregado_id}/periodos"
DADOS_URL_TMPL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/{agregado_id}"
    "/periodos/{periodo}/variaveis/{variaveis}"
)

# valores usados pelo SIDRA pra "sem informação" / sigiloso / não se aplica
VALORES_AUSENTES = {"..", "...", "-", "X", ""}


def _normalize(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = texto.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-zA-Z0-9]+", "_", texto).strip("_").lower()


def _parse_valor(valor) -> float | None:
    if valor in VALORES_AUSENTES:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def buscar_metadados(agregado_id: str, timeout: int = 60) -> dict:
    resp = requests.get(METADADOS_URL_TMPL.format(agregado_id=agregado_id), timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _escolher_nivel_territorial(metadados: dict) -> str:
    """
    Escolhe o nível territorial a consultar. Nem todo agregado suporta
    o mesmo nível (alguns só têm dado nacional, outros vão até
    município) — por isso não dá pra hardcodar "N3" como no exemplo
    original. Preferência: município (N6) > UF (N3) > o que existir.
    """
    niveis = metadados.get("nivelTerritorial", {}).get("Administrativo", [])
    if not niveis:
        raise RuntimeError(
            f"Agregado {metadados.get('id')} não tem nível territorial "
            "administrativo declarado nos metadados."
        )
    for preferido in ("N6", "N3", "N1"):
        if preferido in niveis:
            return preferido
    return niveis[0]


def montar_consulta(metadados: dict, periodo: str = "all") -> tuple[str, dict]:
    """
    Monta (url, params) pra buscar TODOS os dados de um agregado, com
    todas as variáveis e todas as categorias de cada classificação.
    """
    agregado_id = metadados["id"]
    variaveis = metadados.get("variaveis", [])
    classificacoes = metadados.get("classificacoes", [])

    if not variaveis:
        raise RuntimeError(f"Agregado {agregado_id} não tem variáveis nos metadados.")

    variaveis_ids = "|".join(str(v["id"]) for v in variaveis)
    nivel = _escolher_nivel_territorial(metadados)

    url = DADOS_URL_TMPL.format(agregado_id=agregado_id, periodo=periodo, variaveis=variaveis_ids)

    params = {"localidades": f"{nivel}[all]"}
    if classificacoes:
        params["classificacao"] = "|".join(f"{c['id']}[all]" for c in classificacoes)

    return url, params


def _flatten_resultado(resultado: dict, variavel_nome: str, unidade: str, agregado_id: str) -> list[dict]:
    """Achata UM resultado (uma combinação de categorias) em linhas, uma
    por localidade x período."""
    valores_classificacao: dict[str, str] = {}

    for classif in resultado.get("classificacoes", []):
        # cada classif tem um dict "categoria": {"id_categoria": "nome_categoria"}
        # normalmente com um único par — pega o primeiro
        categoria = classif.get("categoria", {})
        if not categoria:
            continue
        cat_id, cat_nome = next(iter(categoria.items()))
        nome_coluna = _normalize(classif.get("nome") or classif.get("id") or "classificacao")
        valores_classificacao[nome_coluna] = cat_nome
        valores_classificacao[f"{nome_coluna}_id"] = cat_id

    linhas = []
    for serie in resultado.get("series", []):
        localidade = serie.get("localidade", {})
        for periodo, valor in serie.get("serie", {}).items():
            linha = {
                "agregado_id": agregado_id,
                "variavel": variavel_nome,
                "unidade": unidade,
                "localidade_id": localidade.get("id"),
                "localidade_nome": localidade.get("nome"),
                "periodo": periodo,
                "valor": _parse_valor(valor),
            }
            linha.update(valores_classificacao)
            linhas.append(linha)

    return linhas


def _ano_do_periodo(periodo_id: str) -> int | None:
    """
    Extrai o ano de um id de período do SIDRA. A maioria é só o ano
    ("2022"), mas periodicidade mensal/trimestral vem como os 4
    primeiros dígitos sendo o ano (ex.: "202201" = janeiro de 2022).
    """
    match = re.match(r"^(\d{4})", str(periodo_id))
    return int(match.group(1)) if match else None


def _filtrar_por_janela_de_anos(periodos: list[str], anos_de_janela: int) -> list[str]:
    """
    Mantém só os períodos cujo ano está entre (ano atual - anos_de_janela)
    e o ano atual, inclusive — ex.: em 2026 com anos_de_janela=5, mantém
    2021 a 2026. Diferente de simplesmente pegar os últimos N períodos
    da lista, que não respeitaria janela de calendário se os períodos
    disponíveis não forem espaçados ano a ano (ex.: anos de censo:
    1985, 1995, 2006, 2017...).
    """
    ano_atual = datetime.now().year
    ano_minimo = ano_atual - anos_de_janela

    return [
        p for p in periodos
        if (ano := _ano_do_periodo(p)) is not None and ano_minimo <= ano <= ano_atual
    ]


def listar_periodos(agregado_id: str, timeout: int = 60) -> list[str]:
    """Lista os períodos individuais disponíveis pra um agregado — usado
    como fallback quando periodo="all" é grande demais pra API processar
    numa resposta só."""
    resp = requests.get(PERIODOS_URL_TMPL.format(agregado_id=agregado_id), timeout=timeout)
    resp.raise_for_status()
    return [p["id"] for p in resp.json()]


def _buscar_e_achatar(metadados: dict, periodo: str, timeout: int) -> list[dict]:
    agregado_id = metadados["id"]
    url, params = montar_consulta(metadados, periodo=periodo)

    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    dados = resp.json()

    linhas: list[dict] = []
    for bloco in dados:
        variavel_nome = bloco.get("variavel", "")
        unidade = bloco.get("unidade", "")
        for resultado in bloco.get("resultados", []):
            linhas.extend(_flatten_resultado(resultado, variavel_nome, unidade, agregado_id))
    return linhas


def extrair_dados(agregado_id: str, anos_de_janela: int | None = 5, timeout: int = 120) -> list[dict]:
    """
    Ponto de entrada principal: descobre os metadados do agregado,
    busca os períodos dentro da janela de calendário [ano atual -
    anos_de_janela, ano atual] (um período de cada vez) e devolve os
    dados já normalizados (lista de dicts, uma linha por localidade x
    período x combinação de categorias) — pronta pra virar DataFrame
    (pandas ou Spark).

    Ex.: com anos_de_janela=5 rodando em 2026, busca 2021 a 2026
    (inclusive), não importa quantos períodos existam nesse intervalo.

    Passe anos_de_janela=None pra buscar o histórico completo — mas
    cuidado: pra agregados grandes (muitas décadas x todos os municípios
    x várias classificações), a API do SIDRA pode responder com 500
    Internal Server Error mesmo período por período, sem dar pra reduzir
    mais (isso já foi observado em algumas tabelas "série histórica
    1920/2006" do Censo Agropecuário). Cada período que falhar é
    logado e pulado, sem derrubar os demais.

    Sempre busca um período de cada vez (não usa periodo="all"): pedir
    o histórico inteiro numa resposta só, combinado com
    localidades=N6[all] (todos os municípios) e todas as categorias de
    cada classificação, é grande demais pra API processar de uma vez —
    ela responde com 500 Internal Server Error em vez de um erro mais
    claro de "requisição grande demais".
    """
    metadados = buscar_metadados(agregado_id)
    periodos = listar_periodos(agregado_id, timeout=timeout)

    if anos_de_janela is not None:
        periodos = _filtrar_por_janela_de_anos(periodos, anos_de_janela)

    linhas: list[dict] = []
    for periodo in periodos:
        try:
            linhas.extend(_buscar_e_achatar(metadados, periodo, timeout))
        except requests.HTTPError as exc:
            log.error(
                "Agregado %s: falhou no período %s: %s",
                agregado_id,
                periodo,
                exc,
            )
            continue

    return linhas