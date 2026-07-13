"""
Ingestão genérica: baixa o arquivo do portal CONAB e grava no Iceberg
(camada bronze), com schema inferido automaticamente a partir do arquivo —
não é necessário conhecer as colunas de antemão.
"""

from __future__ import annotations

import logging
import os
import re
import tempfile
import unicodedata
from pathlib import Path

import requests

from dotenv import load_dotenv
from pyspark.sql import SparkSession

from spark.schema_evolution import write_with_schema_check


log = logging.getLogger(__name__)

# Caminhos candidatos para o .env
_ENV_CANDIDATES = (
    Path(__file__).resolve().with_name(".env"),      # dags/spark/.env
    Path(__file__).resolve().parents[2] / ".env",    # /opt/airflow/.env
)

TIMEOUT_DOWNLOAD = 120

ICEBERG_JARS = (
    "/opt/spark-jars/iceberg-spark-runtime-4.0_2.13-1.10.1.jar,"
    "/opt/spark-jars/iceberg-aws-bundle-1.10.1.jar"
)


def _load_catalog_config() -> tuple[str, str, str]:
    """
    Lê CATALOG_URI / WAREHOUSE / TOKEN da forma mais robusta possível:

    1. Recarrega o .env com override=True para sobrescrever valores
       vazios/inválidos que o Airflow possa ter injetado no ambiente.
    2. Lê as variáveis de ambiente (agora ajustadas pelo .env).
    3. Valida que nenhuma está ausente ou em branco.

    Retorna (catalog_uri, warehouse, token)"""
    for env_file in _ENV_CANDIDATES:
        if env_file.exists():
            # override=True: o .env sempre vence sobre vars vazias do container
            load_dotenv(dotenv_path=env_file, override=True)
            log.info("Carregado .env de: %s", env_file)
            break

    catalog_uri = os.getenv("CATALOG_URI") or os.getenv("ICEBERG_CATALOG_URI", "")
    warehouse = os.getenv("WAREHOUSE") or os.getenv("ICEBERG_WAREHOUSE", "")
    token = os.getenv("TOKEN") or os.getenv("ICEBERG_TOKEN", "")

    missing = [name for name, val in
               [("CATALOG_URI/ICEBERG_CATALOG_URI", catalog_uri),
                ("WAREHOUSE/ICEBERG_WAREHOUSE", warehouse),
                ("TOKEN/ICEBERG_TOKEN", token)]
               if not val]
    if missing:
        raise RuntimeError(
            "Configuração do catálogo Iceberg REST ausente: "
            + ", ".join(missing)
            + ". Defina as variáveis no ambiente do Airflow "
              "ou em airflow/dags/spark/.env."
        )

    # Log parcial do token para diagnóstico (não expõe o segredo)
    log.info(
        "Catálogo configurado — URI=%s | warehouse=%s | token=%s…%s",
        catalog_uri,
        warehouse,
        token[:8],
        token[-4:],
    )
    return catalog_uri, warehouse, token


def _normalize_column_name(name: object, used_names: set[str] | None = None) -> str:
    """Normaliza nomes de coluna para um formato seguro ao escrever no Iceberg."""
    text = "" if name is None else str(name).strip()
    if not text:
        text = "column"

    normalized = unicodedata.normalize("NFKD", text)
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")

    if not normalized:
        normalized = "column"
    if normalized[0].isdigit():
        normalized = f"col_{normalized}"

    if used_names is None:
        return normalized

    candidate = normalized
    suffix = 2
    while candidate in used_names:
        candidate = f"{normalized}_{suffix}"
        suffix += 1

    used_names.add(candidate)
    return candidate


def _normalize_dataframe_schema(df) -> object:
    """Renomeia colunas com caracteres inválidos para um esquema compatível."""
    columns = list(df.columns)
    used_names: set[str] = set()
    normalized_columns = [_normalize_column_name(col, used_names) for col in columns]

    if normalized_columns != columns:
        log.info("Normalizando colunas do DataFrame para escrita Iceberg: %s", dict(zip(columns, normalized_columns)))
        return df.toDF(*normalized_columns)

    return df


def get_spark(app_name: str = "conab-ingest") -> SparkSession:
    """
    Sessão Spark local, configurada para rodar dentro de um container
    Docker sem depender de resolução de hostname de rede.
    """
    catalog_uri, warehouse, token = _load_catalog_config()

    spark = (
        SparkSession.builder.appName(app_name)
        .master("local[2]")
        .config("spark.driver.host", "127.0.0.1")
        .config("spark.driver.bindAddress", "127.0.0.1")
        .config("spark.ui.enabled", "false")
        .config("spark.jars", ICEBERG_JARS)
        .config(
            "spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions",
        )
        .config("spark.sql.catalog.my_catalog", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.my_catalog.type", "rest")
        .config("spark.sql.catalog.my_catalog.uri", catalog_uri)
        .config("spark.sql.catalog.my_catalog.warehouse", warehouse)
        # NÃO usar a propriedade `token` — o Iceberg >= 1.9 infere oauth2
        # e tenta um token-exchange que falha com tokens Bearer estáticos
        # do Cloudflare R2. Injetamos o Authorization header diretamente
        # pelo mecanismo `header.*`, igual ao X-Iceberg-Access-Delegation.
        .config("spark.sql.catalog.my_catalog.header.Authorization", f"Bearer {token}")
        .config(
            "spark.sql.catalog.my_catalog.header.X-Iceberg-Access-Delegation",
            "vended-credentials",
        )
        .config("spark.sql.catalog.my_catalog.s3.remote-signing-enabled", "false")
        .config("spark.sql.defaultCatalog", "my_catalog")
        .getOrCreate()
    )

    spark.sql("USE my_catalog")

    return spark


def _download(url: str) -> str:
    """
    Spark não lê URLs http(s) diretamente (spark.read.csv espera um
    caminho de filesystem/HDFS/S3/etc). Por isso baixamos o arquivo para
    um temporário local antes de carregar no Spark.
    """
    resp = requests.get(url, timeout=TIMEOUT_DOWNLOAD)
    resp.raise_for_status()

    suffix = "." + url.rsplit(".", 1)[-1] if "." in url.rsplit("/", 1)[-1] else ""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(resp.content)

    return path


def _read_dataframe(spark: SparkSession, local_path: str, extensao: str):
    extensao = extensao.lower()

    if extensao == "txt":
        return spark.read.csv(
            local_path,
            header=True,
            inferSchema=True,
            sep=";",
            encoding="iso-8859-1",
        )

    if extensao in ("xls", "xlsx"):
        # arquivo pequeno (ex.: Série Histórica da Capacidade Estática) —
        # mais simples ler com pandas e converter, evitando depender de
        # um jar extra (spark-excel) no cluster/Colab.
        import pandas as pd

        try:
            pdf = pd.read_excel(local_path, engine="calamine")
        except ImportError:
            if extensao == "xlsx":
                pdf = pd.read_excel(local_path, engine="")
            else:
                raise ImportError(
                    "Falha ao ler arquivo .openpyxlxls: instale `python-calamine` "
                    "ou `xlrd>=2.0.1` no container do Airflow."
                ) from None

        return spark.createDataFrame(pdf)

    if extensao == "csv":
        return spark.read.csv(local_path, header=True, inferSchema=True, sep=",")

    raise ValueError(f"Extensão não suportada: '{extensao}'")


def ingest(item: dict) -> None:
    """
    item: dict retornado pelo scraper, com chaves
    categoria, tabela, url, extensao.
    """
    categoria = item["categoria"]
    tabela = item["tabela"]
    url = item["url"]
    extensao = item.get("extensao") or url.rsplit(".", 1)[-1]

    spark = get_spark(app_name=f"conab-ingest-{categoria}-{tabela}")
    local_path = _download(url)

    try:
        df = _read_dataframe(spark, local_path, extensao)
        df = _normalize_dataframe_schema(df)

        # O namespace deve bater com o prefixo do FQN da tabela.
        # Ex.: table_fqn = "conab.safra" → namespace = "conab"
        namespace = "default"
        layer = "bronze"
        source = "conab"
        table_fqn = f"{namespace}.{layer}.{source}.{tabela}"

        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {namespace}")
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {namespace}.{layer}")
        spark.sql(f"CREATE NAMESPACE IF NOT EXISTS {namespace}.{layer}.{source}")

        try:
            write_with_schema_check(spark, df, table_fqn)
        except Exception as exc:
            if "NoSuchKeyException" in str(exc) or "404" in str(exc):
                spark.catalog.dropTable(table_fqn, ignoreIfNotExists=True)
                df.writeTo(table_fqn).using("iceberg").createOrReplace()
            else:
                raise

    finally:
        os.remove(local_path)
        spark.stop()