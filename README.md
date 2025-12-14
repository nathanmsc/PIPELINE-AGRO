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
        │                    DATA LAKE (S3 / MinIO)                 │
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
---
```img
<svg width="1100" height="1300" viewBox="0 0 1100 1300"
     xmlns="http://www.w3.org/2000/svg"
     font-family="Arial, Helvetica, sans-serif">

  <defs>
    <style>
      .box { fill: #ffffff; stroke: #000000; stroke-width: 2; }
      .title { font-size: 18px; font-weight: bold; text-anchor: middle; }
      .text { font-size: 14px; }
      .arrow { stroke: #000000; stroke-width: 2; fill: none; marker-end: url(#arrowhead); }
    </style>

    <marker id="arrowhead" markerWidth="10" markerHeight="7"
            refX="10" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#000000"/>
    </marker>
  </defs>

  <!-- INGESTÃO -->
  <rect x="400" y="40" width="300" height="120" class="box"/>
  <text x="550" y="70" class="title">CAMADA DE INGESTÃO</text>
  <rect x="460" y="90" width="180" height="50" class="box"/>
  <text x="550" y="120" class="text" text-anchor="middle">Apache Airflow</text>

  <line x1="550" y1="160" x2="550" y2="200" class="arrow"/>

  <!-- DATA LAKE -->
  <rect x="150" y="200" width="800" height="460" class="box"/>
  <text x="550" y="230" class="title">DATA LAKE (S3 / MinIO)</text>

  <!-- Bronze -->
  <rect x="200" y="260" width="700" height="110" class="box"/>
  <text x="550" y="285" class="title">Raw Zone (Bronze)</text>
  <text x="220" y="310" class="text">• Dados brutos no formato original</text>
  <text x="220" y="330" class="text">• Particionamento: /source/year/month/day/</text>
  <text x="220" y="350" class="text">• Formatos: JSON, CSV, Parquet</text>

  <!-- Silver -->
  <rect x="200" y="390" width="700" height="110" class="box"/>
  <text x="550" y="415" class="title">Refined Zone (Silver)</text>
  <text x="220" y="440" class="text">• Dados limpos e padronizados</text>
  <text x="220" y="460" class="text">• Schema enforcement (Delta Lake)</text>
  <text x="220" y="480" class="text">• Compressão: Snappy</text>

  <!-- Gold -->
  <rect x="200" y="520" width="700" height="110" class="box"/>
  <text x="550" y="545" class="title">Curated Zone (Gold)</text>
  <text x="220" y="570" class="text">• Dados agregados e features analíticas</text>
  <text x="220" y="590" class="text">• Modelagem dimensional (Star Schema)</text>
  <text x="220" y="610" class="text">• Compressão: ZSTD</text>

  <line x1="550" y1="660" x2="550" y2="710" class="arrow"/>

  <!-- PROCESSAMENTO -->
  <rect x="400" y="710" width="300" height="130" class="box"/>
  <text x="550" y="740" class="title">PROCESSAMENTO BATCH</text>
  <text x="430" y="770" class="text">• Apache Spark</text>
  <text x="430" y="795" class="text">• Orquestração: Airflow</text>
  <text x="430" y="820" class="text">• Execução: Diário / Semanal</text>

  <line x1="550" y1="840" x2="550" y2="890" class="arrow"/>

  <!-- SERVING -->
  <rect x="400" y="890" width="300" height="120" class="box"/>
  <text x="550" y="920" class="title">SERVING LAYER</text>
  <text x="430" y="950" class="text">• PostgreSQL (OLAP)</text>
  <text x="430" y="975" class="text">• Data Warehouse</text>

  <line x1="550" y1="1010" x2="550" y2="1060" class="arrow"/>

  <!-- CONSUMO -->
  <rect x="400" y="1060" width="300" height="120" class="box"/>
  <text x="550" y="1090" class="title">CONSUMPTION LAYER</text>
  <text x="430" y="1120" class="text">• Dashboards BI</text>
  <text x="430" y="1145" class="text">• Jupyter Notebooks</text>
  <text x="430" y="1170" class="text">• Análises exploratórias</text>

</svg>
```
