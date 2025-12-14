# PIPELINE-AGRO

### PIPELINE DE DADOS DO AGRONEGÓCIO

#### Fontes de dados


| Fonte / Instituição | API / Interface | Formato dos Dados | Frequência | Limitações Técnicas |
|--------------------|-----------------|-------------------|------------|---------------------|
| [INMET](https://apitempo.inmet.gov.br/estacao/dados/) | REST API | JSON | Horária | Rate limit: 1000 requisições/dia |
| [IBGE – SIDRA](https://apisidra.ibge.gov.br/) | SOAP / REST | XML / JSON | Anual | Sem limite formal |
| CONAB | Downloads manuais | CSV / Excel | Mensal | Não possui API pública |
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

### 1.3 Arquitetura Técnica Detalhada

#### 1.3.1 Arquitetura Lambda Modificada
```
┌─────────────────────────────────────────────────────────────┐
│                     CAMADA DE INGESTÃO                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  NiFi    │  │ Airflow  │  │  Kafka   │  │  Lambda  │   │
│  │ Crawler  │  │ Scheduler│  │ Producer │  │ Functions│   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
└───────┼────────────┼─────────────┼─────────────┼──────────┘
        │            │             │             │
        ▼            ▼             ▼             ▼
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAKE (S3/MinIO)                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Raw Zone (Bronze)                                    │  │
│  │  - Dados brutos no formato original                  │  │
│  │  - Particionamento: /source/year/month/day/          │  │
│  │  - Formato: JSON, CSV, Parquet                       │  │
│  │  - Retenção: 365 dias                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Refined Zone (Silver)                                │  │
│  │  - Dados limpos e padronizados                       │  │
│  │  - Schema enforcement via Delta Lake                 │  │
│  │  - Formato: Delta/Parquet + metadados                │  │
│  │  - Compressão: Snappy                                │  │
│  │  - Retenção: 730 dias                                │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Curated Zone (Gold)                                  │  │
│  │  - Dados agregados e features                        │  │
│  │  - Modelos dimensionais (Star Schema)               │  │
│  │  - Formato: Parquet otimizado                       │  │
│  │  - Compressão: ZSTD                                  │  │
│  │  - Retenção: Indefinida                              │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
        │                                       │
        ▼                                       ▼
┌─────────────────────┐            ┌──────────────────────────┐
│  BATCH PROCESSING   │            │   SPEED LAYER (Opcional)  │
│  - Spark/Airflow    │            │   - Kafka Streams         │
│  - Processamento    │            │   - Flink                 │
│  - Diário/Semanal   │            │   - Dados tempo real      │
└──────────┬──────────┘            └───────────┬──────────────┘
           │                                    │
           └────────────────┬───────────────────┘
                            ▼
                ┌───────────────────────┐
                │  SERVING LAYER        │
                │  - PostgreSQL (OLTP)  │
                │  - Redshift (OLAP)    │
                │  - Elasticsearch      │
                │  - Redis (Cache)      │
                └───────────┬───────────┘
                            │
                            ▼
                ┌───────────────────────┐
                │  CONSUMPTION LAYER    │
                │  - Power BI           │
                │  - Tableau            │
                │  - APIs REST          │
                │  - Jupyter Notebooks  │
                └───────────────────────┘
```
