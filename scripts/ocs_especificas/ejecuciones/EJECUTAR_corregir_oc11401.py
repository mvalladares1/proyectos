#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EJECUCIÓN REAL: Corrección OC11401 - Precio $6.50 → $1.60
⚠️ Este SCRIPT EJECUTA CAMBIOS REALES
"""
import xmlrpc.client
from datetime import datetime
import json

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# CORRECCIÓN
PRECIO_INCORRECTO = 6.5
PRECIO_CORRECTO = 1.6
PRODUCTO_CORRECTO = '[101122000] AR HB Conv. IQF en Bandeja'

print("=" * 100)
print("⚠️  EJECUCIÓN REAL: CORRECCIÓN OC11401")
print(f"PRECIO INCORRECTO: ${PRECIO_INCORRECTO} USD/kg")
print(f"PRECIO CORRECTO: ${PRECIO_CORRECTO} USD/kg")
print(f"PRODUCTO: {PRODUCTO_CORRECTO}")
print("=" * 100)
print("\n🔴 ESTE SCRIPT EJECUTARÁ CAMBIOS REALES EN ODOO")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

if not uid:
    print("❌ Error de autenticación")
    exit(1)

print(f"\n✅ Conectado como UID: {uid}\n")

log_cambios = {
    'fecha_ejecucion': datetime.now().isoformat(),
    'oc': 'OC11401',
    'precio_incorrecto': PRECIO_INCORRECTO,
    'precio_correcto': PRECIO_CORRECTO,
    'usuario': username,
    'cambios_realizados': [],
    'errores': []
}

# ============================================================================
# PASO 0: BUSCAR Y ELIMINAR FACTURA BORRADOR
# ============================================================================
print("=" * 100)
print("PASO 0: ELIMINAR FACTURA BORRADOR CON PRECIO INCORRECTO")
print("=" * 100)

oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC11401']]],
    {'fields': ['id', 'invoice_ids'], 'limit': 1}
)

if not oc:
    print("❌ OC11401 no encontrada")
    exit(1)

oc_id = oc[0]['id']
invoice_ids = oc[0].get('invoice_ids', [])

if invoice_ids:
    facturas_borrador = models.execute_kw(db, uid, password, 'account.move', 'search_read',
        [[['id', 'in', invoice_ids], ['state', '=', 'draft']]],
        {'fields': ['id', 'name', 'state', 'invoice_line_ids']}
    )
    
    for factura in facturas_borrador:
        print(f"\n📋 Factura borrador encontrada: {factura['name']} (ID: {factura['id']})")
        
        # Verificar si contiene la línea incorrecta
        if factura.get('invoice_line_ids'):
            lineas = models.execute_kw(db, uid, password, 'account.move.line', 'search_read',
                [[['id', 'in', factura['invoice_line_ids']]]],
                {'fields': ['price_unit', 'product_id', 'purchase_line_id']}
            )
            
            tiene_linea_incorrecta = any(l.get('price_unit') == PRECIO_INCORRECTO for l in lineas)
            
            if tiene_linea_incorrecta:
                print(f"   ⚠️  Contiene línea con precio incorrecto")
                print(f"   🗑️  Eliminando factura borrador...")
                
                try:
                    # Primero cancelar (si es necesario) y luego eliminar
                    result = models.execute_kw(
                        db, uid, password,
                        'account.move', 'button_draft',
                        [[factura['id']]]
                    )
                    
                    result = models.execute_kw(
                        db, uid, password,
                        'account.move', 'unlink',
                        [[factura['id']]]
                    )
                    
                    if result:
                        print(f"   ✅ Factura eliminada correctamente")
                        log_cambios['cambios_realizados'].append({
                            'paso': 'eliminar_factura_borrador',
                            'factura_id': factura['id'],
                            'factura_nombre': factura['name']
                        })
                    else:
                        print(f"   ⚠️  No se pudo eliminar la factura")
                        
                except Exception as e:
                    print(f"   ⚠️  Error al eliminar factura: {e}")
                    print(f"   Continuando con la corrección de todos modos...")
                    log_cambios['errores'].append({
                        'paso': 'eliminar_factura',
                        'error': str(e)
                    })

# ============================================================================
# PASO 1: CORREGIR LÍNEA DE OC
# ============================================================================
print("\n" + "=" * 100)
print("PASO 1: CORRECCIÓN DE LÍNEA DE ORDEN DE COMPRA")
print("=" * 100)

lineas_oc = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['id', 'product_id', 'product_qty', 'price_unit', 'qty_invoiced']}
)

print(f"\n📦 Encontradas {len(lineas_oc)} líneas\n")

for linea in lineas_oc:
    producto = linea['product_id'][1] if linea['product_id'] else 'N/A'
    precio_actual = linea['price_unit']
    
    if precio_actual == PRECIO_INCORRECTO and PRODUCTO_CORRECTO in producto:
        print(f"🔧 Corrigiendo línea ID {linea['id']}: {producto}")
        print(f"   Cantidad: {linea['product_qty']} kg")
        print(f"   Precio actual: ${precio_actual:,.2f}")
        print(f"   Precio nuevo: ${PRECIO_CORRECTO:,.2f}")
        print(f"   Cantidad facturada: {linea.get('qty_invoiced', 0)}")
        
        # Resetear cantidad facturada si es necesario
        valores_actualizar = {'price_unit': PRECIO_CORRECTO}
        if linea.get('qty_invoiced', 0) > 0:
            print(f"   ⚠️  Reseteando qty_invoiced a 0 (se eliminó la factura)")
            valores_actualizar['qty_invoiced'] = 0
        
        try:
            result = models.execute_kw(
                db, uid, password,
                'purchase.order.line', 'write',
                [[linea['id']], valores_actualizar]
            )
            
            if result:
                print(f"   ✅ ACTUALIZADO correctamente")
                log_cambios['cambios_realizados'].append({
                    'paso': 'purchase.order.line',
                    'id': linea['id'],
                    'campos': valores_actualizar,
                    'valor_anterior': precio_actual,
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

# Verificar total OC
print("\n📊 Verificando total de OC...")
oc_updated = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['amount_total']}
)
if oc_updated:
    print(f"   Total OC actualizado: ${oc_updated[0]['amount_total']:,.2f}")

# ============================================================================
# PASO 2: CORREGIR MOVIMIENTOS DE STOCK
# ============================================================================
print("\n" + "=" * 100)
print("PASO 2: CORRECCIÓN DE MOVIMIENTOS DE STOCK")
print("=" * 100)

pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
    [[['origin', '=', 'OC11401']]],
    {'fields': ['id', 'name', 'state', 'move_ids']}
)

if pickings:
    print(f"\n📥 Encontrados {len(pickings)} albaranes\n")
    
    for picking in pickings:
        print(f"Albarán: {picking['name']}")
        
        if picking.get('move_ids'):
            moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                [[['id', 'in', picking['move_ids']]]],
                {'fields': [
                    'id', 'product_id', 'quantity_done', 'price_unit',
                    'state', 'purchase_line_id'
                ]}
            )
            
            for move in moves:
                producto = move['product_id'][1] if move['product_id'] else 'N/A'
                precio_actual = move.get('price_unit', 0)
                
                # Buscar si este movimiento está relacionado con la línea incorrecta
                pol_id = move.get('purchase_line_id')
                if pol_id:
                    pol_id = pol_id[0] if isinstance(pol_id, list) else pol_id
                    
                    # Verificar si es la línea con precio 6.5
                    pol = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
                        [[pol_id]], {'fields': ['price_unit']}
                    )
                    
                    # Corregir si viene de la línea que acabamos de corregir
                    if pol and PRODUCTO_CORRECTO in producto:
                        # Solo corregir si el precio parece incorrecto
                        if precio_actual != PRECIO_CORRECTO and move.get('quantity_done', 0) > 0:
                            print(f"  🔧 Corrigiendo movimiento ID {move['id']}: {producto}")
                            print(f"     Cantidad: {move['quantity_done']} kg")
                            print(f"     Precio actual: ${precio_actual:,.2f}")
                            print(f"     Precio nuevo: ${PRECIO_CORRECTO:,.2f}")
                            
                            try:
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
                                        'producto': producto
                                    })
                                else:
                                    print(f"     ❌ ERROR")
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
        print()

# ============================================================================
# PASO 3: CORREGIR CAPAS DE VALORACIÓN
# ============================================================================
print("\n" + "=" * 100)
print("PASO 3: CORRECCIÓN DE CAPAS DE VALORACIÓN")
print("=" * 100)

# Buscar capas relacionadas con el albarán de OC11401
valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
    [[
        ['description', 'ilike', 'RF/Vilk/IN//02313']
    ]],
    {'fields': [
        'id', 'product_id', 'quantity', 'unit_cost', 'value',
        'remaining_qty', 'remaining_value', 'description'
    ], 'limit': 10}
)

if valuation_layers:
    print(f"\n📉 Encontradas {len(valuation_layers)} capas de valoración\n")
    
    for vl in valuation_layers:
        producto = vl['product_id'][1] if vl['product_id'] else 'N/A'
        
        if PRODUCTO_CORRECTO in producto and vl['unit_cost'] != PRECIO_CORRECTO:
            cantidad = vl['quantity']
            costo_actual = vl['unit_cost']
            nuevo_valor = cantidad * PRECIO_CORRECTO
            
            print(f"🔧 Corrigiendo capa ID {vl['id']}: {producto}")
            print(f"   Cantidad: {cantidad} kg")
            print(f"   Costo actual: ${costo_actual:,.2f}")
            print(f"   Costo nuevo: ${PRECIO_CORRECTO:,.2f}")
            print(f"   Valor actual: ${vl['value']:,.2f}")
            print(f"   Valor nuevo: ${nuevo_valor:,.2f}")
            
            try:
                valores_actualizar = {
                    'unit_cost': PRECIO_CORRECTO,
                    'value': nuevo_valor
                }
                
                if vl.get('remaining_qty', 0) > 0:
                    nuevo_remaining = vl['remaining_qty'] * PRECIO_CORRECTO
                    valores_actualizar['remaining_value'] = nuevo_remaining
                
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
                        'valor_anterior': costo_actual,
                        'producto': producto
                    })
                else:
                    print(f"   ❌ ERROR")
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
    print("\n⚠️ No se encontraron capas de valoración para corregir")

# ============================================================================
# RESUMEN
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN DE EJECUCIÓN")
print("=" * 100)

total_cambios = len(log_cambios['cambios_realizados'])
total_errores = len(log_cambios['errores'])

print(f"""
✅ CAMBIOS REALIZADOS: {total_cambios}
❌ ERRORES ENCONTRADOS: {total_errores}
""")

if total_errores > 0:
    print("⚠️  ERRORES:")
    for error in log_cambios['errores']:
        print(f"  • {error.get('paso', 'N/A')}: {error.get('error', 'N/A')}")

# Verificación final
oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['name', 'amount_total', 'state']}
)

if oc_final:
    print(f"\n📋 OC11401 después de corrección:")
    print(f"   Total: ${oc_final[0]['amount_total']:,.2f}")
    print(f"   Estado: {oc_final[0]['state']}")

# Guardar log
try:
    filename = f'oc11401_ejecucion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_cambios, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Log guardado en: {filename}")
except Exception as e:
    print(f"\n⚠️ No se pudo guardar el log: {e}")

print("\n" + "=" * 100)
if total_errores == 0 and total_cambios > 0:
    print("✅ CORRECCIÓN COMPLETADA EXITOSAMENTE")
else:
    print("⚠️  CORRECCIÓN COMPLETADA - REVISAR LOG")
print("=" * 100)
