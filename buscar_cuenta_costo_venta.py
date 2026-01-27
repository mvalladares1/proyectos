import sys
sys.path.insert(0, '.')
from shared.odoo_client import OdooClient

odoo = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

# Buscar cuentas de costo de venta
cuentas = odoo.search_read('account.account', [['code', 'ilike', '51']], ['id', 'code', 'name'], limit=30)

print("\n🔍 CUENTAS DE COSTO (51xxxx):")
print("=" * 80)
for c in cuentas:
    print(f"{c['code']:15} {c['name']}")
