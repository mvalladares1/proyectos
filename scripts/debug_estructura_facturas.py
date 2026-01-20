"""
Debug COMPLETO para entender estructura de facturas en Odoo.
Revisa:
- Líneas duplicadas (exclude_from_invoice_tab)
- Monedas (USD vs CLP)
- Tipos de cambio
- Campos correctos para usar
"""

import sys
sys.path.append('.')
import os
from dotenv import load_dotenv
import xmlrpc.client

load_dotenv()

# Conectar a Odoo
url = os.getenv('ODOO_URL')
db = os.getenv('ODOO_DB')
username = os.getenv('ODOO_USERNAME')
password = os.getenv('ODOO_PASSWORD')

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

def search_read(model, domain, fields, limit=1000):
    return models.execute_kw(db, uid, password, model, 'search_read', 
                             [domain], {'fields': fields, 'limit': limit})

print("="*140)
print("ANÁLISIS DE FACTURA FCXE 000281 (Ejemplo de venta)")
print("="*140)

# Buscar la factura completa
factura = search_read(
    'account.move',
    [['name', '=', 'FCXE 000281']],
    ['id', 'name', 'move_type', 'currency_id', 'company_currency_id', 'date', 'invoice_date'],
    limit=1
)

if factura:
    fac = factura[0]
    print(f"\nFactura: {fac['name']}")
    print(f"Tipo: {fac['move_type']}")
    print(f"Fecha: {fac.get('invoice_date') or fac.get('date')}")
    
    currency = fac.get('currency_id')
    currency_name = currency[1] if isinstance(currency, list) else str(currency)
    print(f"Moneda factura: {currency_name}")
    
    company_currency = fac.get('company_currency_id')
    company_currency_name = company_currency[1] if isinstance(company_currency, list) else str(company_currency)
    print(f"Moneda compañía: {company_currency_name}")
    
    # Obtener TODAS las líneas
    lineas = search_read(
        'account.move.line',
        [['move_id', '=', fac['id']]],
        [
            'name', 'product_id', 'quantity', 'price_unit', 'price_subtotal',
            'balance', 'amount_currency', 'currency_id',
            'exclude_from_invoice_tab', 'display_type', 'account_id'
        ],
        limit=100
    )
    
    print(f"\nTotal líneas en factura: {len(lineas)}\n")
    print(f"{'Producto/Descripción':<50} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Balance':>15} {'Amt Curr':>15} {'Exclude':>8} {'Display':>10}")
    print("-" * 160)
    
    for line in lineas:
        nombre = str(line.get('name', ''))[:50]
        
        prod = line.get('product_id')
        if prod:
            prod_name = prod[1][:50] if isinstance(prod, list) else str(prod)[:50]
        else:
            prod_name = nombre
        
        qty = line.get('quantity', 0)
        unit = line.get('price_unit', 0)
        subtotal = line.get('price_subtotal', 0)
        balance = line.get('balance', 0)
        amt_curr = line.get('amount_currency', 0)
        exclude = line.get('exclude_from_invoice_tab', False)
        display = str(line.get('display_type') or '-')[:10]
        
        print(f"{prod_name:<50} {qty:>10.2f} {unit:>12,.2f} {subtotal:>15,.2f} {balance:>15,.2f} {amt_curr:>15,.2f} {str(exclude):>8} {display:>10}")

print("\n" + "="*140)
print("ANÁLISIS DE FACTURA FAC 000055 (Ejemplo de compra)")
print("="*140)

factura_compra = search_read(
    'account.move',
    [['name', '=', 'FAC 000055']],
    ['id', 'name', 'move_type', 'currency_id', 'company_currency_id', 'date', 'invoice_date'],
    limit=1
)

if factura_compra:
    fac = factura_compra[0]
    print(f"\nFactura: {fac['name']}")
    print(f"Tipo: {fac['move_type']}")
    print(f"Fecha: {fac.get('invoice_date') or fac.get('date')}")
    
    currency = fac.get('currency_id')
    currency_name = currency[1] if isinstance(currency, list) else str(currency)
    print(f"Moneda factura: {currency_name}")
    
    company_currency = fac.get('company_currency_id')
    company_currency_name = company_currency[1] if isinstance(company_currency, list) else str(company_currency)
    print(f"Moneda compañía: {company_currency_name}")
    
    lineas = search_read(
        'account.move.line',
        [['move_id', '=', fac['id']]],
        [
            'name', 'product_id', 'quantity', 'price_unit', 'price_subtotal',
            'balance', 'amount_currency', 'currency_id',
            'exclude_from_invoice_tab', 'display_type', 'account_id'
        ],
        limit=100
    )
    
    print(f"\nTotal líneas en factura: {len(lineas)}\n")
    print(f"{'Producto/Descripción':<50} {'Qty':>10} {'P.Unit':>12} {'Subtotal':>15} {'Balance':>15} {'Amt Curr':>15} {'Exclude':>8} {'Display':>10}")
    print("-" * 160)
    
    for line in lineas:
        nombre = str(line.get('name', ''))[:50]
        
        prod = line.get('product_id')
        if prod:
            prod_name = prod[1][:50] if isinstance(prod, list) else str(prod)[:50]
        else:
            prod_name = nombre
        
        qty = line.get('quantity', 0)
        unit = line.get('price_unit', 0)
        subtotal = line.get('price_subtotal', 0)
        balance = line.get('balance', 0)
        amt_curr = line.get('amount_currency', 0)
        exclude = line.get('exclude_from_invoice_tab', False)
        display = str(line.get('display_type') or '-')[:10]
        
        print(f"{prod_name:<50} {qty:>10.2f} {unit:>12,.2f} {subtotal:>15,.2f} {balance:>15,.2f} {amt_curr:>15,.2f} {str(exclude):>8} {display:>10}")

print("\n" + "="*140)
print("RESUMEN DE CAMPOS RECOMENDADOS")
print("="*140)
print("""
Para obtener las líneas CORRECTAS de factura:

FILTROS NECESARIOS:
1. ['exclude_from_invoice_tab', '=', False]  -> Solo líneas de factura real, no contabilidad
2. ['quantity', '>', 0]                       -> Cantidad positiva
3. ['price_subtotal', '>', 0]                 -> Monto positivo (excluye ajustes negativos)
4. ['display_type', '=', False]               -> Excluir líneas de sección/nota

CAMPOS PARA MONEDA:
- Si move_id.currency_id != company_currency_id:
    * Usar 'amount_currency' (monto en moneda extranjera)
    * Obtener tipo de cambio del día o usar 'balance' (ya convertido a CLP)
- Si move_id.currency_id == company_currency_id:
    * Usar 'price_subtotal' directamente (ya en CLP)

RECOMENDACIÓN:
Usar 'balance' que siempre está en moneda de la compañía (CLP)
Para cantidad usar 'quantity'
""")
