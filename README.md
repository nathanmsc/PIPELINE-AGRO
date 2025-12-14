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
