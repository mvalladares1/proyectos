"""
Verificar que facturas FCXE 000002 y 000007 están en el nuevo análisis
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

odoo = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

print("="*100)
print("VERIFICACIÓN: Facturas FCXE en análisis actualizado")
print("="*100)

# Buscar FCXE 000002 y 000007
facturas_buscar = ['FCXE 000002', 'FCXE 000007']

for factura_nombre in facturas_buscar:
    print(f"\n🔍 Buscando: {factura_nombre}")
    
    # Buscar el move
    moves = odoo.search_read(
        'account.move',
        [['name', '=', factura_nombre]],
        ['id', 'name', 'date', 'state', 'payment_state', 'journal_id', 'move_type'],
        limit=1
    )
    
    if not moves:
        print(f"   ❌ No encontrada en account.move")
        continue
    
    move = moves[0]
    print(f"   ✓ Encontrada: ID {move['id']}")
    print(f"     - Fecha: {move.get('date')}")
    print(f"     - Estado: {move.get('state')}")
    print(f"     - Payment State: {move.get('payment_state')}")
    print(f"     - Diario: {move.get('journal_id', [None, 'N/A'])[1]}")
    print(f"     - Tipo: {move.get('move_type')}")
    
    # Buscar las líneas
    lineas = odoo.search_read(
        'account.move.line',
        [
            ['move_id', '=', move['id']],
            ['display_type', '=', 'product']
        ],
        ['id', 'name', 'product_id', 'quantity', 'credit', 'debit', 'account_id'],
        limit=10
    )
    
    print(f"\n   📋 Líneas de producto: {len(lineas)}")
    for linea in lineas:
        producto = linea.get('product_id', [None, 'N/A'])[1] if linea.get('product_id') else linea.get('name', 'Texto libre')
        cantidad = linea.get('quantity', 0)
        cuenta = linea.get('account_id', [None, 'N/A'])[1]
        valor = linea.get('credit', 0) - linea.get('debit', 0)
        
        print(f"     - {producto[:50]:50s} | {cantidad:8.2f} kg | ${valor:12,.0f} | {cuenta}")

# Verificar totales en ambas cuentas
print("\n" + "="*100)
print("ANÁLISIS DE CUENTA 43010111 (OTROS INGRESOS)")
print("="*100)

lineas_otros = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['account_id.code', '=', '43010111'],
        ['display_type', '=', 'product']
    ],
    ['id', 'move_id', 'name', 'product_id', 'quantity', 'credit', 'debit', 'date'],
    limit=50
)

print(f"\n✓ Total líneas en cuenta 43010111: {len(lineas_otros)}")
print(f"✓ Valor total: ${sum([l.get('credit', 0) - l.get('debit', 0) for l in lineas_otros]):,.0f}")

print("\nTop 10 líneas por valor:")
lineas_sorted = sorted(lineas_otros, key=lambda x: x.get('credit', 0) - x.get('debit', 0), reverse=True)[:10]

for linea in lineas_sorted:
    factura = linea.get('move_id', [None, 'N/A'])[1]
    descripcion = linea.get('name', 'N/A')
    producto = linea.get('product_id', [None, 'N/A'])[1] if linea.get('product_id') else 'Sin producto'
    valor = linea.get('credit', 0) - linea.get('debit', 0)
    fecha = linea.get('date', 'N/A')
    
    print(f"{factura:15s} | {fecha:10s} | ${valor:12,.0f} | {descripcion[:40]}")

print("\n" + "="*100)
print("✅ VERIFICACIÓN COMPLETADA")
print("="*100)
