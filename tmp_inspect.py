import sys
import requests
from pathlib import Path
sys.path.insert(0, r'd:\Documents\src\AGRODATA-PA\CORE\AIRFLOW\dags')
from utils.conab_scraper import scraper_conab

items = scraper_conab()
print('datasets', len(items))
for idx, item in enumerate(items[:12]):
    print('IDX', idx, item['categoria'], '|', item['tabela'], '|', item['extensao'])
    print('URL', item['url'])
    try:
        r = requests.get(item['url'], timeout=30)
        r.raise_for_status()
        text = r.text
        lines = text.splitlines()
        print('first line', lines[0][:500])
        if len(lines) > 1:
            print('second line', lines[1][:500])
    except Exception as e:
        print('ERR', e)
    print('---')
