#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANALIZAR OC09581: Discrepancia en cantidad
- Línea OC: 103
- Recepción: 746,650 kg
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("ANÁLISIS OC09581 - DISCREPANCIA EN CANTIDAD")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

# PASO 1: Buscar OC09581
print("=" * 100)
print("PASO 1: INFORMACIÓN DE LA OC")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC09581']]],
    {'fields': ['id', 'name', 'partner_id', 'date_order', 'state', 'currency_id', 'amount_total'], 'limit': 1}
)

if not oc:
    print("❌ OC09581 no encontrada")
    exit(1)

oc = oc[0]
oc_id = oc['id']

print(f"\n📋 OC: {oc['name']} (ID: {oc_id})")
print(f"   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
print(f"   Fecha: {oc['date_order']}")
print(f"   Estado: {oc['state']}")
print(f"   Moneda: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")
print(f"   Total: ${oc['amount_total']:,.2f}")

# PASO 2: Líneas de la OC
print("\n" + "=" * 100)
print("PASO 2: LÍNEAS DE LA OC")
print("=" * 100)

lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['id', 'product_id', 'product_qty', 'product_uom', 'price_unit', 'price_subtotal', 'qty_received']}
)

print(f"\n📦 Total de líneas: {len(lineas)}\n")

for linea in lineas:
    print(f"Línea ID {linea['id']}:")
    print(f"  Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"  Cantidad pedida: {linea['product_qty']} {linea['product_uom'][1] if linea['product_uom'] else ''}")
    print(f"  Cantidad recibida: {linea.get('qty_received', 0)}")
    print(f"  Precio unitario: ${linea['price_unit']:,.2f}")
    print(f"  Subtotal: ${linea['price_subtotal']:,.2f}")
    print(f"  ⚠️  DISCREPANCIA: Pedida={linea['product_qty']}, Recibida={linea.get('qty_received', 0)}")
    print()

# PASO 3: Recepciones relacionadas
print("=" * 100)
print("PASO 3: RECEPCIONES (STOCK.PICKING)")
print("=" * 100)

pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
    [[['origin', '=', 'OC09581']]],
    {'fields': ['id', 'name', 'state', 'date_done', 'picking_type_id']}
)

print(f"\n📦 Total de recepciones: {len(pickings)}\n")

for picking in pickings:
    print(f"Recepción: {picking['name']} (ID: {picking['id']})")
    print(f"  Estado: {picking['state']}")
    print(f"  Fecha: {picking.get('date_done', 'N/A')}")
    print(f"  Tipo: {picking['picking_type_id'][1] if picking['picking_type_id'] else 'N/A'}")
    
    # Movimientos de esta recepción
    moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
        [[['picking_id', '=', picking['id']]]],
        {'fields': ['id', 'product_id', 'product_uom_qty', 'quantity_done', 'product_uom', 'state']}
    )
    
    for move in moves:
        print(f"    Movimiento ID {move['id']}:")
        print(f"      Producto: {move['product_id'][1] if move['product_id'] else 'N/A'}")
        print(f"      Cantidad esperada: {move['product_uom_qty']} {move['product_uom'][1] if move['product_uom'] else ''}")
        print(f"      Cantidad realizada: {move['quantity_done']} {move['product_uom'][1] if move['product_uom'] else ''}")
        print(f"      Estado: {move['state']}")
    print()

# PASO 4: Valoración de inventario
print("=" * 100)
print("PASO 4: VALORACIÓN DE INVENTARIO")
print("=" * 100)

# Buscar capas de valoración por descripción
if lineas:
    producto_name = lineas[0]['product_id'][1] if lineas[0]['product_id'] else ''
    
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[['description', 'ilike', 'OC09581']]],
        {'fields': ['id', 'description', 'quantity', 'unit_cost', 'value', 'create_date'], 'limit': 10}
    )
    
    print(f"\n💰 Capas de valoración encontradas: {len(valuation_layers)}\n")
    
    for layer in valuation_layers:
        print(f"Capa ID {layer['id']}:")
        print(f"  Descripción: {layer['description']}")
        print(f"  Cantidad: {layer['quantity']}")
        print(f"  Costo unitario: ${layer['unit_cost']:,.2f}")
        print(f"  Valor: ${layer['value']:,.2f}")
        print(f"  Fecha: {layer['create_date']}")
        print()

print("=" * 100)
print("RESUMEN DE ANÁLISIS")
print("=" * 100)

if lineas:
    linea = lineas[0]
    print(f"\n⚠️  DISCREPANCIA DETECTADA:")
    print(f"   Cantidad en línea OC: {linea['product_qty']}")
    print(f"   Cantidad recibida: {linea.get('qty_received', 0)}")
    print(f"   Diferencia: {linea.get('qty_received', 0) - linea['product_qty']}")
    print(f"\n💡 CORRECCIÓN NECESARIA:")
    print(f"   Actualizar purchase.order.line ID {linea['id']}")
    print(f"   Cambiar product_qty de {linea['product_qty']} a {linea.get('qty_received', 0)}")
