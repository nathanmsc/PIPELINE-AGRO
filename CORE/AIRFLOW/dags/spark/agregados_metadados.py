"""
Ingestão dos DADOS (não metadados) de agregados do IBGE (SIDRA) para o
Iceberg (bronze).

Diferente de spark/ingest_agregados.py (que grava a descrição/estrutura
de cada agregado, sempre createOrReplace porque é dado de referência),
aqui a escrita é sempre append + evolução de schema — os dados numéricos
por localidade/período SÃO uma série que cresce (ou é reprocessada
integralmente a cada carga, mas ainda assim é histórico, não descrição).

Cada agregado vira sua PRÓPRIA tabela (agregado_id no nome), porque
agregados diferentes têm dimensões de classificação diferentes (um tem
"Produto", outro tem "Tipo de rebanho", outro não tem classificação
nenhuma) — misturar tudo numa tabela só geraria uma tabela com dezenas
de colunas quase todas nulas.

Processa um LOTE de agregados por chamada, com uma única SparkSession
(mesmo raciocínio de spark/ingest_agregados.py: evita overhead de uma
JVM por agregado com ~357 agregados no total).
"""

from __future__ import annotations

import logging

from spark.ingest import get_spark
from spark.schema_evolution import write_with_schema_check
from utils.ibge_extractor import extrair_dados

log = logging.getLogger(__name__)

NAMESPACE = "default"
LAYER = "bronze"
SOURCE = "sidra"

def _ingest_um_agregado(spark, item: dict, anos_de_janela: int | None) -> None:
    agregado_id = item["agregado_id"]
    tabela = item["tabela"]

    linhas = extrair_dados(agregado_id, anos_de_janela=anos_de_janela)
    if not linhas:
        log.warning("agregado_id=%s (%s) não retornou nenhuma linha.", agregado_id, tabela)
        return

    df = spark.createDataFrame(linhas)
    
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {NAMESPACE}")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {NAMESPACE}.{LAYER}")
    spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {NAMESPACE}.{LAYER}.{SOURCE}")

    table_fqn = f"{NAMESPACE}.{LAYER}.{SOURCE}.{tabela}"
    

    write_with_schema_check(spark, df, table_fqn)


def ingest_lote(lote: list[dict], anos_de_janela: int | None = 5) -> None:
    """
    Ponto de entrada da task mapeada: processa um LOTE de agregados,
    cada um virando sua própria tabela Iceberg, com uma SparkSession
    compartilhada pro lote inteiro.

    Falhas individuais são logadas e não derrubam o lote inteiro.
    """
    spark = get_spark(app_name="ibge-dados-agregados-ingest")

    erros = []
    try:
        for item in lote:
            try:
                _ingest_um_agregado(spark, item, anos_de_janela=anos_de_janela)
            except Exception as exc:
                log.error(
                    "Falha ao ingerir dados do agregado_id=%s (%s): %s",
                    item.get("agregado_id"),
                    item.get("tabela"),
                    exc,
                )
                erros.append((item.get("agregado_id"), str(exc)))
    finally:
        spark.stop()

    if erros:
        raise RuntimeError(
            f"{len(erros)}/{len(lote)} agregados falharam no lote: {erros}"
        )