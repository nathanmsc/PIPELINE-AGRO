# PIPELINE-AGRO

### PIPELINE DE DADOS DO AGRONEGÓCIO

#### Fontes de dados

https://apitempo.inmet.gov.br/estacao/dados/
https://apisidra.ibge.gov.br/
https://servicodados.ibge.gov.br/api/docs

| Fonte / Instituição | API / Interface | Formato dos Dados | Frequência | Limitações Técnicas |
|--------------------|-----------------|-------------------|------------|---------------------|
| INMET              | REST API        | JSON              | Horária    | Rate limit: 1000 requisições/dia |
| IBGE – SIDRA       | SOAP / REST     | XML / JSON        | Anual      | Sem limite formal |
| CONAB              | Downloads manuais | CSV / Excel     | Mensal     | Não possui API pública |
| CEPEA              | Web scraping    | HTML              | Diária     | Necessita parsing de páginas |
| ANA (Hidrologia)   | REST API        | JSON              | Diária     | Requer autenticação OAuth 2.0 |
