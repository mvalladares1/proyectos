"""
Script de debug para verificar por qué no aparece el número de ruta en algunas OCs
"""

import requests
import json

# API de logística
API_LOGISTICA_RUTAS = 'https://riofuturoprocesos.com/api/logistica/rutas'

def obtener_rutas_logistica():
    """Obtiene todas las rutas del sistema de logística"""
    try:
        response = requests.get(API_LOGISTICA_RUTAS, timeout=10)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        print(f"Error al obtener rutas: {e}")
        return []

def buscar_ruta_en_logistica(oc_name, rutas_logistica):
    """Busca la ruta asociada a una OC"""
    for ruta in rutas_logistica:
        # Buscar por purchase_order_name o po
        po_name = ruta.get('purchase_order_name') or ruta.get('po')
        if po_name and po_name == oc_name:
            return ruta
    return None

# Lista de OCs a verificar (las que mostraban N/A)
ocs_a_verificar = [
    'OC12560',
    'OC12559',
    'OC12556',
    'OC12554',
    'OC12553',
    'OC12535',  # Esta mostraba RT00469 en lugar de N/A
    'OC12528',  # Esta mostraba RT00476 en lugar de N/A
]

print("="*80)
print("DEBUG: Analizando números de ruta")
print("="*80)

# Obtener rutas
print("\n1. Obteniendo rutas del sistema de logística...")
rutas_logistica = obtener_rutas_logistica()
print(f"   ✓ {len(rutas_logistica)} rutas obtenidas")

# Filtrar solo las que tienen OC asignada
rutas_con_oc = [r for r in rutas_logistica if r.get('purchase_order_name') or r.get('po')]
print(f"   ✓ {len(rutas_con_oc)} rutas con OC asignada")

print("\n2. Analizando OCs específicas:")
print("-"*80)

for oc_name in ocs_a_verificar:
    print(f"\n📋 OC: {oc_name}")
    
    ruta_info = buscar_ruta_en_logistica(oc_name, rutas_logistica)
    
    if ruta_info:
        print(f"   ✓ Encontrada en sistema de logística")
        print(f"   Campos disponibles: {list(ruta_info.keys())}")
        
        # Mostrar campos relevantes
        print(f"\n   Campos específicos:")
        print(f"   - id: {ruta_info.get('id', 'NO EXISTE')}")
        print(f"   - name: {ruta_info.get('name', 'NO EXISTE')}")
        print(f"   - ruta_name: {ruta_info.get('ruta_name', 'NO EXISTE')}")
        print(f"   - purchase_order_name: {ruta_info.get('purchase_order_name', 'NO EXISTE')}")
        print(f"   - po: {ruta_info.get('po', 'NO EXISTE')}")
        print(f"   - total_distance_km: {ruta_info.get('total_distance_km', 'NO EXISTE')}")
        print(f"   - total_qnt: {ruta_info.get('total_qnt', 'NO EXISTE')}")
        
        # Intentar obtener nombre de ruta desde routes
        routes_field = ruta_info.get('routes', False)
        if routes_field and isinstance(routes_field, str) and routes_field.startswith('['):
            try:
                routes_data = json.loads(routes_field)
                if isinstance(routes_data, list) and len(routes_data) > 0:
                    route_info = routes_data[0]
                    print(f"\n   Info desde campo 'routes':")
                    print(f"   - route_name: {route_info.get('route_name', 'NO EXISTE')}")
                    print(f"   - origin: {route_info.get('origin', 'NO EXISTE')}")
                    print(f"   - destination: {route_info.get('destination', 'NO EXISTE')}")
                    print(f"   - cost_type: {route_info.get('cost_type', 'NO EXISTE')}")
            except Exception as e:
                print(f"   ✗ Error parseando routes: {e}")
        else:
            print(f"   - routes: {routes_field if routes_field else 'NO EXISTE'}")
    else:
        print(f"   ✗ NO encontrada en sistema de logística")

print("\n" + "="*80)
print("Análisis completo")
print("="*80)

# Estadísticas generales
print(f"\nEstadísticas:")
rutas_con_ruta_name = [r for r in rutas_con_oc if r.get('ruta_name')]
print(f"- Rutas con OC: {len(rutas_con_oc)}")
print(f"- Rutas con campo 'ruta_name': {len(rutas_con_ruta_name)}")
print(f"- Porcentaje con ruta_name: {len(rutas_con_ruta_name)/len(rutas_con_oc)*100:.1f}%")
