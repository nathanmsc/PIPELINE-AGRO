# PIPELINE-AGRO

### PIPELINE DE DADOS DO AGRONEGÓCIO

#### Fontes de dados


| Fonte / Instituição | API / Interface | Formato dos Dados | Frequência | Limitações Técnicas |
|--------------------|-----------------|-------------------|------------|---------------------|
| [INMET](https://portal.inmet.gov.br/uploads/dadoshistoricos/2025.zip) | Download manual | ZIP / CSV | mensal | Sem limite formal |
| [IBGE – SIDRA](https://apisidra.ibge.gov.br/) | SOAP / REST | XML / JSON | Anual | Sem limite formal |
| [CONAB](https://portaldeinformacoes.conab.gov.br/downloads/arquivos/PrecosMensalUF.txt) | Downloads manuais | CSV / Excel | Mensal | Sem limite formal |
| CEPEA | Web scraping | HTML | Diária | Necessita parsing de páginas |
| ANA (Hidrologia) | REST API | JSON | Diária | Requer autenticação OAuth 2.0 |


IBGE – Serviços de Dados: https://servicodados.ibge.gov.br/api/docs

### INMET - DADOS CLIMÁTICOS

```py
# Especificação técnica detalhada
endpoint = "https://apitempo.inmet.gov.br/estacao/dados/"
parametros = {
    "dataInicio": "YYYY-MM-DD",
    "dataFim": "YYYY-MM-DD",
    "codEstacao": "A001"  # Código da estação meteorológica
}
headers = {
    "Authorization": f"Bearer {token}"
}

# Campos retornados
campos_resposta = {
    "DC_NOME": "Nome da estação",
    "VL_LATITUDE": "Latitude",
    "VL_LONGITUDE": "Longitude",
    "DT_MEDICAO": "Data/hora da medição",
    "TEM_INS": "Temperatura instantânea (°C)",
    "PRE_INS": "Precipitação instantânea (mm)",
    "UMD_INS": "Umidade relativa (%)"
}

# Tratamento de erros específicos
erros_conhecidos = {
    400: "Parâmetros inválidos - verificar formato de data",
    401: "Token de autenticação expirado",
    429: "Rate limit excedido - implementar backoff exponencial",
    503: "Serviço temporariamente indisponível - retry após 5min"
}
```
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

**Estratégias de Fallback:**
- Cache local de 7 dias para dados críticos
- Endpoints alternativos (mirrors regionais)
- Dados históricos como fonte secundária

---

#### Arquitetura Lambda Modificada
```
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
        │                    [DATA LAKE (R2 / Bucket)](https://pub-a8167dbe4471488a908c0920420b2bba.r2.dev)                │
        │                                                           │
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

```
