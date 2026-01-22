"""
DEBUG: Analizar cuentas contables usadas en compras y ventas
Para identificar cuáles líneas debemos considerar
"""
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuración
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("DEBUG: CUENTAS CONTABLES EN COMPRAS Y VENTAS")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# Analizar una factura de proveedor de ejemplo
print("\n🔍 EJEMPLO DE FACTURA DE PROVEEDOR:")
facturas_proveedor = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'in_invoice'],
        ['state', '=', 'posted'],
        ['journal_id.name', '=', 'Facturas de Proveedores']
    ],
    ['name', 'date', 'amount_total'],
    limit=1
)

if facturas_proveedor:
    factura = facturas_proveedor[0]
    print(f"\nFactura: {factura['name']} - ${factura.get('amount_total', 0):,.2f}")
    
    # Obtener todas las líneas de esta factura
    lineas = odoo.search_read(
        'account.move.line',
        [['move_id', '=', factura['id']]],
        ['name', 'account_id', 'product_id', 'quantity', 'debit', 'credit'],
        limit=100
    )
    
    print(f"\nLíneas contables ({len(lineas)}):")
    print(f"{'Cuenta':<60} {'Producto':<30} {'Cantidad':>12} {'Débito':>15} {'Crédito':>15}")
    print("-" * 140)
    
    for linea in lineas:
        account = linea.get('account_id', [None, 'Sin cuenta'])
        account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
        
        producto = linea.get('product_id', [None, ''])
        prod_name = producto[1] if isinstance(producto, (list, tuple)) else ''
        
        print(f"{account_name:<60} {prod_name[:28]:<30} {linea.get('quantity', 0):>12,.2f} ${linea.get('debit', 0):>14,.2f} ${linea.get('credit', 0):>14,.2f}")

# Analizar todas las cuentas usadas en compras
print("\n\n" + "=" * 140)
print("ANÁLISIS DE CUENTAS EN COMPRAS (Con Producto)")
print("=" * 140)

lineas_compras = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Proveedores'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['product_id.type', '!=', 'service'],
        ['date', '>=', '2024-01-01'],
        ['date', '<=', '2024-12-31']
    ],
    ['account_id', 'debit', 'credit', 'quantity'],
    limit=10000
)

# Agrupar por cuenta
cuentas_compras = {}
for linea in lineas_compras:
    account = linea.get('account_id', [None, 'Sin cuenta'])
    account_name = account[1] if isinstance(account, (list, tuple)) else 'Sin cuenta'
    
    if account_name not in cuentas_compras:
        cuentas_compras[account_name] = {
            'lineas': 0,
            'debito': 0,
            'credito': 0,
            'cantidad': 0
        }
    
    cuentas_compras[account_name]['lineas'] += 1
    cuentas_compras[account_name]['debito'] += linea.get('debit', 0)
    cuentas_compras[account_name]['credito'] += linea.get('credit', 0)
    cuentas_compras[account_name]['cantidad'] += linea.get('quantity', 0)

print(f"\n{'Cuenta':<65} {'Líneas':>8} {'Total Débito':>18} {'Total Crédito':>18} {'Cantidad (kg)':>15}")
print("-" * 140)

for cuenta, datos in sorted(cuentas_compras.items(), key=lambda x: -x[1]['debito']):
    print(f"{cuenta:<65} {datos['lineas']:>8,} ${datos['debito']:>17,.2f} ${datos['credito']:>17,.2f} {datos['cantidad']:>15,.2f}")

# Analizar una factura de cliente de ejemplo
print("\n\n" + "=" * 140)
print("EJEMPLO DE FACTURA DE CLIENTE:")
print("=" * 140)

facturas_cliente = odoo.search_read(
    'account.move',
    [
        ['move_type', '=', 'out_invoice'],
        ['state', '=', 'posted'],
        ['journal_id.name', '=', 'Facturas de Cliente']
    ],
    ['name', 'date', 'amount_total'],
    limit=1
)

if facturas_cliente:
    factura = facturas_cliente[0]
    print(f"\nFactura: {factura['name']} - ${factura.get('amount_total', 0):,.2f}")
    
    # Obtener todas las líneas de esta factura
    lineas = odoo.search_read(
        'account.move.line',
        [['move_id', '=', factura['id']]],
        ['name', 'account_id', 'product_id', 'quantity', 'debit', 'credit'],
        limit=100
    )
    
    print(f"\nLíneas contables ({len(lineas)}):")
    print(f"{'Cuenta':<60} {'Producto':<30} {'Cantidad':>12} {'Débito':>15} {'Crédito':>15}")
    print("-" * 140)
    
    for linea in lineas:
        account = linea.get('account_id', [None, 'Sin cuenta'])
        account_name = account[1] if isinstance(account, (list, tuple)) else str(account)
        
        producto = linea.get('product_id', [None, ''])
        prod_name = producto[1] if isinstance(producto, (list, tuple)) else ''
        
        print(f"{account_name:<60} {prod_name[:28]:<30} {linea.get('quantity', 0):>12,.2f} ${linea.get('debit', 0):>14,.2f} ${linea.get('credit', 0):>14,.2f}")

# Analizar todas las cuentas usadas en ventas
print("\n\n" + "=" * 140)
print("ANÁLISIS DE CUENTAS EN VENTAS (Con Producto)")
print("=" * 140)

lineas_ventas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['product_id.type', '!=', 'service'],
        ['date', '>=', '2024-01-01'],
        ['date', '<=', '2024-12-31']
    ],
    ['account_id', 'debit', 'credit', 'quantity'],
    limit=10000
)

# Agrupar por cuenta
cuentas_ventas = {}
for linea in lineas_ventas:
    account = linea.get('account_id', [None, 'Sin cuenta'])
    account_name = account[1] if isinstance(account, (list, tuple)) else 'Sin cuenta'
    
    if account_name not in cuentas_ventas:
        cuentas_ventas[account_name] = {
            'lineas': 0,
            'debito': 0,
            'credito': 0,
            'cantidad': 0
        }
    
    cuentas_ventas[account_name]['lineas'] += 1
    cuentas_ventas[account_name]['debito'] += linea.get('debit', 0)
    cuentas_ventas[account_name]['credito'] += linea.get('credit', 0)
    cuentas_ventas[account_name]['cantidad'] += linea.get('quantity', 0)

print(f"\n{'Cuenta':<65} {'Líneas':>8} {'Total Débito':>18} {'Total Crédito':>18} {'Cantidad (kg)':>15}")
print("-" * 140)

for cuenta, datos in sorted(cuentas_ventas.items(), key=lambda x: -x[1]['credito']):
    print(f"{cuenta:<65} {datos['lineas']:>8,} ${datos['debito']:>17,.2f} ${datos['credito']:>17,.2f} {datos['cantidad']:>15,.2f}")

print("\n" + "=" * 140)
print("DEBUG COMPLETADO")
print("=" * 140)
