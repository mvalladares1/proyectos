import sys
sys.path.append(r'c:\new\RIO FUTURO\DASHBOARD')
from shared.odoo_client import OdooClient
from dotenv import load_dotenv
import os

load_dotenv()
odoo = OdooClient(username=os.getenv('ODOO_USERNAME'), password=os.getenv('ODOO_PASSWORD'))

# Ver campos de quality.check
campos_quality = odoo.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type']})

print('Campos que contienen "calific":')
for k, v in campos_quality.items():
    if 'calific' in k.lower() or 'calific' in v.get('string', '').lower():
        print(f'  {k}: {v["string"]} ({v.get("type", "")})')

print('\nCampos que contienen "clasificac":')
for k, v in campos_quality.items():
    if 'clasificac' in k.lower() or 'clasificac' in v.get('string', '').lower():
        print(f'  {k}: {v["string"]} ({v.get("type", "")})')

print('\nCampos que contienen "defecto":')
for k, v in campos_quality.items():
    if 'defecto' in k.lower() or 'defecto' in v.get('string', '').lower():
        print(f'  {k}: {v["string"]} ({v.get("type", "")})')

print('\nCampos que contienen "palet" o "pallet":')
for k, v in campos_quality.items():
    if 'palet' in k.lower() or 'palet' in v.get('string', '').lower():
        print(f'  {k}: {v["string"]} ({v.get("type", "")})')

# Obtener un quality check reciente para ver sus datos
print('\n\nEjemplo de quality.check reciente:')
qcs = odoo.search_read(
    'quality.check',
    [('create_date', '>=', '2025-11-01')],
    [],
    limit=1
)
if qcs:
    print(f'\nQuality Check ID: {qcs[0].get("id")}')
    print('Campos relevantes:')
    for key, value in qcs[0].items():
        if any(x in key.lower() for x in ['calific', 'clasificac', 'defecto', 'palet', 'temp', 'hongos', 'inmadura']):
            print(f'  {key}: {value}')
