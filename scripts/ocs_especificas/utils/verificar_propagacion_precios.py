#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAR PROPAGACIÓN DE PRECIOS EN CADENA
Revisar si los cambios en purchase.order.line se propagaron a:
- stock.move (precio unitario)
- stock.valuation.layer (unit_cost)
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# OCs corregidas con sus precios correctos
OCS_VERIFICAR = {
    'OC12288': {'precio': 2.0, 'producto': '[101252000] AR HB Org. Block en Bandeja'},
    'OC11401': {'precio': 1.6, 'producto': '[101122000] AR HB Conv. IQF en Bandeja'},
    'OC12902': {'precio': 3085.0, 'producto': '[102121000] FB S/V Conv. IQF en Bandeja'},
    'OC09581': {'precio': 2.3, 'producto': '[101222000] AR HB Org. IQF en Bandeja'},
    'OC12755': {'precio': 2000.0, 'producto': '[102151000] FB S/V Conv. Block en Bandeja'},
    'OC13491': {'precio': 3300.0, 'producto': '[102221000] FB S/V Org. IQF en Bandeja'},
    'OC13530': {'precio': 3300.0, 'producto': '[102221000] FB S/V Org. IQF en Bandeja'},
    'OC13596': {'precio': 3300.0, 'producto': '[102221000] FB S/V Org. IQF en Bandeja'}
}

print("=" * 120)
print("VERIFICACIÓN DE PROPAGACIÓN DE PRECIOS EN CADENA")
print("=" * 120)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

problemas = []

for oc_name, config in OCS_VERIFICAR.items():
    print("=" * 120)
    print(f"OC: {oc_name} - Precio correcto: ${config['precio']:,.2f}")
    print("=" * 120)
    
    precio_correcto = config['precio']
    
    # Buscar OC
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id'], 'limit': 1}
    )
    
    if not oc:
        print(f"❌ {oc_name} no encontrada\n")
        continue
    
    oc_id = oc[0]['id']
    
    # PASO 1: Verificar líneas de compra
    lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': ['id', 'product_id', 'price_unit', 'product_qty']}
    )
    
    print(f"\n📋 LÍNEAS DE COMPRA")
    for linea in lineas:
        if linea['product_id'] and config['producto'] in linea['product_id'][1]:
            precio_linea = linea['price_unit']
            estado_linea = "✓" if abs(precio_linea - precio_correcto) < 0.01 else "❌"
            print(f"   {estado_linea} Línea ID {linea['id']}: ${precio_linea:,.2f}")
            
            if abs(precio_linea - precio_correcto) >= 0.01:
                problemas.append({
                    'oc': oc_name,
                    'tipo': 'purchase.order.line',
                    'id': linea['id'],
                    'precio_actual': precio_linea,
                    'precio_correcto': precio_correcto
                })
            
            linea_id = linea['id']
    
    # PASO 2: Verificar movimientos de stock
    pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
        [[['origin', '=', oc_name]]],
        {'fields': ['id', 'name', 'state']}
    )
    
    print(f"\n📦 MOVIMIENTOS DE INVENTARIO")
    for picking in pickings:
        if picking['state'] != 'done':
            continue
            
        moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
            [[['picking_id', '=', picking['id']]]],
            {'fields': ['id', 'product_id', 'price_unit', 'quantity_done', 'purchase_line_id']}
        )
        
        for move in moves:
            if move['product_id'] and config['producto'] in move['product_id'][1]:
                precio_move = move.get('price_unit', 0)
                estado_move = "✓" if abs(precio_move - precio_correcto) < 0.01 else "❌"
                print(f"   {estado_move} Move ID {move['id']} ({picking['name']}): ${precio_move:,.2f} | Cantidad: {move['quantity_done']:,.3f}")
                
                if abs(precio_move - precio_correcto) >= 0.01 and move['quantity_done'] > 0:
                    problemas.append({
                        'oc': oc_name,
                        'tipo': 'stock.move',
                        'id': move['id'],
                        'picking': picking['name'],
                        'cantidad': move['quantity_done'],
                        'precio_actual': precio_move,
                        'precio_correcto': precio_correcto
                    })
    
    # PASO 3: Verificar capas de valoración
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[['description', 'ilike', oc_name]]],
        {'fields': ['id', 'description', 'quantity', 'unit_cost', 'value', 'product_id'], 'limit': 20}
    )
    
    print(f"\n💰 CAPAS DE VALORACIÓN")
    if valuation_layers:
        for layer in valuation_layers:
            if layer['product_id'] and config['producto'][:15] in layer['product_id'][1]:
                costo_layer = layer['unit_cost']
                estado_layer = "✓" if abs(costo_layer - precio_correcto) < 0.01 else "❌"
                print(f"   {estado_layer} Layer ID {layer['id']}: Costo ${costo_layer:,.2f} | Cantidad: {layer['quantity']:,.3f} | Valor: ${layer['value']:,.2f}")
                
                if abs(costo_layer - precio_correcto) >= 0.01 and layer['quantity'] != 0:
                    problemas.append({
                        'oc': oc_name,
                        'tipo': 'stock.valuation.layer',
                        'id': layer['id'],
                        'cantidad': layer['quantity'],
                        'costo_actual': costo_layer,
                        'costo_correcto': precio_correcto,
                        'valor_actual': layer['value'],
                        'valor_correcto': layer['quantity'] * precio_correcto
                    })
    else:
        print(f"   ⚠️  No se encontraron capas de valoración")
    
    print()

# RESUMEN DE PROBLEMAS
print("=" * 120)
print("RESUMEN DE PROBLEMAS ENCONTRADOS")
print("=" * 120)

if problemas:
    print(f"\n⚠️  Se encontraron {len(problemas)} problemas:\n")
    
    for p in problemas:
        print(f"❌ {p['oc']} - {p['tipo']} ID {p['id']}")
        if p['tipo'] == 'stock.move':
            print(f"   Picking: {p['picking']}")
            print(f"   Cantidad: {p['cantidad']:,.3f}")
            print(f"   Precio: ${p['precio_actual']:,.2f} → ${p['precio_correcto']:,.2f}")
        elif p['tipo'] == 'stock.valuation.layer':
            print(f"   Cantidad: {p['cantidad']:,.3f}")
            print(f"   Costo: ${p['costo_actual']:,.2f} → ${p['costo_correcto']:,.2f}")
            print(f"   Valor: ${p['valor_actual']:,.2f} → ${p['valor_correcto']:,.2f}")
        else:
            print(f"   Precio: ${p['precio_actual']:,.2f} → ${p['precio_correcto']:,.2f}")
        print()
    
    print("💡 Se requiere corrección en cadena")
else:
    print("\n✅ No se encontraron problemas. Todos los precios están correctos en toda la cadena.")

print("\n" + "=" * 120)
print("FIN DE LA VERIFICACIÓN")
print("=" * 120)
