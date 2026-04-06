#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECCIÓN OC11681 - CAMBIO DE MONEDA CLP → USD
Cambiar la moneda de CLP a USD en la orden de compra y registros relacionados
"""
import xmlrpc.client
import json
from datetime import datetime

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Datos de la corrección (del análisis)
OC_ID = 11690
NOMBRE_OC = "OC11681"
LINEA_ID = 18969
MOVE_ID = 157019
LAYER_ID = 90074

MONEDA_ORIGEN = 45  # CLP
MONEDA_DESTINO = 2  # USD

print("="*80)
print(f"CORRECCIÓN DE OC11681 - CAMBIO DE MONEDA CLP → USD")
print("="*80)

log_ejecucion = {
    'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'oc': NOMBRE_OC,
    'oc_id': OC_ID,
    'tipo_correccion': 'cambio_moneda',
    'moneda_origen': 'CLP',
    'moneda_destino': 'USD',
    'modificaciones': [],
    'errores': []
}

try:
    # Conectar
    common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    
    if not uid:
        raise Exception("❌ Error de autenticación")
    
    models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
    print("✅ Conectado a Odoo\n")
    
    # Verificar que no hay facturas en borrador
    facturas = models.execute_kw(db, uid, password,
        'account.move', 'search_read',
        [[('invoice_origin', '=', NOMBRE_OC), ('state', '=', 'draft')]],
        {'fields': ['id', 'name', 'state']})
    
    if facturas:
        print(f"⚠️  Hay {len(facturas)} factura(s) en borrador. Eliminando...")
        for factura in facturas:
            models.execute_kw(db, uid, password,
                'account.move', 'unlink', [[factura['id']]])
            print(f"   ✓ Eliminada factura {factura['name']} (ID: {factura['id']})")
            log_ejecucion['modificaciones'].append({
                'tipo': 'factura_eliminada',
                'id': factura['id'],
                'nombre': factura['name']
            })
    else:
        print("✓ No hay facturas en borrador\n")
    
    # 1. CAMBIAR MONEDA EN LA ORDEN DE COMPRA
    print(f"1. Cambiando moneda en OC {NOMBRE_OC} (ID: {OC_ID})...")
    
    # Leer estado actual
    oc_antes = models.execute_kw(db, uid, password,
        'purchase.order', 'read',
        [OC_ID],
        {'fields': ['currency_id', 'amount_total']})[0]
    
    # Cambiar moneda
    models.execute_kw(db, uid, password,
        'purchase.order', 'write',
        [[OC_ID], {'currency_id': MONEDA_DESTINO}])
    
    # Verificar
    oc_despues = models.execute_kw(db, uid, password,
        'purchase.order', 'read',
        [OC_ID],
        {'fields': ['currency_id', 'amount_total']})[0]
    
    print(f"   Antes: {oc_antes['currency_id'][1]} (ID: {oc_antes['currency_id'][0]})")
    print(f"   Después: {oc_despues['currency_id'][1]} (ID: {oc_despues['currency_id'][0]})")
    print(f"   Total: ${oc_antes['amount_total']:,.2f} → ${oc_despues['amount_total']:,.2f}\n")
    
    log_ejecucion['modificaciones'].append({
        'tipo': 'purchase_order',
        'id': OC_ID,
        'campo': 'currency_id',
        'antes': oc_antes['currency_id'],
        'despues': oc_despues['currency_id']
    })
    
    # 2. CAMBIAR MONEDA EN LA LÍNEA DE COMPRA
    print(f"2. Cambiando moneda en línea {LINEA_ID}...")
    
    # Leer estado actual
    linea_antes = models.execute_kw(db, uid, password,
        'purchase.order.line', 'read',
        [LINEA_ID],
        {'fields': ['currency_id', 'price_unit', 'price_subtotal']})[0]
    
    # Cambiar moneda
    models.execute_kw(db, uid, password,
        'purchase.order.line', 'write',
        [[LINEA_ID], {'currency_id': MONEDA_DESTINO}])
    
    # Verificar
    linea_despues = models.execute_kw(db, uid, password,
        'purchase.order.line', 'read',
        [LINEA_ID],
        {'fields': ['currency_id', 'price_unit', 'price_subtotal']})[0]
    
    print(f"   Antes: {linea_antes['currency_id'][1]} - Precio: ${linea_antes['price_unit']:,.2f}")
    print(f"   Después: {linea_despues['currency_id'][1]} - Precio: ${linea_despues['price_unit']:,.2f}\n")
    
    log_ejecucion['modificaciones'].append({
        'tipo': 'purchase_order_line',
        'id': LINEA_ID,
        'campo': 'currency_id',
        'antes': linea_antes['currency_id'],
        'despues': linea_despues['currency_id']
    })
    
    # 3. CAMBIAR MONEDA EN LA CAPA DE VALORACIÓN
    print(f"3. Cambiando moneda en capa de valoración {LAYER_ID}...")
    
    # Leer estado actual
    layer_antes = models.execute_kw(db, uid, password,
        'stock.valuation.layer', 'read',
        [LAYER_ID],
        {'fields': ['currency_id', 'unit_cost', 'value']})[0]
    
    # Cambiar moneda
    models.execute_kw(db, uid, password,
        'stock.valuation.layer', 'write',
        [[LAYER_ID], {'currency_id': MONEDA_DESTINO}])
    
    # Verificar
    layer_despues = models.execute_kw(db, uid, password,
        'stock.valuation.layer', 'read',
        [LAYER_ID],
        {'fields': ['currency_id', 'unit_cost', 'value']})[0]
    
    print(f"   Antes: {layer_antes['currency_id'][1]} - Costo: ${layer_antes['unit_cost']:,.2f}, Valor: ${layer_antes['value']:,.2f}")
    print(f"   Después: {layer_despues['currency_id'][1]} - Costo: ${layer_despues['unit_cost']:,.2f}, Valor: ${layer_despues['value']:,.2f}\n")
    
    log_ejecucion['modificaciones'].append({
        'tipo': 'stock_valuation_layer',
        'id': LAYER_ID,
        'campo': 'currency_id',
        'antes': layer_antes['currency_id'],
        'despues': layer_despues['currency_id']
    })
    
    # RESUMEN FINAL
    print("="*80)
    print("✅ CORRECCIÓN COMPLETADA")
    print("="*80)
    print(f"OC: {NOMBRE_OC}")
    print(f"Cambio de moneda: CLP → USD")
    print(f"Modificaciones realizadas: {len(log_ejecucion['modificaciones'])}")
    print(f"  • 1 Purchase Order (currency_id)")
    print(f"  • 1 Purchase Order Line (currency_id)")
    print(f"  • 1 Stock Valuation Layer (currency_id)")
    
    # Guardar log
    log_filename = f"oc11681_moneda_20260312_{datetime.now().strftime('%H%M%S')}.json"
    with open(log_filename, 'w', encoding='utf-8') as f:
        json.dump(log_ejecucion, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Log guardado: {log_filename}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    log_ejecucion['errores'].append(str(e))
    import traceback
    traceback.print_exc()
    
    # Guardar log de error
    log_filename = f"oc11681_moneda_ERROR_20260312_{datetime.now().strftime('%H%M%S')}.json"
    with open(log_filename, 'w', encoding='utf-8') as f:
        json.dump(log_ejecucion, f, indent=2, ensure_ascii=False)
    print(f"\n💾 Log de error guardado: {log_filename}")
