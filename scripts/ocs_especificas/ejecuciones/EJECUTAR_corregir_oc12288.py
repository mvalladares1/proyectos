#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EJECUCIÓN REAL: Corrección en cadena de OC12288 - Precio $0.00 → $2.0 USD
⚠️ ESTE SCRIPT EJECUTA CAMBIOS REALES EN ODOO
"""
import xmlrpc.client
from datetime import datetime
import json

# Conexión a Odoo
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# PRECIO CORRECTO
PRECIO_CORRECTO = 2.0
PRODUCTO_CORRECTO = '[101252000] AR HB Org. Block en Bandeja'

print("=" * 100)
print("⚠️  EJECUCIÓN REAL: CORRECCIÓN OC12288")
print(f"PRECIO CORRECTO: ${PRECIO_CORRECTO} USD/kg")
print(f"PRODUCTO: {PRODUCTO_CORRECTO}")
print("=" * 100)
print("\n🔴 ESTE SCRIPT EJECUTARÁ CAMBIOS REALES EN ODOO")
print("=" * 100)

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"\n✅ Conectado como UID: {uid}\n")

# Log de cambios
log_cambios = {
    'fecha_ejecucion': datetime.now().isoformat(),
    'precio_correcto': PRECIO_CORRECTO,
    'usuario': username,
    'cambios_realizados': [],
    'errores': []
}

# ============================================================================
# PASO 1: OBTENER Y VALIDAR DATOS DE OC12288
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: VALIDACIÓN DE DATOS DE OC12288")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12288']]],
    {'fields': ['id', 'name', 'state', 'amount_total', 'order_line'], 'limit': 1}
)

if not oc:
    print("❌ OC12288 no encontrada")
    exit(1)

oc = oc[0]
oc_id = oc['id']

print(f"\n📋 OC ID: {oc_id}")
print(f"   Estado: {oc['state']}")
print(f"   Total Actual: ${oc['amount_total']:,.2f}")

if oc['state'] not in ['draft', 'sent', 'purchase', 'to approve']:
    print(f"\n⚠️  ADVERTENCIA: Estado '{oc['state']}' - ¿Continuar de todos modos? (s/n)")
    respuesta = input().strip().lower()
    if respuesta != 's':
        print("❌ Cancelado por el usuario")
        exit(0)

# ============================================================================
# PASO 2: CORREGIR LÍNEAS DE ORDEN DE COMPRA
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: CORRECCIÓN DE LÍNEAS DE ORDEN DE COMPRA")
print("=" * 100)

lineas_oc = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['id', 'product_id', 'name', 'product_qty', 'price_unit']}
)

print(f"\n📦 Encontradas {len(lineas_oc)} líneas\n")

for linea in lineas_oc:
    producto = linea['product_id'][1] if linea['product_id'] else 'N/A'
    precio_actual = linea['price_unit']
    
    # Solo corregir el producto correcto con precio 0
    if PRODUCTO_CORRECTO in producto and precio_actual == 0.0:
        print(f"🔧 Corrigiendo línea ID {linea['id']}: {producto}")
        print(f"   Precio actual: ${precio_actual:,.2f}")
        print(f"   Precio nuevo: ${PRECIO_CORRECTO:,.2f}")
        
        try:
            # EJECUTAR CAMBIO
            result = models.execute_kw(
                db, uid, password,
                'purchase.order.line', 'write',
                [[linea['id']], {'price_unit': PRECIO_CORRECTO}]
            )
            
            if result:
                print(f"   ✅ ACTUALIZADO correctamente")
                log_cambios['cambios_realizados'].append({
                    'paso': 'purchase.order.line',
                    'id': linea['id'],
                    'campo': 'price_unit',
                    'valor_anterior': precio_actual,
                    'valor_nuevo': PRECIO_CORRECTO,
                    'producto': producto
                })
            else:
                print(f"   ❌ ERROR: No se pudo actualizar")
                log_cambios['errores'].append({
                    'paso': 'purchase.order.line',
                    'id': linea['id'],
                    'error': 'write retornó False'
                })
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {e}")
            log_cambios['errores'].append({
                'paso': 'purchase.order.line',
                'id': linea['id'],
                'error': str(e)
            })
    else:
        print(f"⏭️  Saltando línea ID {linea['id']}: {producto} (precio: ${precio_actual:,.2f})")

# Verificar cambio en OC
print("\n📊 Verificando total de OC...")
oc_updated = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['amount_total']}
)
if oc_updated:
    print(f"   Total OC actualizado: ${oc_updated[0]['amount_total']:,.2f}")

# ============================================================================
# PASO 3: CORREGIR MOVIMIENTOS DE STOCK
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: CORRECCIÓN DE MOVIMIENTOS DE STOCK")
print("=" * 100)

pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
    [[['origin', '=', 'OC12288']]],
    {'fields': ['id', 'name', 'state', 'move_ids']}
)

if pickings:
    print(f"\n📥 Encontrados {len(pickings)} albaranes\n")
    
    for picking in pickings:
        print(f"Albarán: {picking['name']} (Estado: {picking['state']})")
        
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': ['id', 'product_id', 'quantity_done', 'price_unit', 'state']}
            )
            
            for move in moves:
                producto = move['product_id'][1] if move['product_id'] else 'N/A'
                precio_actual = move.get('price_unit', 0)
                
                # Solo corregir el producto correcto con precio 0 y que tenga cantidad realizada
                if PRODUCTO_CORRECTO in producto and precio_actual == 0.0 and move.get('quantity_done', 0) > 0:
                    print(f"  🔧 Corrigiendo movimiento ID {move['id']}: {producto}")
                    print(f"     Cantidad: {move['quantity_done']} kg")
                    print(f"     Precio actual: ${precio_actual:,.2f}")
                    print(f"     Precio nuevo: ${PRECIO_CORRECTO:,.2f}")
                    
                    try:
                        # EJECUTAR CAMBIO
                        result = models.execute_kw(
                            db, uid, password,
                            'stock.move', 'write',
                            [[move['id']], {'price_unit': PRECIO_CORRECTO}]
                        )
                        
                        if result:
                            print(f"     ✅ ACTUALIZADO correctamente")
                            log_cambios['cambios_realizados'].append({
                                'paso': 'stock.move',
                                'id': move['id'],
                                'campo': 'price_unit',
                                'valor_anterior': precio_actual,
                                'valor_nuevo': PRECIO_CORRECTO,
                                'producto': producto,
                                'cantidad': move['quantity_done']
                            })
                        else:
                            print(f"     ❌ ERROR: No se pudo actualizar")
                            log_cambios['errores'].append({
                                'paso': 'stock.move',
                                'id': move['id'],
                                'error': 'write retornó False'
                            })
                    except Exception as e:
                        print(f"     ❌ EXCEPCIÓN: {e}")
                        log_cambios['errores'].append({
                            'paso': 'stock.move',
                            'id': move['id'],
                            'error': str(e)
                        })
                else:
                    print(f"  ⏭️  Saltando movimiento ID {move['id']}: {producto} (precio: ${precio_actual:,.2f}, qty: {move.get('quantity_done', 0)})")
            print()
else:
    print("\n⚠️ No hay albaranes asociados")

# ============================================================================
# PASO 4: CORREGIR CAPAS DE VALORACIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 4: CORRECCIÓN DE CAPAS DE VALORACIÓN DE INVENTARIO")
print("=" * 100)

# Buscar capas con el producto correcto, fecha específica y costo 0
valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
    [[
        ['description', 'ilike', 'RF/RFP/IN/02140'],  # Albarán específico de OC12288
        ['unit_cost', '=', 0.0]
    ]],
    {'fields': ['id', 'product_id', 'quantity', 'unit_cost', 'value', 'remaining_qty', 'remaining_value', 'description']}
)

if valuation_layers:
    print(f"\n📉 Encontradas {len(valuation_layers)} capas de valoración\n")
    
    for vl in valuation_layers:
        producto = vl['product_id'][1] if vl['product_id'] else 'N/A'
        
        # Solo corregir el producto correcto
        if PRODUCTO_CORRECTO in producto:
            cantidad = vl['quantity']
            costo_actual = vl['unit_cost']
            valor_actual = vl['value']
            nuevo_valor = cantidad * PRECIO_CORRECTO
            
            print(f"🔧 Corrigiendo capa ID {vl['id']}: {producto}")
            print(f"   Descripción: {vl['description']}")
            print(f"   Cantidad: {cantidad} kg")
            print(f"   Costo Unit. actual: ${costo_actual:,.2f}")
            print(f"   Costo Unit. nuevo: ${PRECIO_CORRECTO:,.2f}")
            print(f"   Valor actual: ${valor_actual:,.2f}")
            print(f"   Valor nuevo: ${nuevo_valor:,.2f}")
            
            try:
                # EJECUTAR CAMBIO
                valores_actualizar = {
                    'unit_cost': PRECIO_CORRECTO,
                    'value': nuevo_valor
                }
                
                # Si hay cantidad remanente, actualizar también el valor remanente
                if vl.get('remaining_qty', 0) > 0:
                    nuevo_remaining_value = vl['remaining_qty'] * PRECIO_CORRECTO
                    valores_actualizar['remaining_value'] = nuevo_remaining_value
                    print(f"   Remaining value: ${vl.get('remaining_value', 0):,.2f} → ${nuevo_remaining_value:,.2f}")
                
                result = models.execute_kw(
                    db, uid, password,
                    'stock.valuation.layer', 'write',
                    [[vl['id']], valores_actualizar]
                )
                
                if result:
                    print(f"   ✅ ACTUALIZADO correctamente")
                    log_cambios['cambios_realizados'].append({
                        'paso': 'stock.valuation.layer',
                        'id': vl['id'],
                        'campos': valores_actualizar,
                        'valor_anterior_unit_cost': costo_actual,
                        'valor_anterior_value': valor_actual,
                        'producto': producto,
                        'cantidad': cantidad
                    })
                else:
                    print(f"   ❌ ERROR: No se pudo actualizar")
                    log_cambios['errores'].append({
                        'paso': 'stock.valuation.layer',
                        'id': vl['id'],
                        'error': 'write retornó False'
                    })
            except Exception as e:
                print(f"   ❌ EXCEPCIÓN: {e}")
                log_cambios['errores'].append({
                    'paso': 'stock.valuation.layer',
                    'id': vl['id'],
                    'error': str(e)
                })
            print()
        else:
            print(f"⏭️  Saltando capa ID {vl['id']}: {producto}")
else:
    print("\n⚠️ No hay capas de valoración para corregir")

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN DE EJECUCIÓN")
print("=" * 100)

total_cambios = len(log_cambios['cambios_realizados'])
total_errores = len(log_cambios['errores'])

print(f"""
✅ CAMBIOS REALIZADOS: {total_cambios}
❌ ERRORES ENCONTRADOS: {total_errores}

DESGLOSE:
""")

# Contar por tipo
tipos = {}
for cambio in log_cambios['cambios_realizados']:
    paso = cambio['paso']
    tipos[paso] = tipos.get(paso, 0) + 1

for tipo, cantidad in tipos.items():
    print(f"  • {tipo}: {cantidad} cambios")

if total_errores > 0:
    print(f"\n⚠️  ERRORES:")
    for error in log_cambios['errores']:
        print(f"  • {error['paso']} ID {error['id']}: {error['error']}")

# Verificación final
print("\n" + "=" * 100)
print("VERIFICACIÓN FINAL")
print("=" * 100)

oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['name', 'amount_total', 'state']}
)

if oc_final:
    print(f"\n📋 OC12288 después de corrección:")
    print(f"   Total: ${oc_final[0]['amount_total']:,.2f}")
    print(f"   Estado: {oc_final[0]['state']}")

# Guardar log
try:
    filename = f'oc12288_ejecucion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_cambios, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Log de ejecución guardado en: {filename}")
except Exception as e:
    print(f"\n⚠️ No se pudo guardar el log: {e}")

print("\n" + "=" * 100)
print("FIN DE LA EJECUCIÓN")
print("=" * 100)

if total_errores == 0 and total_cambios > 0:
    print("\n✅ CORRECCIÓN COMPLETADA EXITOSAMENTE")
elif total_errores > 0:
    print("\n⚠️  CORRECCIÓN COMPLETADA CON ERRORES - REVISAR LOG")
else:
    print("\n⚠️  NO SE REALIZARON CAMBIOS")
