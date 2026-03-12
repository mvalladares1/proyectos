#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Corrección completa en cadena: OC10388
Precio: $1,900 → $2,850
Actualiza: purchase.order.line → stock.move → stock.valuation.layer
"""
import xmlrpc.client
import json
from datetime import datetime

# ============= CONFIGURACIÓN =============
OC_NAME = 'OC10388'

# Definir correcciones necesarias
CORRECCIONES = {
    'oc_id': 10397,
    'moneda_id': None,  # No cambiar moneda (ya es CLP)
    'lineas': [
        {
            'linea_id': 16945,
            'precio_nuevo': 2850.0,
            'cantidad_nueva': None,  # No cambiar cantidad
            'moves_ids': [146774]  # Solo el move done, no el cancelado (147060)
        }
    ],
    'facturas_borrador_eliminar': []  # No hay facturas
}

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# ============= EJECUCIÓN =============

print("=" * 120)
print(f"CORRECCIÓN EN CADENA: {OC_NAME}")
print("=" * 120)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

log = {
    'oc': OC_NAME,
    'fecha_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'cambios': []
}

# Buscar OC
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', OC_NAME]]],
    {'fields': ['id', 'amount_total', 'state'], 'limit': 1}
)

if not oc:
    print(f"❌ {OC_NAME} no encontrada")
    exit(1)

oc_id = oc[0]['id']
total_antes = oc[0]['amount_total']

print(f"📋 {OC_NAME} (ID: {oc_id})")
print(f"   Total antes: ${total_antes:,.2f}")
print(f"   Estado: {oc[0]['state']}\n")

# ========== PASO 1: ELIMINAR FACTURAS BORRADOR ==========
if CORRECCIONES['facturas_borrador_eliminar']:
    print("=" * 120)
    print("PASO 1: ELIMINAR FACTURAS BORRADOR")
    print("=" * 120)
    
    for factura_id in CORRECCIONES['facturas_borrador_eliminar']:
        try:
            factura = models.execute_kw(db, uid, password, 'account.move', 'read',
                [[factura_id]], {'fields': ['name', 'state']}
            )
            
            if factura and factura[0]['state'] == 'draft':
                print(f"\n🗑️  Eliminando factura {factura[0]['name']} (ID: {factura_id})")
                
                result = models.execute_kw(db, uid, password, 'account.move', 'unlink', [[factura_id]])
                
                if result:
                    print(f"   ✅ Factura eliminada")
                    log['cambios'].append({
                        'tipo': 'factura_eliminada',
                        'id': factura_id,
                        'nombre': factura[0]['name']
                    })
                else:
                    print(f"   ❌ ERROR al eliminar")
            else:
                print(f"   ⚠️  Factura {factura_id} no está en borrador o no existe")
        
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {e}")
else:
    print("✅ PASO 1: No hay facturas borrador para eliminar\n")

# ========== PASO 2: CAMBIAR MONEDA DE OC (SI APLICA) ==========
if CORRECCIONES['moneda_id']:
    print("\n" + "=" * 120)
    print("PASO 2: ACTUALIZAR MONEDA DE OC")
    print("=" * 120)
    
    try:
        result = models.execute_kw(
            db, uid, password,
            'purchase.order', 'write',
            [[oc_id], {'currency_id': CORRECCIONES['moneda_id']}]
        )
        
        if result:
            print(f"✅ Moneda de OC actualizada")
            log['cambios'].append({
                'tipo': 'oc_moneda',
                'id': oc_id,
                'moneda_nueva': CORRECCIONES['moneda_id']
            })
        else:
            print(f"❌ ERROR al actualizar moneda")
    except Exception as e:
        print(f"❌ EXCEPCIÓN: {e}")
else:
    print("✅ PASO 2: No se requiere cambio de moneda\n")

# ========== PASO 3: ACTUALIZAR LÍNEAS DE COMPRA ==========
print("=" * 120)
print("PASO 3: ACTUALIZAR LÍNEAS DE COMPRA")
print("=" * 120)

for linea_config in CORRECCIONES['lineas']:
    linea_id = linea_config['linea_id']
    
    if not linea_id:
        print("⚠️  No hay linea_id configurada")
        continue
    
    # Obtener datos actuales
    linea = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
        [[linea_id]], {'fields': ['product_id', 'product_qty', 'price_unit', 'price_subtotal']}
    )
    
    if not linea:
        print(f"❌ Línea {linea_id} no encontrada")
        continue
    
    linea = linea[0]
    
    print(f"\n🔧 Línea ID {linea_id}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    
    # Preparar actualización
    actualizacion = {}
    
    if linea_config['precio_nuevo'] is not None:
        print(f"   Precio: ${linea['price_unit']:,.2f} → ${linea_config['precio_nuevo']:,.2f}")
        actualizacion['price_unit'] = linea_config['precio_nuevo']
    
    if linea_config['cantidad_nueva'] is not None:
        print(f"   Cantidad: {linea['product_qty']:,.3f} → {linea_config['cantidad_nueva']:,.3f}")
        actualizacion['product_qty'] = linea_config['cantidad_nueva']
    
    if CORRECCIONES['moneda_id']:
        actualizacion['currency_id'] = CORRECCIONES['moneda_id']
    
    # Ejecutar actualización
    if actualizacion:
        try:
            result = models.execute_kw(
                db, uid, password,
                'purchase.order.line', 'write',
                [[linea_id], actualizacion]
            )
            
            if result:
                print(f"   ✅ Línea actualizada")
                
                # Verificar
                linea_nueva = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
                    [[linea_id]], {'fields': ['product_qty', 'price_unit', 'price_subtotal']}
                )
                
                if linea_nueva:
                    print(f"   Subtotal nuevo: ${linea_nueva[0]['price_subtotal']:,.2f}")
                    
                    log['cambios'].append({
                        'tipo': 'purchase.order.line',
                        'id': linea_id,
                        'precio_antes': linea['price_unit'],
                        'precio_despues': linea_nueva[0]['price_unit'],
                        'cantidad_antes': linea['product_qty'],
                        'cantidad_despues': linea_nueva[0]['product_qty']
                    })
            else:
                print(f"   ❌ ERROR")
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {e}")

# ========== PASO 4: ACTUALIZAR MOVIMIENTOS DE STOCK ==========
print("\n" + "=" * 120)
print("PASO 4: ACTUALIZAR MOVIMIENTOS DE STOCK (CORRECCIÓN EN CADENA)")
print("=" * 120)

for linea_config in CORRECCIONES['lineas']:
    if not linea_config['precio_nuevo']:
        continue
    
    precio_correcto = linea_config['precio_nuevo']
    
    for move_id in linea_config['moves_ids']:
        # Obtener movimiento
        move = models.execute_kw(db, uid, password, 'stock.move', 'read',
            [[move_id]], {'fields': ['product_id', 'price_unit', 'quantity_done', 'state']}
        )
        
        if not move:
            print(f"❌ Move {move_id} no encontrado")
            continue
        
        move = move[0]
        
        print(f"\n📦 Move ID {move_id}: {move['product_id'][1] if move['product_id'] else 'N/A'}")
        print(f"   Precio antes: ${move['price_unit']:,.2f}")
        print(f"   Precio nuevo: ${precio_correcto:,.2f}")
        print(f"   Cantidad: {move['quantity_done']:,.3f}")
        
        try:
            result = models.execute_kw(
                db, uid, password,
                'stock.move', 'write',
                [[move_id], {'price_unit': precio_correcto}]
            )
            
            if result:
                print(f"   ✅ Stock.move actualizado")
                log['cambios'].append({
                    'tipo': 'stock.move',
                    'id': move_id,
                    'precio_antes': move['price_unit'],
                    'precio_despues': precio_correcto
                })
            else:
                print(f"   ❌ ERROR")
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {e}")

# ========== PASO 5: ACTUALIZAR CAPAS DE VALORACIÓN ==========
print("\n" + "=" * 120)
print("PASO 5: ACTUALIZAR CAPAS DE VALORACIÓN (CORRECCIÓN EN CADENA)")
print("=" * 120)

for linea_config in CORRECCIONES['lineas']:
    if not linea_config['precio_nuevo']:
        continue
    
    precio_correcto = linea_config['precio_nuevo']
    
    for move_id in linea_config['moves_ids']:
        # Buscar capas de valoración por stock_move_id
        layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
            [[['stock_move_id', '=', move_id]]],
            {'fields': ['id', 'quantity', 'unit_cost', 'value']}
        )
        
        for layer in layers:
            cantidad = layer['quantity']
            valor_correcto = cantidad * precio_correcto
            
            print(f"\n💰 Layer ID {layer['id']} (move_id={move_id})")
            print(f"   Cantidad: {cantidad:,.3f}")
            print(f"   Costo antes: ${layer['unit_cost']:,.2f}")
            print(f"   Costo nuevo: ${precio_correcto:,.2f}")
            print(f"   Valor antes: ${layer['value']:,.2f}")
            print(f"   Valor nuevo: ${valor_correcto:,.2f}")
            
            try:
                result = models.execute_kw(
                    db, uid, password,
                    'stock.valuation.layer', 'write',
                    [[layer['id']], {
                        'unit_cost': precio_correcto,
                        'value': valor_correcto
                    }]
                )
                
                if result:
                    print(f"   ✅ Capa de valoración actualizada")
                    log['cambios'].append({
                        'tipo': 'stock.valuation.layer',
                        'id': layer['id'],
                        'costo_antes': layer['unit_cost'],
                        'costo_despues': precio_correcto,
                        'valor_antes': layer['value'],
                        'valor_despues': valor_correcto
                    })
                else:
                    print(f"   ❌ ERROR")
            except Exception as e:
                print(f"   ❌ EXCEPCIÓN: {e}")

# ========== VERIFICACIÓN FINAL ==========
print("\n" + "=" * 120)
print("VERIFICACIÓN FINAL")
print("=" * 120)

oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['amount_total', 'currency_id']}
)

if oc_final:
    total_despues = oc_final[0]['amount_total']
    
    print(f"\n📋 {OC_NAME}:")
    print(f"   Total antes: ${total_antes:,.2f}")
    print(f"   Total después: ${total_despues:,.2f}")
    print(f"   Diferencia: ${total_despues - total_antes:,.2f}")
    print(f"   Moneda: {oc_final[0]['currency_id'][1] if oc_final[0].get('currency_id') else 'N/A'}")
    
    log['total_antes'] = total_antes
    log['total_despues'] = total_despues

# Guardar log
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'{OC_NAME.lower()}_ejecucion_{timestamp}.json'

with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"\n💾 Log guardado: {log_file}")
print(f"\n📊 Resumen de cambios:")
print(f"   Total modificaciones: {len(log['cambios'])}")

# Contar por tipo
tipos = {}
for cambio in log['cambios']:
    tipo = cambio['tipo']
    tipos[tipo] = tipos.get(tipo, 0) + 1

for tipo, cantidad in tipos.items():
    print(f"   - {tipo}: {cantidad}")

print("\n" + "=" * 120)
print("✅ CORRECCIÓN EN CADENA COMPLETADA")
print("=" * 120)
