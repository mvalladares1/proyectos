"""
Analizar qué cuentas contables se usan en facturas de cliente
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("\n🔍 ANALIZANDO CUENTAS EN FACTURAS DE CLIENTE...")
print("=" * 100)

# Buscar TODAS las líneas de facturas de cliente con productos
lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['date', '>=', '2023-01-01'],
        ['date', '<=', '2024-12-31']
    ],
    ['account_id', 'product_id', 'quantity', 'debit', 'credit'],
    limit=1000
)

print(f"\n✓ Total líneas analizadas: {len(lineas):,}")

# Agrupar por cuenta
cuentas_map = {}
for linea in lineas:
    account_info = linea.get('account_id')
    if account_info:
        account_id, account_name = account_info if isinstance(account_info, (list, tuple)) else (None, str(account_info))
        
        if account_name not in cuentas_map:
            cuentas_map[account_name] = {
                'lineas': 0,
                'debito_total': 0,
                'credito_total': 0,
                'cantidad_total': 0
            }
        
        cuentas_map[account_name]['lineas'] += 1
        cuentas_map[account_name]['debito_total'] += linea.get('debit', 0)
        cuentas_map[account_name]['credito_total'] += linea.get('credit', 0)
        cuentas_map[account_name]['cantidad_total'] += abs(linea.get('quantity', 0))

print("\n📊 CUENTAS CONTABLES USADAS:")
print("=" * 100)
print(f"{'Cuenta':<50} {'Líneas':>10} {'Débito':>18} {'Crédito':>18} {'Cantidad (kg)':>15}")
print("-" * 100)

for cuenta, data in sorted(cuentas_map.items(), key=lambda x: -x[1]['lineas']):
    print(f"{cuenta:<50} {data['lineas']:>10,} ${data['debito_total']:>16,.2f} ${data['credito_total']:>16,.2f} {data['cantidad_total']:>14,.2f}")

print("\n" + "=" * 100)
