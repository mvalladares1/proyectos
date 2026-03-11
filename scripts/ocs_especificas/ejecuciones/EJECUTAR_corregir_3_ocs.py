#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EJECUCIÓN REAL: Corrección de OC12902, OC09581, OC12363
- OC12902: Precio 3.080 → 3.085 y moneda CLP → USD (SIN FACTURAS)
- OC09581: Moneda CLP → USD, precio 2.3 (CON FACTURAS - solo cambio moneda)
- OC12363: Moneda CLP → USD, precio 1.6 (CON FACTURAS - solo cambio moneda)
"""
import xmlrpc.client
from datetime import datetime
import json

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("⚠️  EJECUCIÓN REAL: CORRECCIÓN DE 3 OCs")
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
    'usuario': username,
    'ocs_corregidas': [],
    'errores': []
}

# Obtener ID de moneda USD
usd_currency = models.execute_kw(db, uid, password, 'res.currency', 'search_read',
    [[['name', '=', 'USD']]],
    {'fields': ['id', 'name'], 'limit': 1}
)

if not usd_currency:
    print("❌ No se encontró moneda USD")
    exit(1)

USD_ID = usd_currency[0]['id']
print(f"💵 Moneda USD ID: {USD_ID}\n")

# ============================================================================
# CONFIGURACIÓN DE OCs A CORREGIR
# ============================================================================
OCS_CORREGIR = [
    {
        'nombre': 'OC12902',
        'precio_correcto': 3.085,
        'precio_actual': 3.080,
        'cambiar_precio': True,
        'cambiar_moneda': True,
        'tiene_facturas': False
    },
    {
        'nombre': 'OC09581',
        'precio_correcto': 2.3,
        'precio_actual': 2.3,
        'cambiar_precio': False,
        'cambiar_moneda': True,
        'tiene_facturas': True
    },
    {
        'nombre': 'OC12363',
        'precio_correcto': 1.6,
        'precio_actual': 1.6,
        'cambiar_precio': False,
        'cambiar_moneda': True,
        'tiene_facturas': True
    }
]

# ============================================================================
# PROCESAR CADA OC
# ============================================================================
for oc_config in OCS_CORREGIR:
    print("\n" + "=" * 100)
    print(f"PROCESANDO: {oc_config['nombre']}")
    print("=" * 100)
    
    # Buscar OC
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_config['nombre']]]],
        {'fields': [
            'id', 'name', 'state', 'currency_id', 'amount_total',
            'invoice_ids', 'picking_ids', 'order_line'
        ], 'limit': 1}
    )
    
    if not oc:
        print(f"❌ {oc_config['nombre']} no encontrada")
        log_cambios['errores'].append({
            'oc': oc_config['nombre'],
            'error': 'OC no encontrada'
        })
        continue
    
    oc = oc[0]
    oc_id = oc['id']
    
    print(f"\n📋 OC ID: {oc_id}")
    print(f"   Estado: {oc['state']}")
    print(f"   Moneda actual: {oc['currency_id'][1] if oc['currency_id'] else 'N/A'}")
    print(f"   Total actual: ${oc['amount_total']:,.2f}")
    
    cambios_oc = {
        'oc': oc_config['nombre'],
        'oc_id': oc_id,
        'cambios': []
    }
    
    # ========================================================================
    # PASO 1: CAMBIAR MONEDA DE LA OC (si aplica)
    # ========================================================================
    if oc_config['cambiar_moneda']:
        print(f"\n🔧 CAMBIO DE MONEDA:")
        print(f"   {oc['currency_id'][1]} → USD")
        
        try:
            result = models.execute_kw(
                db, uid, password,
                'purchase.order', 'write',
                [[oc_id], {'currency_id': USD_ID}]
            )
            
            if result:
                print(f"   ✅ Moneda actualizada a USD")
                cambios_oc['cambios'].append({
                    'paso': 'cambio_moneda_oc',
                    'campo': 'currency_id',
                    'valor_anterior': oc['currency_id'][1] if oc['currency_id'] else 'N/A',
                    'valor_nuevo': 'USD'
                })
            else:
                print(f"   ❌ ERROR al cambiar moneda")
                log_cambios['errores'].append({
                    'oc': oc_config['nombre'],
                    'paso': 'cambio_moneda',
                    'error': 'write retornó False'
                })
        except Exception as e:
            print(f"   ❌ EXCEPCIÓN: {e}")
            log_cambios['errores'].append({
                'oc': oc_config['nombre'],
                'paso': 'cambio_moneda',
                'error': str(e)
            })
    
    # ========================================================================
    # PASO 2: CORREGIR PRECIO EN LÍNEAS (si aplica)
    # ========================================================================
    lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
        [[['order_id', '=', oc_id]]],
        {'fields': ['id', 'product_id', 'price_unit', 'product_qty', 'qty_invoiced']}
    )
    
    for linea in lineas:
        valores_actualizar = {}
        
        # Cambiar precio si aplica
        if oc_config['cambiar_precio'] and abs(linea['price_unit'] - oc_config['precio_actual']) < 0.01:
            print(f"\n🔧 LÍNEA ID {linea['id']}:")
            print(f"   Producto: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
            print(f"   Precio: ${linea['price_unit']:,.4f} → ${oc_config['precio_correcto']:,.4f}")
            valores_actualizar['price_unit'] = oc_config['precio_correcto']
        
        # Cambiar moneda de la línea
        if oc_config['cambiar_moneda']:
            valores_actualizar['currency_id'] = USD_ID
        
        # Resetear qty_invoiced si tiene facturas (para OCs complejas no lo hacemos)
        if not oc_config['tiene_facturas'] and linea.get('qty_invoiced', 0) > 0:
            print(f"   Reseteando qty_invoiced: {linea['qty_invoiced']} → 0")
            valores_actualizar['qty_invoiced'] = 0
        
        if valores_actualizar:
            try:
                result = models.execute_kw(
                    db, uid, password,
                    'purchase.order.line', 'write',
                    [[linea['id']], valores_actualizar]
                )
                
                if result:
                    print(f"   ✅ Línea actualizada")
                    cambios_oc['cambios'].append({
                        'paso': 'actualizar_linea',
                        'linea_id': linea['id'],
                        'cambios': valores_actualizar
                    })
                else:
                    print(f"   ❌ ERROR")
                    log_cambios['errores'].append({
                        'oc': oc_config['nombre'],
                        'linea_id': linea['id'],
                        'error': 'write retornó False'
                    })
            except Exception as e:
                print(f"   ❌ EXCEPCIÓN: {e}")
                log_cambios['errores'].append({
                    'oc': oc_config['nombre'],
                    'linea_id': linea['id'],
                    'error': str(e)
                })
    
    # ========================================================================
    # PASO 3: ACTUALIZAR MOVIMIENTOS DE STOCK (si aplica)
    # ========================================================================
    picking_ids = oc.get('picking_ids', [])
    if picking_ids and (oc_config['cambiar_precio'] or oc_config['cambiar_moneda']):
        pickings = models.execute_kw(db, uid, password, 'stock.picking', 'search_read',
            [[['id', 'in', picking_ids]]],
            {'fields': ['id', 'name', 'move_ids']}
        )
        
        for picking in pickings:
            if picking.get('move_ids'):
                moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
                    [[['id', 'in', picking['move_ids']]]],
                    {'fields': ['id', 'price_unit', 'quantity_done', 'purchase_line_id']}
                )
                
                for move in moves:
                    if move.get('quantity_done', 0) > 0:
                        valores_move = {}
                        
                        if oc_config['cambiar_precio'] and abs(move['price_unit'] - oc_config['precio_actual']) < 0.01:
                            valores_move['price_unit'] = oc_config['precio_correcto']
                        
                        if valores_move:
                            try:
                                result = models.execute_kw(
                                    db, uid, password,
                                    'stock.move', 'write',
                                    [[move['id']], valores_move]
                                )
                                
                                if result:
                                    cambios_oc['cambios'].append({
                                        'paso': 'actualizar_stock_move',
                                        'move_id': move['id'],
                                        'cambios': valores_move
                                    })
                            except Exception as e:
                                log_cambios['errores'].append({
                                    'oc': oc_config['nombre'],
                                    'move_id': move['id'],
                                    'error': str(e)
                                })
    
    # ========================================================================
    # PASO 4: ACTUALIZAR CAPAS DE VALORACIÓN (si aplica cambio de precio)
    # ========================================================================
    if oc_config['cambiar_precio'] and picking_ids:
        # Buscar capas relacionadas con esta OC
        try:
            valuation_layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
                [[
                    ['create_date', '>=', '2026-03-01'],
                    ['unit_cost', '=', oc_config['precio_actual']]
                ]],
                {'fields': ['id', 'product_id', 'quantity', 'unit_cost', 'value', 'description'], 'limit': 20}
            )
            
            for vl in valuation_layers:
                if oc_config['nombre'] in str(vl.get('description', '')):
                    nuevo_valor = vl['quantity'] * oc_config['precio_correcto']
                    
                    try:
                        result = models.execute_kw(
                            db, uid, password,
                            'stock.valuation.layer', 'write',
                            [[vl['id']], {
                                'unit_cost': oc_config['precio_correcto'],
                                'value': nuevo_valor
                            }]
                        )
                        
                        if result:
                            cambios_oc['cambios'].append({
                                'paso': 'actualizar_valuation_layer',
                                'layer_id': vl['id'],
                                'cambios': {
                                    'unit_cost': oc_config['precio_correcto'],
                                    'value': nuevo_valor
                                }
                            })
                    except Exception as e:
                        log_cambios['errores'].append({
                            'oc': oc_config['nombre'],
                            'layer_id': vl['id'],
                            'error': str(e)
                        })
        except Exception as e:
            print(f"   ⚠️ No se pudieron actualizar capas de valoración: {e}")
    
    # Verificar resultado final
    oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
        [[oc_id]], {'fields': ['amount_total', 'currency_id']}
    )
    
    if oc_final:
        print(f"\n📊 RESULTADO:")
        print(f"   Moneda: {oc_final[0]['currency_id'][1] if oc_final[0]['currency_id'] else 'N/A'}")
        print(f"   Total: ${oc_final[0]['amount_total']:,.2f}")
    
    log_cambios['ocs_corregidas'].append(cambios_oc)

# ============================================================================
# RESUMEN FINAL
# ============================================================================
print("\n" + "=" * 100)
print("RESUMEN FINAL")
print("=" * 100)

print(f"\n✅ OCs procesadas: {len(log_cambios['ocs_corregidas'])}")
print(f"❌ Errores: {len(log_cambios['errores'])}")

for oc_corregida in log_cambios['ocs_corregidas']:
    print(f"\n{oc_corregida['oc']}: {len(oc_corregida['cambios'])} cambios realizados")

if log_cambios['errores']:
    print("\n⚠️  ERRORES:")
    for error in log_cambios['errores']:
        print(f"  • {error}")

# Guardar log
try:
    filename = f'correccion_3_ocs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(log_cambios, f, indent=2, ensure_ascii=False)
    print(f"\n✅ Log guardado en: {filename}")
except Exception as e:
    print(f"\n⚠️ No se pudo guardar el log: {e}")

print("\n" + "=" * 100)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 100)
