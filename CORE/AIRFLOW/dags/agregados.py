"""
DAG de ingestão dos DADOS (não metadados) de agregados do IBGE (SIDRA),
usando a mesma lista filtrada de utils/ibge_agregados_client.py (PPM
completa + Censo Agropecuário filtrado por irrigação/máquinas/demografia
rural/valor da produção).

Mesma estrutura de lotes de ingestion_agregados.py: ~357 agregados,
processados em lotes de 25 com uma SparkSession por lote, não uma task
por agregado individual.

Busca só os últimos ANOS_DE_JANELA anos (janela de calendário) de cada
agregado (não o histórico completo) — além de ser o que foi pedido,
isso também evita o 500 Internal Server Error que a API do SIDRA
retorna quando o histórico completo, em nível de município e com todas
as categorias, é grande demais pra processar numa resposta só.
"""

from __future__ import annotations

import sys

import pendulum
from airflow.decorators import dag, task

# ajuste o path conforme onde o projeto for instalado no ambiente do Airflow
sys.path.append("/opt/airflow/conab_pipeline")

from spark.agregados_metadados import ingest_lote  # noqa: E402
from utils.ibge_client import listar_agregados_agro  # noqa: E402

TAMANHO_LOTE = 25
ANOS_DE_JANELA = 5


@dag(
    dag_id="agregados",
    description="Ingestão dos dados numéricos de agregados do IBGE (SIDRA) relacionados ao agro",
    schedule="@weekly",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Bahia"),
    catchup=False,
    tags=["ibge", "sidra", "bronze", "iceberg"],
)
def ingestion_dados_agregados():

    @task
    def listar_em_lotes() -> list[list[dict]]:
        itens = listar_agregados_agro()
        return [
            itens[i : i + TAMANHO_LOTE] for i in range(0, len(itens), TAMANHO_LOTE)
        ]

    @task(
        retries=2,
        retry_delay=pendulum.duration(minutes=2),
    )
    def carregar_lote(lote: list[dict]) -> None:
        ingest_lote(
            lote,
            anos_de_janela=ANOS_DE_JANELA,
        )


    lotes = listar_em_lotes()
    carregar_lote.expand(lote=lotes)


ingestion_dados_agregados()