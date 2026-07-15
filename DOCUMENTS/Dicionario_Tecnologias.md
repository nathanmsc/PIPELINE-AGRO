# Dicionário de Tecnologias - AGRODATA-PA

Este documento catalogas todas as tecnologias, ferramentas, frameworks, plataformas e metodologias mencionadas no artigo técnico do projeto AGRODATA-PA, organizadas por categoria.

---

## 🏗️ **Orquestração e Workflow**

| Tecnologia | Versão/Detalhe | Uso no Projeto |
|------------|----------------|----------------|
| **Apache Airflow** | 3.0.0 (Python 3.11) | Orquestração principal de DAGs; Dynamic Task Mapping para CONAB; agendamento diário |
| **Apache Airflow Providers** | - | Operadores Spark, PostgreSQL, HTTP, Docker |
| **Docker** | - | Containerização da stack Airflow + Spark + JDK |
| **Docker Compose** | - | Orquestração local: Airflow Webserver, Scheduler, PostgreSQL, pgAdmin4 |

---

## ⚡ **Processamento Distribuído**

| Tecnologia | Versão/Detalhe | Uso no Projeto |
|------------|----------------|----------------|
| **Apache Spark** | 3.x (Spark 4.0 runtime para Iceberg) | Processamento distribuído ELT; leitura/escrita Iceberg; uma SparkSession por lote (25 agregados IBGE) |
| **PySpark** | - | API Python para jobs Spark; manipulação de DataFrames |
| **OpenJDK** | 17 (JRE Headless) | Runtime Java para Spark; instalado na imagem Docker customizada |
| **Iceberg Spark Runtime** | `iceberg-spark-runtime-4.0_2.13-1.10.1.jar` | Integração Spark ↔ Iceberg (leitura/escrita tabelas) |
| **Iceberg AWS Bundle** | `iceberg-aws-bundle-1.10.1.jar` | Suporte S3/R2 para Iceberg |

---

## 🧊 **Formato de Tabela e Catálogo (Data Lakehouse)**

| Tecnologia | Versão/Detalhe | Uso no Projeto |
|------------|----------------|----------------|
| **Apache Iceberg** | 1.10.1 | Formato de tabela principal; transações ACID; time travel; schema evolution; partition evolution |
| **Iceberg REST Catalog** | - | Catálogo de metadados via REST API (backend PostgreSQL) |
| **Cloudflare R2** | S3-compatível | Armazenamento de dados (warehouse Iceberg); pay-per-request; assinatura própria (não AWS SigV4) |
| **Apache Parquet** | - | Formato de armazenamento colunar subjacente ao Iceberg |
| **ZSTD Compression** | - | Compressão padrão nos arquivos Parquet/Iceberg |

---

## 🗄️ **Banco de Dados e Metadados**

| Tecnologia | Versão/Detalhe | Uso no Projeto |
|------------|----------------|----------------|
| **PostgreSQL** | - | Backend do Airflow (metadados DAGs, runs, tasks); backend do Iceberg REST Catalog |
| **pgAdmin4** | - | Interface web para administração PostgreSQL (porta 5050) |

---

## ☁️ **Cloud e Infraestrutura**

| Tecnologia | Detalhe | Uso no Projeto |
|------------|---------|----------------|
| **Cloudflare R2** | Object storage S3-compatível | Data Lake principal; warehouse Iceberg (`s3://<bucket>/warehouse`) |
| **Cloudflare R2 API Tokens** | Bearer Token | Autenticação no Iceberg REST Catalog (`Authorization: Bearer <TOKEN>`) |
| **Render** | PaaS (mencionado no CLAUDE.md) | Deploy de produção (referência) |

---

## 📊 **Fontes de Dados (APIs e Portais Oficiais)**

| Fonte | Tecnologia de Acesso | Detalhes |
|-------|---------------------|----------|
| **IBGE SIDRA** | REST API v3 | Agregados PPM (~15) + Censo Agro (~357 filtrados); janela de calendário por ano; um período por request |
| **CONAB** | Web Scraping (HTML) | Portal `download-arquivos.html`; scraper 100% dinâmico; formatos: TXT (CSV `;`), XLS, XLSX, CSV |
| **INMET** | FTP / API (planejado) | Dados climáticos: temperatura, precipitação, umidade, radiação, vento, evapotranspiração |
| **EMBRAPA AgroAPI** | REST API (planejado) | ZARC, modelos de produtividade, indicadores agropecuários |

---

## 🐍 **Linguagens e Bibliotecas Python**

| Biblioteca | Uso no Projeto |
|------------|----------------|
| **pyspark** | Jobs Spark via Python |
| **requests** | HTTP client para APIs IBGE, CONAB scraping |
| **pandas** | Análise exploratória (notebooks); conversão Spark → Pandas para visualização |
| **matplotlib** | Gráficos estatísticos (notebooks Analytics) |
| **seaborn** | Visualizações estatísticas avançadas (notebooks Analytics) |
| **unicodedata** | Normalização Unicode → ASCII (remoção de acentos) |
| **re** | Expressões regulares (normalização de nomes) |
| **pendulum** | Timezone handling (America/Bahia) nas DAGs Airflow |
| **python-dotenv** | Carregamento de variáveis `.env` (desenvolvimento) |

---

## 📐 **Modelagem e Engenharia de Software**

| Metodologia/Conceito | Referência | Aplicação |
|---------------------|------------|-----------|
| **UML (Unified Modeling Language)** | - | Use Case diagrams, Component/Deployment views, ER conceitual |
| **Visão 4+1 (Kruchten)** | Kruchten, 1995 | Arquitetura: Lógica, Processo, Implementação, Implantação, Cenários |
| **RUP (Rational Unified Process)** | Adaptado para dados | Disciplinas: Modelagem de Negócio, Requisitos, Análise & Design, Implementação, Teste, Implantação |
| **Desenvolvimento Iterativo e Incremental** | Larman, 2004 | Sprints por fonte de dados (IBGE, CONAB, INMET, EMBRAPA) |
| **Engenharia de Requisitos** | Pressman, Sommerville | RFs/RNFs rastreáveis; casos de uso; matriz de rastreabilidade |
| **Análise de Riscos (Probabilidade × Impacto)** | PMBOK / ISO 31000 | Matriz de 8 riscos com mitigações implementadas em código |
| **Data Lakehouse Architecture** | Databricks / Iceberg | Camadas Bronze/Silver/Gold; ACID no Data Lake |
| **Medallion Architecture** | - | Bronze (raw) → Silver (clean/typed) → Gold (analytics) |

---

## 🔧 **Ferramentas de Desenvolvimento e Qualidade**

| Ferramenta | Uso |
|------------|-----|
| **Git / GitHub** | Controle de versão; repositório `nathanmsc/AGRODATA-PA` |
| **Jupyter Notebook** | Análise exploratória (`conab.ipynb`, `imnet.ipynb`) |
| **Google Colab** | Notebooks compartilhados (link no Apêndice C) |
| **Spark History Server** | Monitoramento de jobs Spark (performance, DAG visualization) |
| **Airflow UI** | Monitoramento de DAGs, tasks, logs, SLAs, retries |
| **Cloudflare Dashboard** | Monitoramento de custos R2 (storage + requests) |

---

## 📦 **Dependências de Sistema (Dockerfile)**

| Pacote | Finalidade |
|--------|------------|
| `openjdk-17-jre-headless` | JVM para Spark |
| `python3.11` | Runtime Python (imagem base `apache/airflow:3.0.0-python3.11`) |
| `pip` dependencies (`requirements.txt`) | Bibliotecas Python do projeto |

---

## 🔐 **Segurança e Configuração**

| Item | Detalhe |
|------|---------|
| **Airflow Connections** | Armazenamento seguro de credenciais (R2, PostgreSQL, APIs) |
| **Airflow Variables** | Configurações sensíveis (CATALOG_URI, WAREHOUSE, TOKEN) |
| **`.env` file** | Desenvolvimento local (gitignored) |
| **Header `X-Iceberg-Access-Delegation: vended-credentials`** | Workaround Iceberg ≥1.9 para delegação de credenciais R2 |
| **`s3.remote-signing-enabled=false`** | R2 usa assinatura própria (não AWS SigV4) |

---

## 📈 **Observabilidade e Métricas**

| Métrica | Ferramenta | Target |
|---------|------------|--------|
| **Freshness** | Airflow UI / SLA | D-1 disponível às 06:00 |
| **Completude IBGE** | Contagem tabelas Bronze | 100% agregados alvo |
| **Completude CONAB** | `listar_datasets()` vs tasks mapeadas | 100% datasets descobertos |
| **Taxa de falha** | Airflow metrics / Prometheus | < 5% tasks/execução |
| **Tempo ingestão IBGE** | Spark History Server | < 4 horas (357 agregados) |
| **Custo R2 mensal** | Cloudflare Dashboard | < $50 |
| **Schema evolution success** | Logs `schema_evolution.py` | 100% writes sem erro |

---

## 🧪 **Testes e Validação (Planejado/Futuro)**

| Ferramenta | Categoria | Status |
|------------|-----------|--------|
| **Great Expectations** | Data Quality | Planejado (Trabalho Futuro) |
| **Soda Core** | Data Quality | Planejado (Trabalho Futuro) |
| **dbt** | Transformação Silver/Gold | Planejado (Trabalho Futuro) |
| **DataHub / Amundsen** | Data Catalog/Discovery | Planejado (Trabalho Futuro) |

---

## 📚 **Referências Bibliográficas Citadas**

| Autor/Obra | Ano | Relevância |
|------------|-----|------------|
| Pressman, R. S. - *Engenharia de Software: Uma Abordagem Profissional* | 2010 | Fundamentos de engenharia de software aplicados a pipelines de dados |
| Sommerville, I. - *Engenharia de Software* | 2011 | Características de software (invisibilidade, complexidade, mutabilidade) |
| Larman, C. - *Applying UML and Patterns* | 2004 | Desenvolvimento iterativo e incremental; UML |
| Cooper, A. et al. - *About Face 3* | 2007 | Design centrado no usuário/stakeholder |
| Fowler, M. - *Patterns of Enterprise Application Architecture* | 2003 | Padrões de arquitetura (camadas, catálogo) |
| Kimball, R. & Ross, M. - *The Data Warehouse Toolkit* | 2013 | Modelagem dimensional (camada Gold) |
| Apache Iceberg / Airflow / Spark Docs | Atual | Referências técnicas oficiais |
| IBGE / CONAB / INMET / EMBRAPA Docs | Atual | Documentação das APIs e portais de dados |

---

## 📋 **Resumo por Camada da Arquitetura**

| Camada | Tecnologias Principais |
|--------|------------------------|
| **Apresentação** | Trino/Presto, Apache Superset, Jupyter/Python SDK |
| **Serviços/Catálogo** | Iceberg REST Catalog (PostgreSQL backend) |
| **Processamento** | Apache Spark 3.x + PySpark, Iceberg Spark Runtime |
| **Armazenamento** | Cloudflare R2 (S3-compatível), Apache Parquet, ZSTD |
| **Orquestração** | Apache Airflow 3.0, Dynamic Task Mapping, Docker Compose |
| **Fontes** | IBGE SIDRA API, CONAB Scraper, INMET, EMBRAPA AgroAPI |
| **Infra/Base** | OpenJDK 17, PostgreSQL, pgAdmin4, Docker, GitHub |

---

## 🏷️ **Tags de Classificação**

```yaml
categories:
  - Data Engineering
  - Data Lakehouse
  - Apache Iceberg
  - Apache Airflow
  - Apache Spark
  - Cloudflare R2
  - Brazilian Agribusiness
  - IBGE SIDRA
  - CONAB
  - INMET
  - EMBRAPA
  - UML
  - Software Engineering
  - Schema Evolution
  - Dynamic Task Mapping
  - Medallion Architecture
  - ELT Pipeline
  - ACID Transactions
  - Time Travel
  - Data Governance
```

---

*Documento gerado a partir da análise do arquivo `DOCUMENTS/Artigo.md` do projeto AGRODATA-PA.*
*Versão: 1.0 — Julho 2026*