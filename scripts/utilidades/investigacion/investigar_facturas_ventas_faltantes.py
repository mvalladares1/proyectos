"""
Investigar facturas de ventas que no aparecen en el análisis
Identificar características comunes para incluirlas
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*140)
print("INVESTIGACIÓN DE FACTURAS DE VENTAS FALTANTES")
print("="*140)
print()

# Facturas a investigar
facturas_investigar = [
    {'nombre': 'Factura 140', 'fecha': '2024-11', 'kilos': 2006, 'producto': 'Frambuesa'},
    {'nombre': 'Factura 2597', 'fecha': None, 'kilos': 197.5, 'producto': 'Frambuesa'},
    {'nombre': 'Factura 2', 'fecha': '2023-03', 'kilos': 9600, 'producto': 'Frambuesa'},
    {'nombre': 'Factura 7', 'fecha': '2023-07', 'kilos': 9600, 'producto': 'Frambuesa'},
    {'nombre': 'Factura 6', 'fecha': '2023-07', 'kilos': 18000, 'producto': 'Frambuesa'},
]

print("🔍 Buscando facturas por número...")
print()

for factura_info in facturas_investigar:
    print("-" * 140)
    print(f"Buscando: {factura_info['nombre']} ({factura_info.get('fecha', 'N/A')})")
    
    # Extraer número de factura
    numero = factura_info['nombre'].split()[-1]
    
    # Buscar factura en account.move
    facturas = odoo.search_read(
        'account.move',
        [
            '|', ['name', 'ilike', numero],
            ['ref', 'ilike', numero]
        ],
        ['id', 'name', 'ref', 'move_type', 'state', 'payment_state', 'journal_id', 'partner_id', 'invoice_date', 'amount_total'],
        limit=10
    )
    
    if facturas:
        for fac in facturas:
            print(f"\n  ✓ Encontrada: {fac.get('name')}")
            print(f"    - ID: {fac['id']}")
            print(f"    - Referencia: {fac.get('ref', 'N/A')}")
            print(f"    - Tipo: {fac.get('move_type', 'N/A')}")
            print(f"    - Estado: {fac.get('state', 'N/A')}")
            print(f"    - Estado Pago: {fac.get('payment_state', 'N/A')}")
            print(f"    - Diario: {fac.get('journal_id', [None, 'N/A'])[1] if fac.get('journal_id') else 'N/A'}")
            print(f"    - Cliente: {fac.get('partner_id', [None, 'N/A'])[1] if fac.get('partner_id') else 'N/A'}")
            print(f"    - Fecha: {fac.get('invoice_date', 'N/A')}")
            print(f"    - Total: ${fac.get('amount_total', 0):,.2f}")
            
            # Obtener líneas de la factura
            lineas = odoo.search_read(
                'account.move.line',
                [
                    ['move_id', '=', fac['id']],
                    ['display_type', '=', 'product']
                ],
                ['id', 'product_id', 'quantity', 'price_unit', 'price_subtotal', 'account_id'],
                limit=20
            )
            
            if lineas:
                print(f"\n    Líneas de producto ({len(lineas)}):")
                for linea in lineas:
                    prod_name = linea.get('product_id', [None, 'N/A'])[1] if linea.get('product_id') else 'Sin producto'
                    qty = linea.get('quantity', 0)
                    precio = linea.get('price_unit', 0)
                    subtotal = linea.get('price_subtotal', 0)
                    cuenta = linea.get('account_id', [None, 'N/A'])[1] if linea.get('account_id') else 'N/A'
                    
                    print(f"      - {prod_name[:50]:50s} | {qty:10,.2f} kg | ${precio:12,.2f}/kg | ${subtotal:15,.2f} | {cuenta[:40]}")
    else:
        print(f"  ⚠️ NO encontrada con búsqueda básica")
        
        # Búsqueda más amplia
        print(f"\n  🔍 Búsqueda ampliada...")
        facturas_amplia = odoo.search_read(
            'account.move',
            [
                ['move_type', 'in', ['out_invoice', 'out_refund']],
                ['state', '=', 'posted']
            ],
            ['id', 'name', 'ref', 'journal_id', 'invoice_date', 'amount_total'],
            limit=5000,
            order='invoice_date desc'
        )
        
        # Filtrar por fecha aproximada si existe
        if factura_info.get('fecha'):
            año_mes = factura_info['fecha']
            facturas_fecha = [f for f in facturas_amplia if f.get('invoice_date', '').startswith(año_mes)]
            print(f"    Facturas en {año_mes}: {len(facturas_fecha)}")
            
            # Mostrar primeras 5
            for fac in facturas_fecha[:5]:
                print(f"      - {fac.get('name'):20s} | {fac.get('journal_id', [None, 'N/A'])[1] if fac.get('journal_id') else 'N/A':30s} | ${fac.get('amount_total', 0):12,.2f}")

print("\n" + "="*140)
print("ANÁLISIS DE DIARIOS DE VENTAS")
print("="*140)
print()

# Obtener todos los diarios con facturas de cliente
diarios = odoo.search_read(
    'account.move',
    [
        ['move_type', 'in', ['out_invoice', 'out_refund']],
        ['state', '=', 'posted']
    ],
    ['journal_id'],
    limit=10000
)

# Contar por diario
from collections import defaultdict
diarios_count = defaultdict(int)
for mov in diarios:
    journal_name = mov.get('journal_id', [None, 'N/A'])[1] if mov.get('journal_id') else 'N/A'
    diarios_count[journal_name] += 1

print("Distribución de facturas de cliente por diario:")
print(f"{'Diario':<50s} | {'Cantidad':>10s}")
print("-" * 140)
for diario, count in sorted(diarios_count.items(), key=lambda x: x[1], reverse=True):
    print(f"{diario[:50]:50s} | {count:10,d}")

print("\n" + "="*140)
print("RECOMENDACIÓN")
print("="*140)
print()
print("Basado en el análisis, probablemente estas facturas están en un diario diferente a 'Facturas de Cliente'")
print("Revisar diarios como: 'Ventas', 'Facturas de Ventas', 'Facturas Exportación', etc.")
print()
print("Para incluirlas en el análisis, agregar condición OR con estos diarios adicionales")
