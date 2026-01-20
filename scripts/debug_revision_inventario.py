"""
Debug: Verificar datos de inventario Nov 2025 - Ene 2026
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("DEBUG INVENTARIO: 2025-11-24 a 2026-01-31")
print("="*140)

# COMPRAS
print("\n" + "="*140)
print("FACTURAS DE COMPRA (in_invoice)")
print("="*140)

lineas_compra = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2025-11-24'],
        ['date', '<=', '2026-01-31'],
        ['quantity', '>', 0],
        ['debit', '>', 0],
        ['account_id.code', '=like', '21%']
    ],
    ['product_id', 'quantity', 'price_unit', 'debit', 'date', 'move_id'],
    limit=5000
)

print(f"\nTotal líneas: {len(lineas_compra)}")

# Obtener productos
prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_compra if l.get('product_id')]))
productos = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids]],
    ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
    limit=5000
)
prod_map = {p['id']: p for p in productos}

# Calcular totales
total_kg = sum([l.get('quantity', 0) for l in lineas_compra])
total_monto = sum([l.get('debit', 0) for l in lineas_compra])

print(f"Total KG: {total_kg:,.2f}")
print(f"Total Monto: ${total_monto:,.0f}")
print(f"Precio Promedio: ${total_monto/total_kg:,.2f}/kg")

# Agrupar por tipo de fruta
resumen_compra = {}
for linea in lineas_compra:
    prod_id = linea.get('product_id', [None])[0]
    if prod_id and prod_id in prod_map:
        prod = prod_map[prod_id]
        
        tipo = prod.get('x_studio_sub_categora')
        tipo = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else str(tipo) if tipo else "Sin clasificar"
        
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        manejo = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else str(manejo) if manejo else "Sin clasificar"
        
        key = f"{tipo} - {manejo}"
        if key not in resumen_compra:
            resumen_compra[key] = {'kg': 0, 'monto': 0}
        
        resumen_compra[key]['kg'] += linea.get('quantity', 0)
        resumen_compra[key]['monto'] += linea.get('debit', 0)

print("\nRESUMEN COMPRAS POR TIPO:")
print(f"{'Tipo - Manejo':<40} {'KG':>15} {'Monto':>20} {'$/kg':>12}")
print("-" * 90)
for key in sorted(resumen_compra.keys()):
    datos = resumen_compra[key]
    precio = datos['monto'] / datos['kg'] if datos['kg'] > 0 else 0
    print(f"{key:<40} {datos['kg']:>15,.0f} ${datos['monto']:>19,.0f} ${precio:>11,.2f}")

# VENTAS
print("\n" + "="*140)
print("FACTURAS DE VENTA (out_invoice)")
print("="*140)

lineas_venta = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2025-11-24'],
        ['date', '<=', '2026-01-31'],
        ['quantity', '>', 0],
        ['credit', '>', 0],
        ['account_id.code', '=like', '41%']
    ],
    ['product_id', 'quantity', 'price_unit', 'credit', 'date', 'move_id'],
    limit=5000
)

print(f"\nTotal líneas: {len(lineas_venta)}")

# Obtener productos
prod_ids_venta = list(set([l.get('product_id', [None])[0] for l in lineas_venta if l.get('product_id')]))
productos_venta = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids_venta]],
    ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
    limit=5000
)
prod_map_venta = {p['id']: p for p in productos_venta}

# Calcular totales
total_kg_venta = sum([l.get('quantity', 0) for l in lineas_venta])
total_monto_venta = sum([l.get('credit', 0) for l in lineas_venta])

print(f"Total KG: {total_kg_venta:,.2f}")
print(f"Total Monto: ${total_monto_venta:,.0f}")
print(f"Precio Promedio: ${total_monto_venta/total_kg_venta:,.2f}/kg")

# Agrupar por tipo de fruta
resumen_venta = {}
for linea in lineas_venta:
    prod_id = linea.get('product_id', [None])[0]
    if prod_id and prod_id in prod_map_venta:
        prod = prod_map_venta[prod_id]
        
        tipo = prod.get('x_studio_sub_categora')
        tipo = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else str(tipo) if tipo else "Sin clasificar"
        
        manejo = prod.get('x_studio_categora_tipo_de_manejo')
        manejo = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else str(manejo) if manejo else "Sin clasificar"
        
        key = f"{tipo} - {manejo}"
        if key not in resumen_venta:
            resumen_venta[key] = {'kg': 0, 'monto': 0}
        
        resumen_venta[key]['kg'] += linea.get('quantity', 0)
        resumen_venta[key]['monto'] += linea.get('credit', 0)

print("\nRESUMEN VENTAS POR TIPO:")
print(f"{'Tipo - Manejo':<40} {'KG':>15} {'Monto':>20} {'$/kg':>12}")
print("-" * 90)
for key in sorted(resumen_venta.keys()):
    datos = resumen_venta[key]
    precio = datos['monto'] / datos['kg'] if datos['kg'] > 0 else 0
    print(f"{key:<40} {datos['kg']:>15,.0f} ${datos['monto']:>19,.0f} ${precio:>11,.2f}")

print("\n" + "="*140)
print("ANÁLISIS")
print("="*140)
print(f"""
HALLAZGOS:
1. Compras: {total_kg:,.0f} kg @ ${total_monto/total_kg:,.2f}/kg = ${total_monto:,.0f}
2. Ventas:  {total_kg_venta:,.0f} kg @ ${total_monto_venta/total_kg_venta:,.2f}/kg = ${total_monto_venta:,.0f}
3. Diferencia: {total_kg - total_kg_venta:,.0f} kg

PROBLEMA POTENCIAL:
- Estamos comparando PSP (materia prima) con PTT (producto terminado)
- 1 kg de frambuesa comprada NO es igual a 1 kg de frambuesa vendida
- Hay procesamiento, merma real, etc.

VERIFICAR:
- ¿Las compras son todas de PSP (materia prima)?
- ¿Las ventas son todas de PTT (producto terminado)?
- ¿Hay productos clasificados incorrectamente?
""")
