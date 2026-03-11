#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REVERTIR Y CORREGIR OC12902:
- Revertir moneda USD → CLP
- Ajustar precio 3,080 → 3,085 (manteniendo CLP)
"""
import xmlrpc.client

# Conexión
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

PRECIO_CORRECTO = 3085.0

print("=" * 100)
print("⚠️  REVERTIR Y CORREGIR OC12902")
print("   1. Revertir moneda USD → CLP")
print("   2. Ajustar precio → $3,085 CLP")
print("=" * 100)

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print(f"\n✅ Conectado\n")

# Obtener ID de moneda CLP
clp_currency = models.execute_kw(db, uid, password, 'res.currency', 'search_read',
    [[['name', '=', 'CLP']]],
    {'fields': ['id'], 'limit': 1}
)

if not clp_currency:
    print("❌ No se encontró moneda CLP")
    exit(1)

CLP_ID = clp_currency[0]['id']
print(f"💵 CLP ID: {CLP_ID}\n")

# Buscar OC12902
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12902']]],
    {'fields': ['id', 'currency_id', 'amount_total'], 'limit': 1}
)

if not oc:
    print("❌ OC12902 no encontrada")
    exit(1)

oc_id = oc[0]['id']

print(f"📋 OC12902 (ID: {oc_id})")
print(f"   Moneda actual: {oc[0]['currency_id'][1] if oc[0]['currency_id'] else 'N/A'}")
print(f"   Total: ${oc[0]['amount_total']:,.2f}")

# PASO 1: Revertir moneda a CLP en la OC
print("\n" + "=" * 100)
print("PASO 1: REVERTIR MONEDA OC A CLP")
print("=" * 100)

try:
    result = models.execute_kw(
        db, uid, password,
        'purchase.order', 'write',
        [[oc_id], {'currency_id': CLP_ID}]
    )
    
    if result:
        print("✅ Moneda de OC revertida a CLP")
    else:
        print("❌ ERROR al revertir moneda")
except Exception as e:
    print(f"❌ EXCEPCIÓN: {e}")

# PASO 2: Revertir moneda y ajustar precio en líneas
print("\n" + "=" * 100)
print("PASO 2: REVERTIR MONEDA Y AJUSTAR PRECIO EN LÍNEAS")
print("=" * 100)

lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['id', 'product_id', 'price_unit', 'currency_id']}
)

for linea in lineas:
    print(f"\n🔧 Línea ID {linea['id']}: {linea['product_id'][1] if linea['product_id'] else 'N/A'}")
    print(f"   Moneda actual: {linea.get('currency_id', [None, 'N/A'])[1] if linea.get('currency_id') else 'N/A'}")
    print(f"   Precio actual: ${linea['price_unit']:,.2f}")
    print(f"   → Cambiar a: CLP, ${PRECIO_CORRECTO:,.2f}")
    
    try:
        result = models.execute_kw(
            db, uid, password,
            'purchase.order.line', 'write',
            [[linea['id']], {
                'currency_id': CLP_ID,
                'price_unit': PRECIO_CORRECTO
            }]
        )
        
        if result:
            print(f"   ✅ ACTUALIZADO")
        else:
            print(f"   ❌ ERROR")
    except Exception as e:
        print(f"   ❌ EXCEPCIÓN: {e}")

# VERIFICACIÓN FINAL
print("\n" + "=" * 100)
print("VERIFICACIÓN FINAL")
print("=" * 100)

oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['currency_id', 'amount_total']}
)

if oc_final:
    print(f"\n📋 OC12902:")
    print(f"   Moneda: {oc_final[0]['currency_id'][1]} {'✓' if oc_final[0]['currency_id'][1] == 'CLP' else '❌'}")
    print(f"   Total: ${oc_final[0]['amount_total']:,.2f}")

lineas_final = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['price_unit', 'currency_id']}
)

if lineas_final:
    precio = lineas_final[0]['price_unit']
    moneda = lineas_final[0].get('currency_id', [None, 'N/A'])[1] if lineas_final[0].get('currency_id') else 'N/A'
    print(f"   Precio línea: ${precio:,.2f} {moneda}")
    print(f"   Correcto: {'✓' if abs(precio - PRECIO_CORRECTO) < 1 and moneda == 'CLP' else '❌'}")

print("\n" + "=" * 100)
print("✅ CORRECCIÓN COMPLETADA")
print("=" * 100)
