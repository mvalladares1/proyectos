#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ANÁLISIS DE 4 OCs CON ERRORES DE PRECIO Y/O CANTIDAD
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

OCS = ['OC12755', 'OC13491', 'OC13530', 'OC13596']

print("=" * 100)
print("ANÁLISIS DE 4 OCs CON ERRORES")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

for oc_name in OCS:
    print("=" * 100)
    print(f"OC: {oc_name}")
    print("=" * 100)
    
    # Buscar OC
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'partner_id', 'date_order', 'state', 'currency_id', 'amount_total'], 'limit': 1}
    )
    
    if not oc:
        print(f"❌ {oc_name} no encontrada\n")
        continue
    
    oc = oc[0]
    oc_id = oc['id']
    
    print(f"\n📋 {oc_name} (ID: {oc_id})")
    print(f"   Proveedor: {oc['partner_id'][1] if oc['partner_id'] else 'N/A'}")
    print(f"   Fecha: {oc['date_order']}")
    print(f"   Estado: {oc['state']}")
    print(f"   Moneda: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")
    print(f"   Total: ${oc['amount_total']:,.2f}")
    
    # Líneas
    lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': ['id', 'product_id', 'product_qty', 'qty_received', 'price_unit', 'price_subtotal']}
    )
    
    print(f"\n📦 Líneas: {len(lineas)}")
    for linea in lineas:
        print(f"   Línea ID {linea['id']}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
        print(f"      Cantidad pedida: {linea['product_qty']:,.3f}")
        print(f"      Cantidad recibida: {linea.get('qty_received', 0):,.3f}")
        print(f"      Precio unitario: ${linea['price_unit']:,.2f}")
        print(f"      Subtotal: ${linea['price_subtotal']:,.2f}")
    
    # Recepciones
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['origin', '=', oc_name]]],
        {'fields': ['id', 'name', 'state']}
    )
    
    print(f"\n📦 Recepciones: {len(pickings)}")
    for picking in pickings:
        print(f"   {picking['name']} (ID: {picking['id']}) - Estado: {picking['state']}")
        
        # Movimientos
        moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
            [[['picking_id', '=', picking['id']]]],
            {'fields': ['id', 'product_id', 'product_uom_qty', 'quantity_done']}
        )
        
        for move in moves:
            if move['product_id']:
                print(f"      Movimiento ID {move['id']}: {move['product_id'][1]}")
                print(f"         Esperada: {move['product_uom_qty']:,.3f}, Realizada: {move['quantity_done']:,.3f}")
    
    print()

print("=" * 100)
print("FIN DEL ANÁLISIS")
print("=" * 100)
