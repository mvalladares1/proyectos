"""Ver campos del modelo de trasferencias"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.odoo_client import OdooClient

client = OdooClient(
    username='mvalladares@riofuturo.cl',
    password='c0766224bec30cac071ffe43a858c9ccbd521ddd',
    url='https://riofuturo.server98c6e.oerpondemand.net',
    db='riofuturo-master'
)

# Ver campos del modelo
fields = client.search_read(
    'ir.model.fields',
    [['model', '=', 'x_trasferencias_dashboard_v2']],
    ['name', 'field_description', 'ttype', 'relation']
)

print('Campos de x_trasferencias_dashboard_v2:')
print('=' * 80)
for f in fields:
    rel = f" -> {f['relation']}" if f.get('relation') else ''
    print(f"  {f['name']:<30} | {f['ttype']:<15} | {f['field_description']}{rel}")
