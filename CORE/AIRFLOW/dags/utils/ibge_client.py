"""
Cliente da API de Agregados do IBGE (SIDRA), filtrado para:

1. Pesquisas que entram por INTEIRO (poucos agregados, sem filtro
   temático necessário): Pesquisa da Pecuária Municipal (PPM).

2. Censo Agropecuário: NÃO entra por inteiro (tem ~1400 agregados,
   somando várias edições do censo) — só entram agregados cujo NOME
   bate com um dos temas em TEMAS_CENSO_AGROPECUARIO (irrigação,
   máquinas agrícolas, demografia rural / pessoal ocupado, valor da
   produção). Isso porque, no SIDRA, "Irrigação", "Máquinas Agrícolas"
   e "Demografia Rural" não são pesquisas separadas — são módulos
   temáticos dentro do próprio Censo Agropecuário.

3. Qualquer agregado marcado "(série encerrada)" é excluído sempre —
   são versões descontinuadas/antigas da mesma tabela, mantidas no
   catálogo só por retrocompatibilidade.
"""

from __future__ import annotations

import re
import unicodedata

import requests

CATALOGO_URL = "https://servicodados.ibge.gov.br/api/v3/agregados"
METADADOS_URL_TMPL = "https://servicodados.ibge.gov.br/api/v3/agregados/{agregado_id}/metadados"

# pesquisas que entram por inteiro, sem filtro temático — poucos
# agregados cada, baixo risco de trazer volume indesejado
PESQUISAS_COMPLETAS = [
    "pecuaria municipal",
    "ppm",
]

# pesquisa cujo volume total é grande demais pra entrar por inteiro —
# só entra filtrada pelos temas abaixo
TERMO_CENSO_AGROPECUARIO = "censo agropecuario"

# temas usados para filtrar DENTRO do Censo Agropecuário (casados contra
# o nome do agregado, não da pesquisa — a pesquisa toda se chama "Censo
# Agropecuário", o tema está descrito em cada agregado individual)
TEMAS_CENSO_AGROPECUARIO = [
    "irrigacao",
    "maquinas agricolas",
    "trator",
    "implemento agricola",
    "equipamento agricola",
    "pessoal ocupado",
    "mao de obra",
    "trabalhador rural",
    "valor da producao",
]

TERMO_SERIE_ENCERRADA = "serie encerrada"


def normalize(texto: str) -> str:
    """Remove acentos, baixa a caixa, normaliza espaços."""
    texto = unicodedata.normalize("NFKD", texto)
    texto = texto.encode("ascii", "ignore").decode()
    texto = texto.lower()
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


def _slug(texto: str) -> str:
    """Versão do normalize() segura pra nome de tabela/coluna."""
    return re.sub(r"[^a-z0-9]+", "_", normalize(texto)).strip("_")


def _bate_termo(texto_normalizado: str, termos: list[str]) -> bool:
    for termo in termos:
        # siglas curtas (ppm) usam borda de palavra pra não casar como
        # substring dentro de uma palavra maior
        if len(termo) <= 3:
            if re.search(rf"\b{re.escape(termo)}\b", texto_normalizado):
                return True
        elif termo in texto_normalizado:
            return True
    return False


def listar_agregados_agro(url: str = CATALOGO_URL) -> list[dict]:
    """
    Retorna a lista achatada (um dict por agregado) já filtrada conforme
    as regras do módulo (ver docstring do arquivo).

    {
        "pesquisa_id": "...",
        "pesquisa": "Pesquisa da Pecuária Municipal",
        "agregado_id": "3939",
        "tabela": "agregado_3939_efetivo_dos_rebanhos_...",
        "nome_original": "Efetivo dos rebanhos, por tipo de rebanho",
        "url_metadados": "https://servicodados.ibge.gov.br/api/v3/agregados/3939/metadados",
    }
    """
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    catalogo = resp.json()

    agregados: list[dict] = []
    for pesquisa in catalogo:
        pesquisa_nome = pesquisa.get("nome", "")
        pesquisa_norm = normalize(pesquisa_nome)

        pesquisa_completa = _bate_termo(pesquisa_norm, PESQUISAS_COMPLETAS)
        eh_censo_agropecuario = TERMO_CENSO_AGROPECUARIO in pesquisa_norm

        if not (pesquisa_completa or eh_censo_agropecuario):
            continue

        for agregado in pesquisa.get("agregados", []):
            agregado_nome = agregado["nome"]
            agregado_norm = normalize(agregado_nome)

            # exclui séries descontinuadas em qualquer pesquisa
            if TERMO_SERIE_ENCERRADA in agregado_norm:
                continue

            if pesquisa_completa:
                incluir = True
            elif eh_censo_agropecuario:
                incluir = _bate_termo(agregado_norm, TEMAS_CENSO_AGROPECUARIO)
            else:
                incluir = False

            if not incluir:
                continue

            agregado_id = agregado["id"]
            agregados.append(
                {
                    "pesquisa_id": pesquisa.get("id"),
                    "pesquisa": pesquisa_nome,
                    "agregado_id": agregado_id,
                    # inclui o id no nome — o nome sozinho não é
                    # garantidamente único entre pesquisas diferentes
                    "tabela": f"agregado_{agregado_id}_{_slug(agregado_nome)}"[:120],
                    "nome_original": agregado_nome,
                    "url_metadados": METADADOS_URL_TMPL.format(agregado_id=agregado_id),
                }
            )

    if not agregados:
        raise RuntimeError(
            "Nenhum agregado bateu com os filtros — confira se os termos "
            "ainda correspondem aos nomes usados pela API do IBGE."
        )

    return agregados


if __name__ == "__main__":
    import json

    print(json.dumps(listar_agregados_agro(), indent=2, ensure_ascii=False))