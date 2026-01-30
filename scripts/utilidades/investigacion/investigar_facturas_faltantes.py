"""
Investigar por qué ciertas facturas de ventas no aparecen en el análisis
Casos específicos: FAC 002597, FCXE 000002, FCXE 000007
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("INVESTIGACIÓN: FACTURAS DE VENTAS FALTANTES")
print("="*140)
print()

# Investigar facturas específicas
facturas_investigar = ['FAC 002597', 'FCXE 000002', 'FCXE 000007', 'FCXE 000006']

for nombre_factura in facturas_investigar:
    print(f"\n{'='*140}")
    print(f"📋 FACTURA: {nombre_factura}")
    print("="*140)
    
    # Buscar la factura
    facturas = odoo.search_read(
        'account.move',
        [['name', '=', nombre_factura]],
        ['id', 'name', 'move_type', 'state', 'payment_state', 'journal_id', 'date', 
         'partner_id', 'amount_total', 'currency_id', 'invoice_line_ids'],
        limit=1
    )
    
    if not facturas:
        print(f"❌ No encontrada: {nombre_factura}")
        continue
    
    factura = facturas[0]
    
    print(f"\n📄 DATOS DE LA FACTURA:")
    print(f"  ID: {factura['id']}")
    print(f"  Nombre: {factura['name']}")
    print(f"  Tipo (move_type): {factura.get('move_type', 'N/A')}")
    print(f"  Estado: {factura.get('state', 'N/A')}")
    print(f"  Estado Pago: {factura.get('payment_state', 'N/A')}")
    print(f"  Diario: {factura.get('journal_id', [None, 'N/A'])[1]}")
    print(f"  Fecha: {factura.get('date', 'N/A')}")
    print(f"  Cliente: {factura.get('partner_id', [None, 'N/A'])[1]}")
    print(f"  Total: {factura.get('amount_total', 0):,.2f} {factura.get('currency_id', [None, 'N/A'])[1]}")
    
    # Obtener líneas
    line_ids = factura.get('invoice_line_ids', [])
    if line_ids:
        print(f"\n📦 LÍNEAS DE LA FACTURA ({len(line_ids)} líneas):")
        
        lineas = odoo.search_read(
            'account.move.line',
            [['id', 'in', line_ids]],
            ['id', 'product_id', 'name', 'quantity', 'price_unit', 'price_total',
             'account_id', 'display_type', 'debit', 'credit', 'balance'],
            limit=50
        )
        
        for i, linea in enumerate(lineas, 1):
            producto = linea.get('product_id', [None, 'N/A'])[1] if linea.get('product_id') else linea.get('name', 'N/A')
            cuenta = linea.get('account_id', [None, 'N/A'])[1] if linea.get('account_id') else 'N/A'
            display_type = linea.get('display_type', 'N/A')
            
            print(f"\n  Línea {i}:")
            print(f"    Producto: {producto[:80]}")
            print(f"    Cantidad: {linea.get('quantity', 0):,.2f}")
            print(f"    Precio Unit: ${linea.get('price_unit', 0):,.2f}")
            print(f"    Total: ${linea.get('price_total', 0):,.2f}")
            print(f"    Cuenta: {cuenta}")
            print(f"    Display Type: {display_type}")
            print(f"    Débito: ${linea.get('debit', 0):,.2f}")
            print(f"    Crédito: ${linea.get('credit', 0):,.2f}")
            print(f"    Balance: ${linea.get('balance', 0):,.2f}")
    
    # Verificar por qué no pasa los filtros actuales
    print(f"\n🔍 VERIFICACIÓN DE FILTROS:")
    
    # Filtro 1: Diario
    diario = factura.get('journal_id', [None, ''])[1]
    if diario == 'Facturas de Cliente':
        print(f"  ✅ Diario 'Facturas de Cliente': Sí")
    else:
        print(f"  ❌ Diario 'Facturas de Cliente': No (es '{diario}')")
    
    # Filtro 2: move_type
    move_type = factura.get('move_type', '')
    if move_type == 'out_invoice':
        print(f"  ✅ move_type='out_invoice': Sí")
    else:
        print(f"  ❌ move_type='out_invoice': No (es '{move_type}')")
    
    # Filtro 3: state
    state = factura.get('state', '')
    if state == 'posted':
        print(f"  ✅ state='posted': Sí")
    else:
        print(f"  ❌ state='posted': No (es '{state}')")
    
    # Filtro 4: payment_state
    payment_state = factura.get('payment_state', '')
    if payment_state != 'reversed':
        print(f"  ✅ payment_state != 'reversed': Sí (es '{payment_state}')")
    else:
        print(f"  ❌ payment_state != 'reversed': No (es reversed)")
    
    # Filtro 5: Cuenta de líneas
    if lineas:
        cuentas_usadas = set([l.get('account_id', [None, ''])[1] for l in lineas if l.get('account_id')])
        cuentas_excluidas = {'41010202', '43010111', '71010204'}
        
        cuentas_problema = []
        for cuenta in cuentas_usadas:
            codigo = cuenta.split(' ')[0] if ' ' in cuenta else ''
            if codigo in cuentas_excluidas:
                cuentas_problema.append(cuenta)
        
        if cuentas_problema:
            print(f"  ❌ Cuentas excluidas encontradas:")
            for cuenta in cuentas_problema:
                print(f"     - {cuenta}")
        else:
            print(f"  ✅ Cuentas: Ninguna excluida")
        
        # Verificar display_type
        display_types = set([l.get('display_type', 'N/A') for l in lineas])
        if 'product' in display_types:
            print(f"  ✅ Tiene líneas con display_type='product': Sí")
        else:
            print(f"  ⚠️  Display types encontrados: {display_types}")

print("\n" + "="*140)
print("ANÁLISIS ADICIONAL - FACTURAS DE EXPORTACIÓN")
print("="*140)

# Buscar todas las facturas de exportación
print("\n🔍 Buscando facturas con nombre FCXE...")
fcxe_facturas = odoo.search_read(
    'account.move',
    [['name', 'like', 'FCXE']],
    ['id', 'name', 'move_type', 'state', 'date', 'amount_total'],
    limit=20,
    order='date desc'
)

print(f"\n✓ Encontradas {len(fcxe_facturas)} facturas FCXE")
print(f"\n{'Nombre':<20s} | {'Tipo (move_type)':<15s} | {'Estado':<10s} | {'Fecha':<12s} | {'Total':>15s}")
print("-" * 140)

for fac in fcxe_facturas:
    print(f"{fac['name']:<20s} | {fac.get('move_type', 'N/A'):<15s} | {fac.get('state', 'N/A'):<10s} | {fac.get('date', 'N/A'):<12s} | ${fac.get('amount_total', 0):>14,.2f}")

print("\n" + "="*140)
print("ANÁLISIS ADICIONAL - CUENTA 43010111 OTROS INGRESOS")
print("="*140)

# Buscar facturas con líneas en cuenta 43010111
print("\n🔍 Buscando facturas con cuenta 43010111 (Otros Ingresos)...")
lineas_otros_ingresos = odoo.search_read(
    'account.move.line',
    [
        ['account_id.code', '=', '43010111'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['display_type', '=', 'product']
    ],
    ['id', 'move_id', 'product_id', 'quantity', 'price_total', 'date'],
    limit=50,
    order='date desc'
)

print(f"\n✓ Encontradas {len(lineas_otros_ingresos)} líneas con cuenta 43010111")

# Agrupar por factura
from collections import defaultdict
por_factura = defaultdict(lambda: {'lineas': 0, 'kg': 0, 'valor': 0, 'fecha': ''})

for linea in lineas_otros_ingresos:
    move_name = linea.get('move_id', [None, 'N/A'])[1]
    por_factura[move_name]['lineas'] += 1
    por_factura[move_name]['kg'] += linea.get('quantity', 0)
    por_factura[move_name]['valor'] += linea.get('price_total', 0)
    if not por_factura[move_name]['fecha']:
        por_factura[move_name]['fecha'] = linea.get('date', 'N/A')

print(f"\n{'Factura':<20s} | {'Fecha':<12s} | {'Kg':>12s} | {'Valor Total':>18s} | {'Líneas':>8s}")
print("-" * 140)

for factura, datos in sorted(por_factura.items(), key=lambda x: x[1]['valor'], reverse=True):
    print(f"{factura:<20s} | {datos['fecha']:<12s} | {datos['kg']:>12,.2f} | ${datos['valor']:>17,.0f} | {datos['lineas']:>8d}")

total_otros = sum([d['valor'] for d in por_factura.values()])
total_kg_otros = sum([d['kg'] for d in por_factura.values()])

print("-" * 140)
print(f"{'TOTAL':<20s} | {'':<12s} | {total_kg_otros:>12,.2f} | ${total_otros:>17,.0f} | {len(lineas_otros_ingresos):>8d}")

print("\n" + "="*140)
print("✅ INVESTIGACIÓN COMPLETADA")
print("="*140)
print("\nCONCLUSIONES:")
print("1. Verificar move_type de facturas FCXE (pueden no ser 'out_invoice')")
print("2. Verificar si cuenta 43010111 debe incluirse en ventas")
print("3. Cuantificar impacto total de facturas faltantes")
