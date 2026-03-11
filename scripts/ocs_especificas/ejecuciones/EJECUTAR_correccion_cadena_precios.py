#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECCIÓN EN CADENA DE PRECIOS
Actualizar stock.move y stock.valuation.layer con precios correctos
"""
import xmlrpc.client
import json
from datetime import datetime

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Correcciones identificadas
CORRECCIONES = [
    {
        'oc': 'OC12902',
        'move_id': 166160,
        'precio_correcto': 3085.0,
        'cantidad': 4863.540
    },
    {
        'oc': 'OC12755',
        'move_id': 163847,
        'precio_correcto': 2000.0,
        'cantidad': 138.480
    },
    {
        'oc': 'OC13491',
        'move_id': 172191,
        'precio_correcto': 3300.0,
        'cantidad': 4975.760
    },
    {
        'oc': 'OC13530',
        'move_id': 172502,
        'precio_correcto': 3300.0,
        'cantidad': 4566.060
    },
    {
        'oc': 'OC13596',
        'move_id': 173377,
        'precio_correcto': 3300.0,
        'cantidad': 3104.160
    }
]

print("=" * 120)
print("CORRECCIÓN EN CADENA DE PRECIOS EN MOVIMIENTOS DE STOCK")
print("=" * 120)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

log = {
    'fecha_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'correcciones': []
}

for correccion in CORRECCIONES:
    print("=" * 120)
    print(f"{correccion['oc']} - Move ID {correccion['move_id']}")
    print("=" * 120)
    
    move_id = correccion['move_id']
    precio_correcto = correccion['precio_correcto']
    cantidad = correccion['cantidad']
    
    # Obtener datos actuales del movimiento
    move = models.execute_kw(db, uid, password, 'stock.move', 'read',
        [[move_id]],
        {'fields': ['id', 'product_id', 'price_unit', 'quantity_done', 'state', 'picking_id']}
    )
    
    if not move:
        print(f"❌ Move {move_id} no encontrado\n")
        continue
    
    move = move[0]
    precio_antes = move.get('price_unit', 0)
    
    print(f"\n📦 Movimiento ID {move_id}")
    print(f"   Producto: {move['product_id'][1] if move['product_id'] else 'N/A'}")
    print(f"   Picking: {move['picking_id'][1] if move.get('picking_id') else 'N/A'}")
    print(f"   Estado: {move['state']}")
    print(f"   Cantidad: {move['quantity_done']:,.3f}")
    print(f"   Precio antes: ${precio_antes:,.2f}")
    print(f"   Precio correcto: ${precio_correcto:,.2f}")
    
    # ACTUALIZAR MOVIMIENTO
    print(f"\n🔧 Actualizando precio en stock.move...")
    try:
        result = models.execute_kw(
            db, uid, password,
            'stock.move', 'write',
            [[move_id], {'price_unit': precio_correcto}]
        )
        
        if result:
            print(f"   ✅ Stock.move actualizado")
            
            # Verificar
            move_verificado = models.execute_kw(db, uid, password, 'stock.move', 'read',
                [[move_id]], {'fields': ['price_unit']}
            )
            
            if move_verificado:
                precio_nuevo = move_verificado[0]['price_unit']
                print(f"   Verificado: ${precio_nuevo:,.2f} {'✓' if abs(precio_nuevo - precio_correcto) < 0.01 else '❌'}")
        else:
            print(f"   ❌ ERROR al actualizar")
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN: {e}")
    
    # BUSCAR Y ACTUALIZAR CAPAS DE VALORACIÓN
    print(f"\n💰 Buscando capas de valoración...")
    
    # Buscar por stock_move_id
    valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
        [[['stock_move_id', '=', move_id]]],
        {'fields': ['id', 'quantity', 'unit_cost', 'value', 'description'], 'limit': 10}
    )
    
    if valuation_layers:
        print(f"   Encontradas {len(valuation_layers)} capas de valoración")
        
        for layer in valuation_layers:
            costo_antes = layer['unit_cost']
            valor_antes = layer['value']
            cantidad_layer = layer['quantity']
            valor_correcto = cantidad_layer * precio_correcto
            
            print(f"\n   Layer ID {layer['id']}:")
            print(f"      Cantidad: {cantidad_layer:,.3f}")
            print(f"      Costo antes: ${costo_antes:,.2f}")
            print(f"      Costo correcto: ${precio_correcto:,.2f}")
            print(f"      Valor antes: ${valor_antes:,.2f}")
            print(f"      Valor correcto: ${valor_correcto:,.2f}")
            
            try:
                result_layer = models.execute_kw(
                    db, uid, password,
                    'stock.valuation.layer', 'write',
                    [[layer['id']], {
                        'unit_cost': precio_correcto,
                        'value': valor_correcto
                    }]
                )
                
                if result_layer:
                    print(f"      ✅ Capa de valoración actualizada")
                    
                    # Verificar
                    layer_verificado = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'read',
                        [[layer['id']]], {'fields': ['unit_cost', 'value']}
                    )
                    
                    if layer_verificado:
                        print(f"      Verificado: Costo ${layer_verificado[0]['unit_cost']:,.2f}, Valor ${layer_verificado[0]['value']:,.2f} ✓")
                else:
                    print(f"      ❌ ERROR")
            except Exception as e:
                print(f"      ❌ EXCEPCIÓN: {e}")
    else:
        print(f"   ⚠️  No se encontraron capas de valoración para este movimiento")
    
    log['correcciones'].append({
        'oc': correccion['oc'],
        'move_id': move_id,
        'precio_antes': precio_antes,
        'precio_despues': precio_correcto,
        'capas_actualizadas': len(valuation_layers) if valuation_layers else 0
    })
    
    print()

# VERIFICACIÓN FINAL
print("=" * 120)
print("VERIFICACIÓN FINAL")
print("=" * 120)

for correccion in CORRECCIONES:
    move = models.execute_kw(db, uid, password, 'stock.move', 'read',
        [[correccion['move_id']]], {'fields': ['price_unit']}
    )
    
    if move:
        precio = move[0]['price_unit']
        correcto = abs(precio - correccion['precio_correcto']) < 0.01
        estado = "✓" if correcto else "❌"
        print(f"   {estado} {correccion['oc']} - Move {correccion['move_id']}: ${precio:,.2f}")

# Guardar log
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'correccion_cadena_precios_{timestamp}.json'

with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"\n💾 Log guardado: {log_file}")
print("\n" + "=" * 120)
print("✅ CORRECCIÓN EN CADENA COMPLETADA")
print("=" * 120)
