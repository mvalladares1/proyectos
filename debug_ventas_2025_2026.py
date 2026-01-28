"""
DEBUG: Encontrar ventas de productos en 2025 y 2026
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 140)
print("DEBUG: BÚSQUEDA AMPLIA DE VENTAS 2025-2026")
print("=" * 140)

# Búsqueda MUY AMPLIA: todas las líneas de facturas de cliente con productos
print("\n🔍 Paso 1: Búsqueda SIN filtros de cuenta...")

lineas_todas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['date', '>=', '2025-01-01'],
        ['date', '<=', '2026-01-31']
    ],
    ['product_id', 'quantity', 'debit', 'credit', 'account_id', 'date', 'move_id'],
    limit=5000
)

print(f"✓ Total líneas encontradas: {len(lineas_todas):,}")

if not lineas_todas:
    print("\n❌ NO SE ENCONTRARON LÍNEAS. Probando sin filtro de categoría...")
    
    lineas_todas = odoo.search_read(
        'account.move.line',
        [
            ['move_id.move_type', '=', 'out_invoice'],
            ['move_id.state', '=', 'posted'],
            ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
            ['product_id', '!=', False],
            ['date', '>=', '2025-01-01'],
            ['date', '<=', '2026-01-31']
        ],
        ['product_id', 'quantity', 'debit', 'credit', 'account_id', 'date', 'move_id'],
        limit=5000
    )
    
    print(f"✓ Total líneas sin filtro categoría: {len(lineas_todas):,}")

# Agrupar por cuenta
print("\n📊 Paso 2: Análisis por cuenta contable...")
cuentas_stats = {}

for linea in lineas_todas:
    account_info = linea.get('account_id')
    if account_info:
        if isinstance(account_info, (list, tuple)) and len(account_info) >= 2:
            account_code = str(account_info[1])
        else:
            account_code = str(account_info)
        
        if account_code not in cuentas_stats:
            cuentas_stats[account_code] = {
                'lineas': 0,
                'con_cantidad': 0,
                'debito_total': 0,
                'credito_total': 0,
                'cantidad_total': 0
            }
        
        cantidad = linea.get('quantity', 0)
        debito = linea.get('debit', 0)
        credito = linea.get('credit', 0)
        
        cuentas_stats[account_code]['lineas'] += 1
        if cantidad != 0:
            cuentas_stats[account_code]['con_cantidad'] += 1
        cuentas_stats[account_code]['debito_total'] += debito
        cuentas_stats[account_code]['credito_total'] += credito
        cuentas_stats[account_code]['cantidad_total'] += abs(cantidad)

print("\n" + "=" * 140)
print(f"{'Cuenta':<60} {'Líneas':>10} {'Con kg':>10} {'Débito ($)':>18} {'Crédito ($)':>18} {'Total kg':>15}")
print("-" * 140)

for cuenta, stats in sorted(cuentas_stats.items(), key=lambda x: -x[1]['lineas']):
    print(f"{cuenta:<60} {stats['lineas']:>10,} {stats['con_cantidad']:>10,} "
          f"${stats['debito_total']:>16,.2f} ${stats['credito_total']:>16,.2f} {stats['cantidad_total']:>14,.2f}")

# Análisis más detallado de las cuentas con más movimiento
print("\n" + "=" * 140)
print("🔎 Paso 3: Muestras de líneas por cuenta (primeras 3 líneas de cada cuenta)")
print("=" * 140)

for cuenta in sorted(cuentas_stats.keys(), key=lambda x: -cuentas_stats[x]['lineas'])[:5]:
    print(f"\n📌 CUENTA: {cuenta}")
    print("-" * 140)
    
    lineas_cuenta = [l for l in lineas_todas if l.get('account_id') and 
                     (l['account_id'][1] if isinstance(l['account_id'], (list, tuple)) else str(l['account_id'])) == cuenta][:3]
    
    for i, linea in enumerate(lineas_cuenta, 1):
        prod_info = linea.get('product_id', [None, 'N/A'])
        prod_name = prod_info[1] if isinstance(prod_info, (list, tuple)) and len(prod_info) >= 2 else 'N/A'
        
        move_info = linea.get('move_id', [None, 'N/A'])
        move_name = move_info[1] if isinstance(move_info, (list, tuple)) and len(move_info) >= 2 else 'N/A'
        
        print(f"   {i}. {prod_name[:50]:<50} | Factura: {move_name:<20} | Cant: {linea.get('quantity', 0):>10,.2f} kg | "
              f"Déb: ${linea.get('debit', 0):>12,.2f} | Créd: ${linea.get('credit', 0):>12,.2f}")

print("\n" + "=" * 140)
print("CONCLUSIÓN:")
print("=" * 140)

# Identificar la cuenta de costo de venta
cuenta_costo = None
for cuenta, stats in cuentas_stats.items():
    # Costo de venta típicamente tiene DÉBITO (no crédito) y tiene cantidades
    if stats['debito_total'] > stats['credito_total'] and stats['con_cantidad'] > 0:
        if 'COSTO' in cuenta.upper() or '5101' in cuenta:
            cuenta_costo = cuenta
            break

if cuenta_costo:
    print(f"✅ PROBABLE CUENTA DE COSTO DE VENTA: {cuenta_costo}")
    print(f"   - Líneas: {cuentas_stats[cuenta_costo]['lineas']:,}")
    print(f"   - Total kg: {cuentas_stats[cuenta_costo]['cantidad_total']:,.2f}")
    print(f"   - Total débito: ${cuentas_stats[cuenta_costo]['debito_total']:,.2f}")
else:
    print("⚠️ NO SE IDENTIFICÓ CUENTA DE COSTO DE VENTA AUTOMÁTICAMENTE")
    print("   Revisar manualmente las cuentas listadas arriba")

print("\n" + "=" * 140)
