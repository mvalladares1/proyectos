"""
Script de debug para verificar datos de fletes en Odoo vs Sistema de Logística
"""

import os
import sys
import xmlrpc.client
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from pprint import pprint

# Cargar variables de entorno
load_dotenv()

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
API_LOGISTICA_RUTAS = 'https://riofuturoprocesos.com/api/logistica/rutas'

def main():
    username = os.getenv('ODOO_USER')
    password = os.getenv('ODOO_PASSWORD')
    
    if not username or not password:
        print("❌ Error: ODOO_USER y ODOO_PASSWORD deben estar en .env")
        return
    
    print("="*80)
    print("🔍 DEBUG: Verificación cruzada Odoo vs Sistema de Logística")
    print("="*80)
    
    # Conectar a Odoo
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, username, password, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    print(f"\n✅ Conectado a Odoo (UID: {uid})")
    
    # OCs a verificar
    ocs_a_verificar = ['OC11981', 'OC09988', 'OC08257']
    
    print(f"\n📋 Verificando OCs: {', '.join(ocs_a_verificar)}\n")
    
    # Obtener rutas del sistema de logística
    print("🌐 Cargando rutas del sistema de logística...")
    try:
        response = requests.get(API_LOGISTICA_RUTAS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            rutas_logistica = data if isinstance(data, list) else data.get('data', [])
            print(f"✅ {len(rutas_logistica)} rutas cargadas\n")
        else:
            print(f"❌ Error HTTP {response.status_code}")
            rutas_logistica = []
    except Exception as e:
        print(f"❌ Error: {e}")
        rutas_logistica = []
    
    # Para cada OC
    for oc_name in ocs_a_verificar:
        print("="*80)
        print(f"🔎 Analizando: {oc_name}")
        print("="*80)
        
        # 1. Buscar OC en Odoo
        print(f"\n📦 ODOO - Buscando {oc_name}...")
        ocs_odoo = models.execute_kw(
            DB, uid, password,
            'purchase.order', 'search_read',
            [[('name', '=', oc_name)]],
            {'fields': ['id', 'name', 'partner_id', 'date_order', 'order_line', 'amount_untaxed', 'state'], 'limit': 1}
        )
        
        if not ocs_odoo:
            print(f"   ❌ No encontrada en Odoo")
            continue
        
        oc = ocs_odoo[0]
        print(f"   ✅ Encontrada:")
        print(f"      ID: {oc['id']}")
        print(f"      Proveedor: {oc['partner_id'][1] if oc.get('partner_id') else 'N/A'}")
        print(f"      Fecha: {oc.get('date_order', 'N/A')}")
        print(f"      Estado: {oc.get('state', 'N/A')}")
        print(f"      Monto: ${oc.get('amount_untaxed', 0):,.0f}")
        print(f"      Líneas: {len(oc.get('order_line', []))}")
        
        # Obtener líneas de OC
        if oc.get('order_line'):
            print(f"\n   📝 Líneas de la OC:")
            lineas = models.execute_kw(
                DB, uid, password,
                'purchase.order.line', 'search_read',
                [[('id', 'in', oc['order_line'])]],
                {'fields': ['name', 'product_id', 'product_qty', 'price_unit', 'price_subtotal']}
            )
            
            for linea in lineas:
                print(f"      • {linea.get('name', 'Sin nombre')[:60]}")
                print(f"        Producto: {linea['product_id'][1] if linea.get('product_id') else 'N/A'}")
                print(f"        Cantidad: {linea.get('product_qty', 0)}")
                print(f"        Precio unitario: ${linea.get('price_unit', 0):,.2f}")
                print(f"        Subtotal: ${linea.get('price_subtotal', 0):,.2f}")
        
        # 2. Buscar en sistema de logística
        print(f"\n🚛 SISTEMA LOGÍSTICA - Buscando {oc_name}...")
        
        rutas_encontradas = []
        for ruta in rutas_logistica:
            # Buscar por diferentes campos posibles
            po_name = ruta.get('purchase_order_name') or ruta.get('po') or ''
            if po_name == oc_name:
                rutas_encontradas.append(ruta)
        
        if not rutas_encontradas:
            print(f"   ❌ No encontrada en Sistema de Logística")
            
            # Buscar parcialmente por si hay variaciones
            print(f"\n   🔍 Buscando coincidencias parciales...")
            coincidencias_parciales = []
            for ruta in rutas_logistica:
                po_name = ruta.get('purchase_order_name') or ruta.get('po') or ''
                if oc_name in po_name or po_name in oc_name:
                    coincidencias_parciales.append((po_name, ruta.get('name', 'N/A')))
            
            if coincidencias_parciales:
                print(f"   ⚠️ Posibles coincidencias parciales:")
                for po, ruta_nombre in coincidencias_parciales[:5]:
                    print(f"      • PO: '{po}' -> Ruta: {ruta_nombre}")
            else:
                print(f"   ❌ Ninguna coincidencia parcial encontrada")
        else:
            print(f"   ✅ Encontrada {len(rutas_encontradas)} ruta(s):")
            
            for idx, ruta in enumerate(rutas_encontradas, 1):
                print(f"\n   📍 Ruta #{idx}:")
                print(f"      Número: {ruta.get('name', 'N/A')}")
                print(f"      PO Campo: {ruta.get('purchase_order_name') or ruta.get('po', 'N/A')}")
                print(f"      Estado: {ruta.get('status', 'N/A')}")
                print(f"      Distancia total: {ruta.get('total_distance_km', 0)} km")
                print(f"      Cantidad total: {ruta.get('total_qnt', 0)} kg")
                print(f"      Fecha creación: {ruta.get('createdAt', 'N/A')[:10] if ruta.get('createdAt') else 'N/A'}")
                
                # Información de rutas (campo routes)
                routes_field = ruta.get('routes', False)
                if routes_field:
                    print(f"\n      📋 Detalles de rutas:")
                    if isinstance(routes_field, str) and routes_field.startswith('['):
                        try:
                            routes_data = json.loads(routes_field)
                            print(f"         Total de rutas: {len(routes_data)}")
                            
                            for r_idx, route_info in enumerate(routes_data[:3], 1):  # Primeras 3
                                print(f"\n         Ruta {r_idx}:")
                                print(f"            Nombre: {route_info.get('name', 'N/A')}")
                                print(f"            Origen: {route_info.get('origin', 'N/A')}")
                                print(f"            Destino: {route_info.get('destination', 'N/A')}")
                                print(f"            Distancia: {route_info.get('distance', 0)} km")
                                print(f"            Tipo costo: {route_info.get('cost_type', 'N/A')}")
                                print(f"            Costo: ${route_info.get('cost', 0):,.0f}")
                        except json.JSONDecodeError as e:
                            print(f"         ⚠️ Error decodificando JSON: {e}")
                            print(f"         Valor raw: {routes_field[:200]}...")
                    else:
                        print(f"         Tipo: {type(routes_field)}")
                        print(f"         Valor: {routes_field}")
                
                # Información de cargas (campo loads)
                loads_field = ruta.get('loads', [])
                if loads_field:
                    print(f"\n      📦 Cargas:")
                    if isinstance(loads_field, list):
                        print(f"         Total cargas: {len(loads_field)}")
                        for l_idx, load in enumerate(loads_field[:3], 1):  # Primeras 3
                            if isinstance(load, dict):
                                print(f"\n         Carga {l_idx}:")
                                print(f"            Cantidad: {load.get('quantity', 0)} kg")
                                print(f"            Producto: {load.get('product', 'N/A')}")
                                print(f"            Origen: {load.get('origin', 'N/A')}")
                    else:
                        print(f"         Tipo: {type(loads_field)}")
                
                # Otros campos relevantes
                print(f"\n      ℹ️ Otros campos:")
                print(f"         Driver: {ruta.get('driver', 'N/A')}")
                print(f"         Vehicle: {ruta.get('vehicle', 'N/A')}")
                print(f"         Total cost: ${ruta.get('total_cost', 0):,.0f}")
        
        print("\n")
    
    # Resumen final
    print("="*80)
    print("📊 RESUMEN")
    print("="*80)
    print(f"\nOCs verificadas: {len(ocs_a_verificar)}")
    print(f"Rutas totales en sistema: {len(rutas_logistica)}")
    
    # Estadísticas del sistema de logística
    print(f"\n📈 Estadísticas del sistema de logística:")
    rutas_con_po = [r for r in rutas_logistica if r.get('purchase_order_name') or r.get('po')]
    rutas_con_distancia = [r for r in rutas_logistica if r.get('total_distance_km', 0) > 0]
    rutas_con_carga = [r for r in rutas_logistica if r.get('total_qnt', 0) > 0]
    
    print(f"   Rutas con PO asignado: {len(rutas_con_po)} ({len(rutas_con_po)/len(rutas_logistica)*100:.1f}%)")
    print(f"   Rutas con distancia: {len(rutas_con_distancia)} ({len(rutas_con_distancia)/len(rutas_logistica)*100:.1f}%)")
    print(f"   Rutas con carga: {len(rutas_con_carga)} ({len(rutas_con_carga)/len(rutas_logistica)*100:.1f}%)")
    
    # Listar algunos POs del sistema de logística para referencia
    print(f"\n📋 Ejemplos de POs en el sistema de logística (últimos 10):")
    pos_unicos = set()
    for ruta in rutas_logistica:
        po_name = ruta.get('purchase_order_name') or ruta.get('po')
        if po_name:
            pos_unicos.add(po_name)
    
    for po in sorted(list(pos_unicos))[-10:]:
        print(f"   • {po}")
    
    print("\n✅ Debug completado\n")


if __name__ == "__main__":
    main()
