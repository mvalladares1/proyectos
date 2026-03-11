#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrección adicional: OC12902 precio 3.080 → 3.085
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

PRECIO_ACTUAL = 3080.0
PRECIO_CORRECTO = 3085.0

print("=" * 100)
print("⚠️  CORRECCIÓN PRECIO OC12902: $3,080 → $3,085")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

# Obtener ID de moneda USD
usd_currency = models.execute_kw(db, uid, password, 'res.currency', 'search_read',
    [[['name', '=', 'USD']]],
    {'fields': ['id'], 'limit': 1}
)

if not usd_currency:
    print("❌ No se encontró moneda USD")
    exit(1)

USD_ID = usd_currency[0]['id']
print(f"💵 USD ID: {USD_ID}\n")

# Buscar OC12902
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12902']]],
    {'fields': ['id', 'order_line', 'picking_ids'], 'limit': 1}
)

if not oc:
    print("❌ OC12902 no encontrada")
    exit(1)

oc_id = oc[0]['id']

# PASO 1: Corregir línea de OC
print("PASO 1: Corregir línea de orden de compra")
print("-" * 100)

lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['id', 'product_id', 'price_unit', 'product_qty']}
)

for linea in lineas:
    if abs(linea['price_unit'] - PRECIO_ACTUAL) < 1:
        print(f"\n🔧 Línea ID {linea['id']}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
        print(f"   Precio: ${linea['price_unit']:,.2f} → ${PRECIO_CORRECTO:,.2f}")
        print(f"   Actualizando moneda a USD...")
        
        result = models.execute_kw(
            db, uid, password,
            'purchase.order.line', 'write',
            [[linea['id']], {
                'currency_id': USD_ID,
                'price_unit': PRECIO_CORRECTO
            }]
        )
        
        if result:
            print(f"   ✅ ACTUALIZADO")
        else:
            print(f"   ❌ ERROR")

# PASO 2: Corregir movimientos de stock
print("\n\nPASO 2: Corregir movimientos de stock")
print("-" * 100)

picking_ids = oc[0].get('picking_ids', [])
if picking_ids:
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['id', 'in', picking_ids]]],
        {'fields': ['id', 'name', 'move_ids']}
    )
    
    for picking in pickings:
        print(f"\nAlbarán: {picking['name']}")
        
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': ['id', 'price_unit', 'quantity_done']}
            )
            
            for move in moves:
                if move.get('quantity_done', 0) > 0 and abs(move['price_unit'] - PRECIO_ACTUAL) < 1:
                    print(f"  🔧 Movimiento ID {move['id']}")
                    print(f"     Precio: ${move['price_unit']:,.2f} → ${PRECIO_CORRECTO:,.2f}")
                    
                    result = models.execute_kw(
                        db, uid, password,
                        'stock.move', 'write',
                        [[move['id']], {'price_unit': PRECIO_CORRECTO}]
                    )
                    
                    if result:
                        print(f"     ✅ ACTUALIZADO")

# PASO 3: Corregir capas de valoración
print("\n\nPASO 3: Corregir capas de valoración")
print("-" * 100)

try:
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[
            ['unit_cost', '=', PRECIO_ACTUAL],
            ['description', 'ilike', 'OC12902']
        ]],
        {'fields': ['id', 'product_id', 'quantity', 'unit_cost', 'value', 'description']},
        limit=10
    )
    
    if valuation_layers:
        for vl in valuation_layers:
            nuevo_valor = vl['quantity'] * PRECIO_CORRECTO
            
            print(f"\n🔧 Capa ID {vl['id']}")
            print(f"   Cantidad: {vl['quantity']} kg")
            print(f"   Costo: ${vl['unit_cost']:,.2f} → ${PRECIO_CORRECTO:,.2f}")
            print(f"   Valor: ${vl['value']:,.2f} → ${nuevo_valor:,.2f}")
            
            result = models.execute_kw(
                db, uid, password,
                'stock.valuation.layer', 'write',
                [[vl['id']], {
                    'unit_cost': PRECIO_CORRECTO,
                    'value': nuevo_valor
                }]
            )
            
            if result:
                print(f"   ✅ ACTUALIZADO")
    else:
        print("⚠️ No se encontraron capas con costo $3,080")
except Exception as e:
    print(f"⚠️ Error: {e}")

# Verificar resultado
print("\n" + "=" * 100)
print("VERIFICACIÓN FINAL")
print("=" * 100)

oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['name', 'amount_total', 'currency_id']}
)

if oc_final:
    print(f"\nOC12902:")
    print(f"  Moneda: {oc_final[0]['currency_id'][1]}")
    print(f"  Total: ${oc_final[0]['amount_total']:,.2f}")

lineas_final = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['price_unit']}
)

if lineas_final:
    precio_final = lineas_final[0]['price_unit']
    print(f"  Precio línea: ${precio_final:,.2f} {'✓' if abs(precio_final - PRECIO_CORRECTO) < 1 else '❌'}")

print("\n" + "=" * 100)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 100)
