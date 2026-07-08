```py
import requests

dados = requests.get(
    "https://servicodados.ibge.gov.br/api/v3/agregados"
).json()

for pesquisa in dados:
    print(f"\n{pesquisa['id']} - {pesquisa['nome']}")
    print(f"Agregados: {len(pesquisa['agregados'])}")
```
