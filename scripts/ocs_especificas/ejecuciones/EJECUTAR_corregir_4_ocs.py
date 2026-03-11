#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CORRECCIÓN DE 4 OCs:
- OC12755: Precio $0→$2,000 + cantidad 110→138.480
- OC13491: Precio $3,400→$3,300 + cantidad 5,015→4,975.760
- OC13530: Precio $3,400→$3,300 + cantidad 4,730→4,566.060
- OC13596: Precio $3,400→$3,300 + cantidad 3,125→3,104.160
"""
import xmlrpc.client
import json
from datetime import datetime

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Configuración de correcciones
CORRECCIONES = {
    'OC12755': {
        'linea_id': 20854,
        'precio_nuevo': 2000.0,
        'cantidad_nueva': 138.480
    },
    'OC13491': {
        'linea_id': 22232,
        'precio_nuevo': 3300.0,
        'cantidad_nueva': 4975.760
    },
    'OC13530': {
        'linea_id': 22289,
        'precio_nuevo': 3300.0,
        'cantidad_nueva': 4566.060
    },
    'OC13596': {
        'linea_id': 22372,
        'precio_nuevo': 3300.0,
        'cantidad_nueva': 3104.160
    }
}

print("=" * 100)
print("⚠️  CORRECCIÓN DE 4 OCs")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

log = {
    'fecha_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'ocs': {}
}

for oc_name, config in CORRECCIONES.items():
    print("=" * 100)
    print(f"PROCESANDO: {oc_name}")
    print("=" * 100)
    
    linea_id = config['linea_id']
    precio_nuevo = config['precio_nuevo']
    cantidad_nueva = config['cantidad_nueva']
    
    # Obtener datos actuales
    linea = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
        [[linea_id]],
        {'fields': ['id', 'order_id', 'product_id', 'product_qty', 'price_unit', 'price_subtotal']}
    )
    
    if not linea:
        print(f"❌ Línea {linea_id} no encontrada\n")
        continue
    
    linea = linea[0]
    cantidad_antes = linea['product_qty']
    precio_antes = linea['price_unit']
    subtotal_antes = linea['price_subtotal']
    
    print(f"\n🔧 Línea ID {linea_id}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"   Cantidad: {cantidad_antes:,.3f} → {cantidad_nueva:,.3f}")
    print(f"   Precio: ${precio_antes:,.2f} → ${precio_nuevo:,.2f}")
    print(f"   Subtotal antes: ${subtotal_antes:,.2f}")
    print(f"   Subtotal esperado: ${cantidad_nueva * precio_nuevo:,.2f}")
    
    # ACTUALIZAR LÍNEA
    try:
        result = models.execute_kw(
            db, uid, password,
            'purchase.order.line', 'write',
            [[linea_id], {
                'product_qty': cantidad_nueva,
                'price_unit': precio_nuevo
            }]
        )
        
        if result:
            print(f"   ✅ ACTUALIZADO")
            
            # Verificar
            linea_nueva = models.execute_kw(db, uid, password, 'purchase.order.line', 'read',
                [[linea_id]],
                {'fields': ['product_qty', 'price_unit', 'price_subtotal']}
            )
            
            if linea_nueva:
                linea_nueva = linea_nueva[0]
                subtotal_nuevo = linea_nueva['price_subtotal']
                
                print(f"   Cantidad verificada: {linea_nueva['product_qty']:,.3f} ✓")
                print(f"   Precio verificado: ${linea_nueva['price_unit']:,.2f} ✓")
                print(f"   Subtotal nuevo: ${subtotal_nuevo:,.2f}")
                
                log['ocs'][oc_name] = {
                    'linea_id': linea_id,
                    'cantidad_antes': cantidad_antes,
                    'cantidad_despues': linea_nueva['product_qty'],
                    'precio_antes': precio_antes,
                    'precio_despues': linea_nueva['price_unit'],
                    'subtotal_antes': subtotal_antes,
                    'subtotal_despues': subtotal_nuevo,
                    'diferencia': subtotal_nuevo - subtotal_antes
                }
        else:
            print(f"   ❌ ERROR")
            
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN: {e}")
    
    print()

# VERIFICACIÓN FINAL DE TODAS LAS OCs
print("=" * 100)
print("VERIFICACIÓN FINAL")
print("=" * 100)

for oc_name in CORRECCIONES.keys():
    oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
        [[['name', '=', oc_name]]],
        {'fields': ['id', 'amount_total'], 'limit': 1}
    )
    
    if oc:
        print(f"\n📋 {oc_name}:")
        print(f"   Total: ${oc[0]['amount_total']:,.2f}")
        
        if oc_name in log['ocs']:
            log['ocs'][oc_name]['total_oc'] = oc[0]['amount_total']

# Guardar log
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
log_file = f'correccion_4_ocs_{timestamp}.json'

with open(log_file, 'w', encoding='utf-8') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)

print(f"\n💾 Log guardado: {log_file}")
print("\n" + "=" * 100)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 100)
