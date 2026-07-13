"""
Comparação e evolução controlada de schema entre o DataFrame de origem
e a tabela Iceberg existente.

Três caminhos possíveis, decididos ANTES de qualquer escrita:

1. Schemas idênticos            -> append() direto.
2. Só colunas novas no DataFrame -> ALTER TABLE ADD COLUMNS (explícito,
   não via merge-schema implícito no write) e então append().
3. Conflito de tipo em alguma coluna existente -> a tabela é renomeada
   para um backup com timestamp (nunca DROP direto) e recriada do zero
   com o schema atual. Nenhum dado é perdido silenciosamente; fica
   disponível na tabela `_bkp_<timestamp>` para inspeção/merge manual.

Cole este bloco em spark/ingest.py, substituindo o trecho:

    if spark.catalog.tableExists(table_fqn):
        try:
            df.writeTo(table_fqn).option("merge-schema", "true").append()
        except Exception as exc:
            ...
    else:
        df.writeTo(table_fqn).using("iceberg").createOrReplace()

por uma chamada a `write_with_schema_check(spark, df, table_fqn)`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pyspark.sql.types import DataType

log = logging.getLogger(__name__)


def _get_existing_schema(spark, table_fqn: str) -> dict[str, DataType] | None:
    """Retorna {nome_coluna: tipo} da tabela, ou None se ela não existir."""
    if not spark.catalog.tableExists(table_fqn):
        return None
    return {f.name: f.dataType for f in spark.table(table_fqn).schema.fields}


def _compare_schemas(
    existing: dict[str, DataType], incoming: dict[str, DataType]
) -> tuple[list[str], list[tuple[str, DataType, DataType]]]:
    """
    Compara o schema existente na tabela com o schema do DataFrame novo.

    Retorna (colunas_novas, conflitos_de_tipo):
    - colunas_novas: nomes presentes no DataFrame mas ausentes na tabela
      (evolução segura — apenas adiciona).
    - conflitos_de_tipo: (nome, tipo_existente, tipo_novo) para colunas
      que existem nos dois lados mas com tipos diferentes (evolução
      insegura — exige recriação controlada).

    Colunas presentes na tabela mas ausentes no DataFrame novo não geram
    ação nenhuma: continuam na tabela e ficam NULL nas linhas novas, o
    que é o comportamento correto para uma camada bronze (não perde
    histórico de colunas que saíram do arquivo fonte).
    """
    colunas_novas = [nome for nome in incoming if nome not in existing]

    conflitos_de_tipo = [
        (nome, existing[nome], incoming[nome])
        for nome in incoming
        if nome in existing and existing[nome] != incoming[nome]
    ]

    return colunas_novas, conflitos_de_tipo


def write_with_schema_check(spark, df, table_fqn: str) -> None:
    """
    Ponto de entrada único para gravar `df` em `table_fqn`, decidindo
    entre append direto, evolução de schema ou recriação controlada.
    """
    existing_schema = _get_existing_schema(spark, table_fqn)

    # Tabela nova: cria do zero, sem comparação.
    if existing_schema is None:
        df.writeTo(table_fqn).using("iceberg").createOrReplace()
        return

    incoming_schema = {f.name: f.dataType for f in df.schema.fields}
    colunas_novas, conflitos_de_tipo = _compare_schemas(existing_schema, incoming_schema)

    if conflitos_de_tipo:
        # Conflito real de tipo (ex.: uma coluna era string e virou
        # double numa carga mais recente). Não dá pra evoluir com
        # segurança — o Iceberg só amplia tipos numéricos compatíveis
        # (int -> long, float -> double), não faz cast arbitrário.
        # Em vez de recriar por cima (perdendo o histórico), renomeia a
        # tabela atual para um backup com timestamp e recria do zero.
        conflitos_str = ", ".join(
            f"{nome} ({antigo.simpleString()} -> {novo.simpleString()})"
            for nome, antigo, novo in conflitos_de_tipo
        )
        log.warning(
            "Conflito de tipo em '%s': %s. Fazendo backup da tabela "
            "antiga antes de recriar.",
            table_fqn,
            conflitos_str,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_fqn = f"{table_fqn}_bkp_{timestamp}"
        spark.sql(f"ALTER TABLE {table_fqn} RENAME TO {backup_fqn}")
        log.warning("Tabela antiga preservada em '%s'.", backup_fqn)

        df.writeTo(table_fqn).using("iceberg").createOrReplace()
        return

    if colunas_novas:
        # Só colunas novas, sem conflito — evolução segura e explícita
        # via ALTER TABLE, em vez de depender do merge-schema implícito
        # no write (fica registrado no log e no histórico de schema da
        # própria tabela Iceberg).
        for nome in colunas_novas:
            tipo_sql = incoming_schema[nome].simpleString()
            log.info("Adicionando coluna nova '%s' (%s) em '%s'.", nome, tipo_sql, table_fqn)
            spark.sql(f"ALTER TABLE {table_fqn} ADD COLUMNS ({nome} {tipo_sql})")

    df.writeTo(table_fqn).append()