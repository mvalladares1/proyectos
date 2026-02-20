"""
Script de diagnóstico: OCs de fletes sin ruta asignada
Analiza qué OCs no tienen correlativo de ruta (RT00XXX) y por qué
"""

import xmlrpc.client
import requests
import json
from typing import List, Dict, Optional

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
API_LOGISTICA_RUTAS = 'https://riofuturoprocesos.com/api/logistica/db/rutas'

# Credenciales
username = input("Usuario Odoo (email): ").strip()
password = input("Contraseña: ").strip()

print("\n" + "="*80)
print("DIAGNÓSTICO: OCs de Fletes sin Ruta")
print("="*80 + "\n")

# 1. Conectar a Odoo
print("📡 Conectando a Odoo...")
try:
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, username, password, {})
    if not uid:
        print("❌ Error de autenticación")
        exit(1)
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    print(f"✅ Conectado como UID: {uid}\n")
except Exception as e:
    print(f"❌ Error de conexión: {e}")
    exit(1)

# 2. Obtener rutas de logística
print("📡 Obteniendo rutas del sistema de logística...")
try:
    response = requests.get(API_LOGISTICA_RUTAS, timeout=10)
    if response.status_code == 200:
        rutas_logistica = response.json()
        print(f"✅ {len(rutas_logistica)} rutas cargadas\n")
    else:
        print(f"⚠️  Error al obtener rutas: status {response.status_code}")
        rutas_logistica = []
except Exception as e:
    print(f"⚠️  Error al conectar con sistema de logística: {e}")
    rutas_logistica = []

# 3. Crear índice de rutas por nombre de OC
rutas_por_oc = {}
ocs_en_rutas = set()
for ruta in rutas_logistica:
    oc_name = ruta.get('purchase_order_name')
    if oc_name:
        rutas_por_oc[oc_name] = ruta
        ocs_en_rutas.add(oc_name)

print(f"📊 Rutas indexadas por purchase_order_name: {len(rutas_por_oc)}\n")

# 4. Obtener OCs de fletes de Odoo
print("📡 Obteniendo OCs de fletes de Odoo...")
try:
    ocs = models.execute_kw(
        DB, uid, password,
        'purchase.order', 'search_read',
        [[
            ('x_studio_categora_de_producto', '=', 'SERVICIOS'),
            ('state', '!=', 'cancel')
        ]],
        {'fields': ['id', 'name', 'state', 'partner_id', 'amount_untaxed', 
                   'x_studio_selection_field_yUNPd', 'date_order'],
         'limit': 1000,
         'order': 'date_order desc'}
    )
    
    # Filtrar solo TRANSPORTES
    ocs_fletes = []
    for oc in ocs:
        area = oc.get('x_studio_selection_field_yUNPd')
        if area and isinstance(area, (list, tuple)):
            area = area[1]
        
        if not area or 'TRANSPORTES' not in str(area).upper():
            continue
        
        ocs_fletes.append(oc)
    
    print(f"✅ {len(ocs_fletes)} OCs de fletes encontradas\n")
    
except Exception as e:
    print(f"❌ Error al obtener OCs: {e}")
    exit(1)

# 5. Analizar OCs sin ruta
print("="*80)
print("ANÁLISIS: OCs sin Ruta")
print("="*80 + "\n")

sin_ruta = []
con_ruta = []

for oc in ocs_fletes:
    oc_name = oc['name']
    tiene_ruta = oc_name in rutas_por_oc
    
    if tiene_ruta:
        ruta_info = rutas_por_oc[oc_name]
        con_ruta.append({
            'oc_name': oc_name,
            'route_correlativo': ruta_info.get('name', 'N/A'),
            'monto': oc.get('amount_untaxed', 0),
            'proveedor': oc['partner_id'][1] if isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
        })
    else:
        sin_ruta.append({
            'oc_name': oc_name,
            'monto': oc.get('amount_untaxed', 0),
            'estado': oc.get('state', 'N/A'),
            'proveedor': oc['partner_id'][1] if isinstance(oc['partner_id'], (list, tuple)) else 'N/A',
            'fecha': oc.get('date_order', 'N/A')
        })

print(f"📊 RESUMEN:")
print(f"   Total OCs de fletes: {len(ocs_fletes)}")
print(f"   ✅ Con ruta: {len(con_ruta)} ({len(con_ruta)/len(ocs_fletes)*100:.1f}%)")
print(f"   ❌ Sin ruta: {len(sin_ruta)} ({len(sin_ruta)/len(ocs_fletes)*100:.1f}%)")
print()

# Mostrar OCs sin ruta
if sin_ruta:
    print("="*80)
    print(f"OCs SIN RUTA ({len(sin_ruta)} total)")
    print("="*80)
    
    # Ordenar por fecha descendente
    sin_ruta_sorted = sorted(sin_ruta, key=lambda x: x['fecha'], reverse=True)
    
    for idx, oc in enumerate(sin_ruta_sorted[:20], 1):  # Mostrar primeras 20
        print(f"\n{idx}. {oc['oc_name']}")
        print(f"   Proveedor: {oc['proveedor'][:50]}")
        print(f"   Monto: ${oc['monto']:,.0f}")
        print(f"   Estado: {oc['estado']}")
        print(f"   Fecha: {oc['fecha']}")
    
    if len(sin_ruta) > 20:
        print(f"\n... y {len(sin_ruta) - 20} más")

# Mostrar muestra de OCs con ruta (para verificar formato)
if con_ruta:
    print("\n" + "="*80)
    print(f"MUESTRA: OCs CON RUTA (primeras 10)")
    print("="*80)
    
    for idx, oc in enumerate(con_ruta[:10], 1):
        print(f"\n{idx}. {oc['oc_name']} → {oc['route_correlativo']}")
        print(f"   Proveedor: {oc['proveedor'][:50]}")
        print(f"   Monto: ${oc['monto']:,.0f}")

# Verificar si hay rutas "huérfanas" (en logística pero no en Odoo)
print("\n" + "="*80)
print("RUTAS HUÉRFANAS (en Logística pero no en Odoo)")
print("="*80 + "\n")

ocs_odoo = {oc['name'] for oc in ocs_fletes}
rutas_huerfanas = ocs_en_rutas - ocs_odoo

if rutas_huerfanas:
    print(f"⚠️  {len(rutas_huerfanas)} rutas encontradas:")
    for idx, oc_name in enumerate(sorted(rutas_huerfanas)[:20], 1):
        ruta_info = rutas_por_oc[oc_name]
        print(f"{idx}. {oc_name} → {ruta_info.get('name', 'N/A')}")
    
    if len(rutas_huerfanas) > 20:
        print(f"... y {len(rutas_huerfanas) - 20} más")
else:
    print("✅ No hay rutas huérfanas")

print("\n" + "="*80)
print("FIN DEL DIAGNÓSTICO")
print("="*80)
