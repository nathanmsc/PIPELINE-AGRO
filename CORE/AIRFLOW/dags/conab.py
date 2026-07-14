"""
DAG genérica de ingestão CONAB -> Iceberg (bronze).

Não há uma task por arquivo escrita no código: a lista de datasets vem
do scraper em tempo de execução, e o Airflow cria uma task mapeada (carregar[0],
carregar[1], ...) para cada item automaticamente via Dynamic Task Mapping.

Se a CONAB adicionar/remover um dataset no portal, nenhuma linha desta
DAG precisa mudar.
"""

from __future__ import annotations

import sys

import pendulum
from airflow.decorators import dag, task

# ajuste o path conforme onde o projeto for instalado no ambiente do Airflow
sys.path.append("/opt/airflow/conab_pipeline")

from spark.ingest import ingest  # noqa: E402
from utils.conab_scraper import scraper_conab  # noqa: E402


@dag(
    dag_id="conab",
    description="Ingestão dinâmica de todos os datasets do Portal CONAB para o Iceberg (bronze)",
    schedule="@daily",
    start_date=pendulum.datetime(2026, 1, 1, tz="America/Bahia"),
    catchup=False,
    tags=["conab", "bronze", "iceberg", "spark"],
)
def conab():

    @task
    def listar_datasets() -> list[dict]:
        return scraper_conab()

    @task(
        # rede de segurança: se a task for marcada como failed por um
        # falso-negativo de heartbeat (JVM do Spark bloqueada tempo demais
        # pra reportar), o Airflow tenta de novo sozinho em vez de ficar
        # parada até alguém clicar em Clear manualmente
        retries=2,
        retry_delay=pendulum.duration(minutes=2),
    )
    def carregar(item: dict) -> None:
        ingest(item)

    datasets = listar_datasets()
    carregar.expand(item=datasets)


conab()