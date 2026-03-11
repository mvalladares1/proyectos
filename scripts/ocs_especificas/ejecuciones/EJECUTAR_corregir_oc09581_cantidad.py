#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORREGIR OC09581: Ajustar cantidad 103 kg → 746.65 kg
"""
import xmlrpc.client
import json
from datetime import datetime

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

CANTIDAD_CORRECTA = 746.65

print("=" * 100)
print("⚠️  CORRECCIÓN OC09581")
print("   Ajustar cantidad: 103 kg → 746.65 kg")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

log = {
    'oc': 'OC09581',
    'fecha_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'cambios': []
}

# Buscar OC
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC09581']]],
    {'fields': ['id', 'amount_total'], 'limit': 1}
)

if not oc:
    print("❌ OC09581 no encontrada")
    exit(1)

oc_id = oc[0]['id']
total_antes = oc[0]['amount_total']

print(f"📋 OC09581 (ID: {oc_id})")
print(f"   Total antes: ${total_antes:,.2f}\n")

# Obtener línea de compra
linea = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id], ['product_id.default_code', '=', '101222000']]],
    {'fields': ['id', 'product_id', 'product_qty', 'price_unit', 'price_subtotal'], 'limit': 1}
)

if not linea:
    print("❌ Línea de producto no encontrada")
    exit(1)

linea = linea[0]
linea_id = linea['id']
cantidad_antes = linea['product_qty']
precio_unitario = linea['price_unit']

print(f"🔧 Línea ID {linea_id}: {linea['product_id'][1]}")
print(f"   Cantidad antes: {cantidad_antes} kg")
print(f"   Precio unitario: ${precio_unitario}")
print(f"   Subtotal antes: ${linea['price_subtotal']:,.2f}")
print(f"   → Cambiar cantidad a: {CANTIDAD_CORRECTA} kg")
print(f"   → Subtotal esperado: ${CANTIDAD_CORRECTA * precio_unitario:,.2f}\n")

# PASO 1: Actualizar cantidad en línea de OC
print("=" * 100)
print("PASO 1: ACTUALIZAR CANTIDAD EN LÍNEA DE COMPRA")
print("=" * 100)

try:
    result = models.execute_kw(
        db, uid, password,
        'purchase.order.line', 'write',
        [[linea_id], {'product_qty': CANTIDAD_CORRECTA}]
    )
    
    if result:
        print(f"✅ Línea {linea_id} actualizada")
        log['cambios'].append({
            'modelo': 'purchase.order.line',
            'id': linea_id,
            'campo': 'product_qty',
            'antes': cantidad_antes,
            'despues': CANTIDAD_CORRECTA
        })
    else:
        print(f"❌ ERROR al actualizar línea")
except Exception as e:
    print(f"❌ EXCEPCIÓN: {e}")

# VERIFICACIÓN FINAL
print("\n" + "=" * 100)
print("VERIFICACIÓN FINAL")
print("=" * 100)

oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['amount_total']}
)

linea_final = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
    [[linea_id]], {'fields': ['product_qty', 'price_subtotal']}
)

if oc_final and linea_final:
    total_despues = oc_final[0]['amount_total']
    cantidad_despues = linea_final[0]['product_qty']
    subtotal_despues = linea_final[0]['price_subtotal']
    
    print(f"\n📋 OC09581:")
    print(f"   Total antes: ${total_antes:,.2f}")
    print(f"   Total después: ${total_despues:,.2f}")
    print(f"   Diferencia: ${total_despues - total_antes:,.2f}")
    
    print(f"\n🔧 Línea ID {linea_id}:")
    print(f"   Cantidad: {cantidad_antes} kg → {cantidad_despues} kg")
    print(f"   Subtotal: ${linea['price_subtotal']:,.2f} → ${subtotal_despues:,.2f}")
    print(f"   Correcto: {'✓' if abs(cantidad_despues - CANTIDAD_CORRECTA) < 0.01 else '❌'}")
    
    log['total_antes'] = total_antes
    log['total_despues'] = total_despues
    log['cantidad_antes'] = cantidad_antes
    log['cantidad_despues'] = cantidad_despues

# Guardar log
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'oc09581_cantidad_ejecucion_{timestamp}.json'

with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"\n💾 Log guardado: {log_file}")
print("\n" + "=" * 100)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 100)
