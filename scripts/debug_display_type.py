import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 80)
print("ANÁLISIS DE DISPLAY_TYPE EN VENTAS")
print("=" * 80)

# Obtener todas las líneas con PRODUCTOS
lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id', 'display_type', 'name', 'credit', 'debit', 'move_id'],
    limit=100000
)

print(f"\nTotal líneas: {len(lineas):,}")

# Contar display_type
display_types = {}
for linea in lineas:
    dt = linea.get('display_type') or 'False/None'
    display_types[dt] = display_types.get(dt, 0) + 1

print("\n📊 DISTRIBUCIÓN POR DISPLAY_TYPE:")
for dt, count in sorted(display_types.items(), key=lambda x: -x[1]):
    print(f"   {dt:20s}: {count:,} líneas ({count/len(lineas)*100:.1f}%)")

# Ver ejemplos de los que NO son 'product'
print("\n📋 MUESTRA DE LÍNEAS CON display_type False/None (primeras 10):")
no_product = [l for l in lineas if l.get('display_type') != 'product'][:10]

for i, linea in enumerate(no_product, 1):
    move_name = linea.get('move_id', [None, 'N/A'])[1]
    print(f"\n{i}. Factura: {move_name}")
    print(f"   ID: {linea['id']}")
    print(f"   display_type: {linea.get('display_type')}")
    print(f"   name: {linea.get('name', 'N/A')[:60]}")
    print(f"   credit: ${linea.get('credit', 0):,.0f}")
    print(f"   debit: ${linea.get('debit', 0):,.0f}")

print("\n" + "=" * 80)
