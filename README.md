# 🌱 AGRODATA-PA

## Projeto Aplicado de Pipeline de Dados para o Agronegócio

Uma arquitetura de dados para consolidar, processar e disponibilizar informações estratégicas do agronegócio brasileiro em um ambiente centralizado de Data Lake.

---

# 🎯 Objetivos

- Monitoramento de safras
- Inteligência de mercado
- Planejamento agrícola
- Gestão climática
- Análise territorial e ambiental
- Modelagem preditiva

---

# 🗂️ Domínios de Dados

## 1. Produção Agrícola e Estatísticas Oficiais

### IBGE — Agregados

| Dataset | Aplicação |
|----------|------------|
| Produção Agrícola Municipal (PAM) | Planejamento da produção |
| Produção Pecuária Municipal (PPM) | Bovinocultura, leite, aves e mel |
| Censo Agropecuário | Perfil da propriedade rural |
| Valor da Produção Agropecuária | Rentabilidade regional |
| Agricultura Familiar | Políticas públicas |
| Sistemas de Irrigação | Adoção tecnológica |
| Máquinas Agrícolas | Nível de mecanização |
| Uso da Terra | Expansão agrícola |
| Demografia Rural | Mercado consumidor e mão de obra |

---

## 2. Mercado Agrícola e Economia Rural

### CONAB

Disponibiliza:

- Estimativas de safra
- Custos de produção
- Estoques públicos
- Logística e armazenagem
- Fretes
- Oferta e demanda
- Séries históricas de preços

---

## 3. Clima e Meio Ambiente

### INMET

- Temperatura
- Precipitação
- Umidade
- Radiação solar
- Velocidade do vento
- Evapotranspiração


---

## 4. Sanidade Agropecuária e Zoneamento

### EMBRAPA AgroAPI

- ZARC
- Modelos de produtividade
- Indicadores agropecuários

---

# 🏗️ Arquitetura de Dados

```text
FONTES DE DADOS
       │
       ▼
    Airflow
       │
       ▼
 Data Lake (R2)
       │
       ▼
 Apache Spark
       │
       ▼
 Data Warehouse
       │
       ▼
 BI & Analytics
```

---

# ⚙️ Camadas do Data Lake

## Bronze Layer

- Dados brutos
- CSV, JSON e Parquet
- Histórico completo

## Silver Layer

- Dados limpos e padronizados
- Delta Lake
- Parquet + Snappy

## Gold Layer

- Indicadores analíticos
- Features para ML
- Star Schema
- Compressão ZSTD

---

# 🔄 Orquestração

## Apache Airflow

- ETL / ELT
- Agendamento
- Observabilidade
- Gestão de SLA

---

# 🚀 Processamento

## Apache Spark

- Processamento distribuído
- Batch analytics
- Transformações em larga escala
- Enriquecimento geoespacial

---

# 🗄️ Armazenamento

## Cloudflare R2

Catalog URI:

```text
https://catalog.cloudflarestorage.com/515e2015338845cbadff913ac19d97a0/pabucket
```

Warehouse:

```text
515e2015338845cbadff913ac19d97a0_pabucket
```

---

# 📊 Consumo dos Dados

### BI

- Power BI
- Superset
- Metabase

### Data Science

- Jupyter
- Python
- Spark SQL

### APIs

- REST APIs
- Modelos Preditivos
- Aplicações Analíticas

---

# 🌾 Visão Estratégica

O PIPELINE AGRO centraliza dados de produção, mercado, clima, território e sanidade agropecuária em uma arquitetura Lakehouse escalável, transformando dados públicos em inteligência para tomada de decisão.
