# PIPELINE-AGRO

### PIPELINE DE DADOS DO AGRONEGÓCIO

#### FONTES DE DADOS


| Fonte / Instituição | API / Interface | Formato dos Dados | Frequência | Limitações Técnicas |
|--------------------|-----------------|-------------------|------------|---------------------|
| [INMET](https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip) | Download manual | ZIP / CSV | mensal | Sem limite formal |
| [IBGE – SIDRA](https://apisidra.ibge.gov.br/) | SOAP / REST | XML / JSON | Anual | Sem limite formal |
| [CONAB](https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosMensalUF.txt) | Downloads manuais | CSV / Excel | Mensal | Sem limite formal |
| CEPEA | Web scraping | HTML | Diária | Necessita parsing de páginas |
| ANA (Hidrologia) | REST API | JSON | Diária | Requer autenticação OAuth 2.0 |


IBGE – Serviços de Dados: https://servicodados.ibge.gov.br/api/docs

---

### INMET - DADOS CLIMÁTICOS

[EXTRACT FROM IMNET](ETL/imnet.ipynb)
---

### CONAB

[CONAB](ETL/imnet.ipynb)
---

### SIDRA PRODUÇÃO AGRÍCOLA

```py
# Consulta via API SIDRA
api_url = "https://apisidra.ibge.gov.br/values"
query_params = {
    "t": "1612",  # Tabela: Produção Agrícola Municipal
    "v": "214,112,216",  # Variáveis: área plantada, produção, rendimento
    "p": "2023",  # Período
    "n1": "6",  # Nível territorial: Brasil
    "c81": "2713",  # Produto: Soja
    "format": "json"
}

# Schema esperado do retorno
schema_sidra = {
    "V": "Código da variável",
    "D1C": "Cultura agrícola", 
    "D2C": "Município",
    "D3C": "Ano",
    "V": "Valor",
    "U": "Unidade de medida"
}
```
---
### Arquitetura Lambda Modificada


                          ┌───────────────────────────┐
                          │     CAMADA DE INGESTÃO    │
                          │                           │
                          │     ┌──────────────┐      │
                          │     │   Airflow    │      │
                          │     │  Scheduler   │      │
                          │     └──────────────┘      │
                          └──────────────┬────────────┘
                                         │
                                         ▼
        ┌───────────────────────────────────────────────────────────┐
        |                   DATA LAKE - [R2 / Bucket]               | 
        │     https://pub-a8167dbe4471488a908c0920420b2bba.r2.dev   │
        │   ┌────────────────────────────────────────────────────┐  │
        │   │ Raw Zone (Bronze)                                  │  │
        │   │ - Dados brutos no formato original                 │  │
        │   │ - Particionamento: /source/year/month/day/         │  │
        │   │ - Formatos: JSON, CSV, Parquet                     │  │
        │   │ - Retenção: 365 dias                               │  │
        │   └────────────────────────────────────────────────────┘  │
        │                                                           │
        │   ┌────────────────────────────────────────────────────┐  │
        │   │ Refined Zone (Silver)                              │  │
        │   │ - Dados limpos e padronizados                      │  │
        │   │ - Schema enforcement (Delta Lake)                  │  │
        │   │ - Formato: Delta / Parquet                         │  │
        │   │ - Compressão: Snappy                               │  │
        │   │ - Retenção: 730 dias                               │  │
        │   └────────────────────────────────────────────────────┘  │
        │                                                           │
        │   ┌────────────────────────────────────────────────────┐  │
        │   │ Curated Zone (Gold)                                │  │
        │   │ - Dados agregados e features analíticas            │  │
        │   │ - Modelagem dimensional (Star Schema)              │  │
        │   │ - Formato: Parquet otimizado                       │  │
        │   │ - Compressão: ZSTD                                 │  │
        │   │ - Retenção: Indefinida                             │  │
        │   └────────────────────────────────────────────────────┘  │
        └──────────────────────────────┬────────────────────────────┘
                                       │
                                       ▼
                          ┌───────────────────────────┐
                          │     PROCESSAMENTO BATCH   │
                          │                           │
                          │ - Apache Spark            │
                          │ - Orquestração: Airflow   │
                          │ - Execução: Diário/Semanal│
                          └──────────────┬────────────┘
                                         │
                                         ▼
                          ┌───────────────────────────┐
                          │       SERVING LAYER       │
                          │                           │
                          │ - PostgreSQL (OLAP)       │
                          │ - Data Warehouse          │
                          │ - Modelagem dimensional   │
                          └──────────────┬────────────┘
                                         │
                                         ▼
                          ┌───────────────────────────┐
                          │     CONSUMPTION LAYER     │
                          │                           │
                          │ - Dashboards BI           │
                          │ - Jupyter Notebooks       │
                          │ - Análises exploratórias  │
                          └───────────────────────────┘

---
