"""
Debug: Validar datos de stock teórico directamente desde Odoo
Compara con los filtros correctos usados en exportar_stock_teorico_excel.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Configurar credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

FECHA_DESDE = "2022-01-01"
FECHA_HASTA = "2026-01-22"

print("=" * 100)
print("DEBUG: STOCK TEÓRICO - VALIDACIÓN DE DATOS DESDE ODOO")
print("=" * 100)
print(f"Período: {FECHA_DESDE} hasta {FECHA_HASTA}")
print("=" * 100)

# Conectar a Odoo
odoo = OdooClient(username=USERNAME, password=PASSWORD)

# Obtener datos directamente de Odoo (mismo método que el script de exportación)
print("\n📦 DATOS DIRECTOS DE ODOO (con filtros correctos):")
print("-" * 100)

# COMPRAS - exactamente como en exportar_stock_teorico_excel.py
compras_lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['product_id.type', '!=', 'service'],
        ['account_id.code', 'in', ['21020107', '21020106']],
        ['debit', '>', 0],
        ['date', '>=', FECHA_DESDE],
        ['date', '<=', FECHA_HASTA]
    ],
    ['product_id', 'quantity', 'debit'],
    limit=100000
)

total_kg_compras_directo = sum([l.get('quantity', 0) for l in compras_lineas])
total_monto_compras_directo = sum([l.get('debit', 0) for l in compras_lineas])

print(f"\nCompras (directo de Odoo):")
print(f"  Líneas:   {len(compras_lineas)}")
print(f"  Kg:       {total_kg_compras_directo:>15,.2f} kg")
print(f"  Monto:    ${total_monto_compras_directo:>15,.0f}")
print(f"  $/kg:     ${total_monto_compras_directo/total_kg_compras_directo:,.2f}" if total_kg_compras_directo > 0 else "  $/kg:     N/A")

# VENTAS - exactamente como en exportar_stock_teorico_excel.py
ventas_lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['product_id.type', '!=', 'service'],
        ['account_id.code', '=', '41010101'],
        ['credit', '>', 0],
        ['date', '>=', FECHA_DESDE],
        ['date', '<=', FECHA_HASTA]
    ],
    ['product_id', 'quantity', 'credit'],
    limit=100000
)

total_kg_ventas_directo = sum([l.get('quantity', 0) for l in ventas_lineas])
total_monto_ventas_directo = sum([l.get('credit', 0) for l in ventas_lineas])

print(f"\nVentas (directo de Odoo):")
print(f"  Líneas:   {len(ventas_lineas)}")
print(f"  Kg:       {total_kg_ventas_directo:>15,.2f} kg")
print(f"  Monto:    ${total_monto_ventas_directo:>15,.0f}")
print(f"  $/kg:     ${total_monto_ventas_directo/total_kg_ventas_directo:,.2f}" if total_kg_ventas_directo > 0 else "  $/kg:     N/A")

# Merma
merma_directo = total_kg_compras_directo - total_kg_ventas_directo
merma_pct_directo = (merma_directo / total_kg_compras_directo * 100) if total_kg_compras_directo > 0 else 0

print(f"\nMerma (calculada):")
print(f"  Kg:       {merma_directo:>15,.2f} kg")
print(f"  %:        {merma_pct_directo:>7.2f}%")

print("\n" + "=" * 100)
print("RESULTADO:")
print("=" * 100)
print(f"\n✅ Compras:  {total_kg_compras_directo:,.0f} kg por ${total_monto_compras_directo:,.0f}")
print(f"✅ Ventas:   {total_kg_ventas_directo:,.0f} kg por ${total_monto_ventas_directo:,.0f}")
print(f"✅ Merma:    {merma_directo:,.0f} kg ({merma_pct_directo:.2f}%)")
print("\nEstos son los números correctos que deberían aparecer en Stock Teórico Anual")
print("=" * 100)
