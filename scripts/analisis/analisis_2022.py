import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from collections import defaultdict

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 100)
print("ANÁLISIS DE DATOS 2022")
print("=" * 100)

# Compras 2022
print("\n📦 COMPRAS 2022:")
compras_2022 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['display_type', '=', 'product'],
        ['account_id.code', 'in', ['21020107', '21020106']],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2022-12-31']
    ],
    ['id', 'date', 'quantity', 'debit', 'move_id', 'product_id'],
    limit=100000
)

print(f"   Líneas encontradas: {len(compras_2022):,}")

if compras_2022:
    total_kg = sum(l.get('quantity', 0) for l in compras_2022)
    total_monto = sum(l.get('debit', 0) for l in compras_2022)
    print(f"   Total kg: {total_kg:,.2f}")
    print(f"   Total monto: ${total_monto:,.0f}")
    
    print("\n   Primeras 10 facturas:")
    for i, l in enumerate(compras_2022[:10], 1):
        move_name = l.get('move_id', [None, 'N/A'])[1]
        fecha = l.get('date')
        kg = l.get('quantity', 0)
        monto = l.get('debit', 0)
        prod = l.get('product_id', [None, 'N/A'])[1]
        print(f"   {i}. {move_name} ({fecha}): {kg:,.1f} kg | ${monto:,.0f} | {prod[:50]}")

# Ventas 2022
print("\n💰 VENTAS 2022:")
ventas_2022 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['display_type', '=', 'product'],
        ['account_id.code', 'not in', ['41010202', '43010111', '71010204']],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2022-12-31']
    ],
    ['id', 'date', 'quantity', 'credit', 'debit', 'move_id', 'product_id', 'name'],
    limit=100000
)

print(f"   Líneas encontradas: {len(ventas_2022):,}")

if ventas_2022:
    total_kg = sum(l.get('quantity', 0) for l in ventas_2022)
    total_monto = sum(l.get('credit', 0) - l.get('debit', 0) for l in ventas_2022)
    print(f"   Total kg: {total_kg:,.2f}")
    print(f"   Total monto: ${total_monto:,.0f}")
    
    print("\n   Primeras 10 facturas:")
    for i, l in enumerate(ventas_2022[:10], 1):
        move_name = l.get('move_id', [None, 'N/A'])[1]
        fecha = l.get('date')
        kg = l.get('quantity', 0)
        monto = l.get('credit', 0) - l.get('debit', 0)
        
        prod_id = l.get('product_id')
        if prod_id:
            prod_name = prod_id[1]
        else:
            prod_name = l.get('name', 'TEXTO LIBRE')
        
        print(f"   {i}. {move_name} ({fecha}): {kg:,.1f} kg | ${monto:,.0f} | {prod_name[:50]}")

# Verificar distribución por mes
print("\n" + "=" * 100)
print("📅 DISTRIBUCIÓN POR MES 2022")
print("=" * 100)

meses_compras = defaultdict(lambda: {'kg': 0, 'monto': 0, 'lineas': 0})
for l in compras_2022:
    fecha = l.get('date', '')
    if fecha:
        mes = fecha[:7]  # YYYY-MM
        meses_compras[mes]['kg'] += l.get('quantity', 0)
        meses_compras[mes]['monto'] += l.get('debit', 0)
        meses_compras[mes]['lineas'] += 1

print("\n📦 COMPRAS por mes:")
for mes in sorted(meses_compras.keys()):
    data = meses_compras[mes]
    print(f"   {mes}: {data['lineas']:3d} líneas | {data['kg']:10,.0f} kg | ${data['monto']:15,.0f}")

meses_ventas = defaultdict(lambda: {'kg': 0, 'monto': 0, 'lineas': 0})
for l in ventas_2022:
    fecha = l.get('date', '')
    if fecha:
        mes = fecha[:7]
        meses_ventas[mes]['kg'] += l.get('quantity', 0)
        meses_ventas[mes]['monto'] += l.get('credit', 0) - l.get('debit', 0)
        meses_ventas[mes]['lineas'] += 1

print("\n💰 VENTAS por mes:")
for mes in sorted(meses_ventas.keys()):
    data = meses_ventas[mes]
    print(f"   {mes}: {data['lineas']:3d} líneas | {data['kg']:10,.0f} kg | ${data['monto']:15,.0f}")

print("\n" + "=" * 100)
