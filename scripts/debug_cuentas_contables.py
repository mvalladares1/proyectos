"""
Analizar cuentas contables para saber cuáles usar
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("ANÁLISIS DE CUENTAS CONTABLES")
print("="*140)

# Varias facturas de venta
facturas_venta = ['FCXE 000281', 'FAC 000258', 'FCXE 000282']

for factura in facturas_venta:
    lineas = odoo.search_read(
        'account.move.line',
        [
            ['move_id.name', '=', factura],
            ['move_id.move_type', '=', 'out_invoice'],
            ['product_id', '!=', False],
            ['quantity', '>', 0]
        ],
        ['product_id', 'quantity', 'price_unit', 'price_subtotal', 'credit', 'account_id'],
        limit=10
    )
    
    print(f"\nFactura: {factura}")
    print(f"{'Cuenta':<40} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Credit':>15}")
    print("-" * 110)
    
    for line in lineas:
        account = line.get('account_id')
        if isinstance(account, (list, tuple)) and len(account) > 1:
            account_name = account[1][:40]
            account_code = account_name.split()[0] if account_name else ''
        else:
            account_name = str(account)[:40]
            account_code = ''
        
        qty = line.get('quantity', 0)
        unit = line.get('price_unit', 0)
        subtotal = line.get('price_subtotal', 0)
        credit = line.get('credit', 0)
        
        print(f"{account_name:<40} {qty:>10.2f} {unit:>12,.0f} {subtotal:>15,.0f} {credit:>15,.0f}")

print("\n" + "="*140)
print("FACTURAS DE COMPRA")
print("="*140)

facturas_compra = ['FAC 000055', 'FAC 000524', 'FAC 000066']

for factura in facturas_compra:
    lineas = odoo.search_read(
        'account.move.line',
        [
            ['move_id.name', '=', factura],
            ['move_id.move_type', '=', 'in_invoice'],
            ['product_id', '!=', False],
            ['quantity', '>', 0]
        ],
        ['product_id', 'quantity', 'price_unit', 'price_subtotal', 'debit', 'account_id'],
        limit=10
    )
    
    print(f"\nFactura: {factura}")
    print(f"{'Cuenta':<40} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Debit':>15}")
    print("-" * 110)
    
    for line in lineas:
        account = line.get('account_id')
        if isinstance(account, (list, tuple)) and len(account) > 1:
            account_name = account[1][:40]
        else:
            account_name = str(account)[:40]
        
        qty = line.get('quantity', 0)
        unit = line.get('price_unit', 0)
        subtotal = line.get('price_subtotal', 0)
        debit = line.get('debit', 0)
        
        print(f"{account_name:<40} {qty:>10.2f} {unit:>12,.0f} {subtotal:>15,.0f} {debit:>15,.0f}")

print("\n" + "="*140)
print("PATRÓN DETECTADO")
print("="*140)
print("""
VENTAS (out_invoice):
- Cuenta 41xxxxx (INGRESOS) -> credit > 0 -> USAR ESTA
- Cuenta 11xxxxx (EXISTENCIAS) -> credit > 0 -> IGNORAR

COMPRAS (in_invoice):
- Cuenta 11xxxxx (EXISTENCIAS) -> debit > 0 -> USAR ESTA  
- Cuenta 21xxxxx (PROVEEDORES) -> credit > 0 -> IGNORAR

SOLUCIÓN FINAL:
Ventas: credit > 0 AND account_id.code LIKE '41%'
Compras: debit > 0 AND account_id.code LIKE '11%'
""")
