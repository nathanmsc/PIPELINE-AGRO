FROM apache/airflow:slim-latest-python3.12

USER root

# PySpark precisa de uma JVM (o erro "JAVA_GATEWAY_EXITED" acontece
RUN apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jdk-headless curl \
    && apt-get autoremove -yqq --purge \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Jars do Iceberg baixados uma vez no build, em vez de via
# executor local (NullPointerException em BlockManagerId).
RUN mkdir -p /opt/spark-jars \
    && curl -fsSL -o /opt/spark-jars/iceberg-spark-runtime-4.0_2.13-1.10.1.jar \
        https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-spark-runtime-4.0_2.13/1.10.1/iceberg-spark-runtime-4.0_2.13-1.10.1.jar \
    && curl -fsSL -o /opt/spark-jars/iceberg-aws-bundle-1.10.1.jar \
        https://repo1.maven.org/maven2/org/apache/iceberg/iceberg-aws-bundle/1.10.1/iceberg-aws-bundle-1.10.1.jar

# ajuste o caminho se sua arquitetura não for amd64 (ex.: Apple Silicon
# seria .../java-17-openjdk-arm64) — confira com:
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# o executor local — sem isso, tasks em paralelo podem falhar com
# NullPointerException em BlockManagerId ao subir a SparkSession.
ENV SPARK_LOCAL_IP=127.0.0.1

USER airflow

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir --user -r /requirements.txt
