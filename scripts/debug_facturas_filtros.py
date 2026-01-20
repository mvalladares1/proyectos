"""
Debug facturas - entender duplicados y monedas
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("ANÁLISIS FACTURA FCXE 000281 - TODAS LAS LÍNEAS")
print("="*140)

# Buscar todas las líneas de esta factura
lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.name', '=', 'FCXE 000281'],
        ['move_id.move_type', '=', 'out_invoice']
    ],
    [
        'name', 'product_id', 'quantity', 'price_unit', 'price_subtotal',
        'balance', 'debit', 'credit', 'account_id'
    ],
    limit=100
)

print(f"\nTotal líneas: {len(lineas)}\n")
print(f"{'Producto':<45} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Debit':>15} {'Credit':>15} {'Cuenta':<30}")
print("-" * 160)

for line in lineas:
    prod = line.get('product_id')
    if prod:
        prod_name = prod[1][:45] if isinstance(prod, list) else str(prod)[:45]
    else:
        prod_name = str(line.get('name', ''))[:45]
    
    qty = line.get('quantity', 0)
    unit = line.get('price_unit', 0)
    subtotal = line.get('price_subtotal', 0)
    debit = line.get('debit', 0)
    credit = line.get('credit', 0)
    
    account = line.get('account_id')
    if isinstance(account, (list, tuple)) and len(account) > 1:
        account_name = account[1][:30]
    else:
        account_name = str(account)[:30]
    
    print(f"{prod_name:<45} {qty:>10.2f} {unit:>12,.0f} {subtotal:>15,.0f} {debit:>15,.0f} {credit:>15,.0f} {account_name:<30}")

print("\n" + "="*140)
print("CON FILTRO: product_id != False, quantity > 0, price_subtotal > 0")
print("="*140)

lineas_filtradas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.name', '=', 'FCXE 000281'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['product_id', '!=', False],
        ['quantity', '>', 0],
        ['price_subtotal', '>', 0]
    ],
    [
        'name', 'product_id', 'quantity', 'price_unit', 'price_subtotal', 'debit', 'credit'
    ],
    limit=100
)

print(f"\nTotal líneas FILTRADAS: {len(lineas_filtradas)}\n")
print(f"{'Producto':<45} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Debit':>15} {'Credit':>15}")
print("-" * 140)

for line in lineas_filtradas:
    prod = line.get('product_id')
    prod_name = prod[1][:45] if isinstance(prod, list) else str(prod)[:45]
    
    qty = line.get('quantity', 0)
    unit = line.get('price_unit', 0)
    subtotal = line.get('price_subtotal', 0)
    debit = line.get('debit', 0)
    credit = line.get('credit', 0)
    
    print(f"{prod_name:<45} {qty:>10.2f} {unit:>12,.0f} {subtotal:>15,.0f} {debit:>15,.0f} {credit:>15,.0f}")

print("\n" + "="*140)
print("CONCLUSIÓN")
print("="*140)
print("""
El problema de las líneas duplicadas:
- Odoo crea múltiples líneas contables por cada producto
- Una para el producto (credit > 0)
- Una para la contrapartida (debit > 0)
- Líneas de impuestos, etc.

SOLUCIÓN:
Filtrar por credit > 0 en VENTAS (out_invoice) 
Filtrar por debit > 0 en COMPRAS (in_invoice)

Esto asegura que solo contemos la línea del producto, no las contrapartidas.
""")
