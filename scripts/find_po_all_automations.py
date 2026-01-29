"""
Buscar TODAS las automatizaciones de purchase.order y ver sus acciones
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("Conectando a Odoo...")
odoo = OdooClient(username=USERNAME, password=PASSWORD)
print("✓ Conectado\n")

# Buscar modelo purchase.order
models = odoo.search_read(
    'ir.model',
    [['model', '=', 'purchase.order']],
    ['id', 'name', 'model'],
    limit=1
)

if not models:
    print("❌ Modelo purchase.order no encontrado")
    sys.exit(1)

model_id = models[0]['id']
print(f"✓ Modelo 'purchase.order' encontrado (ID: {model_id})\n")

# Buscar TODAS las automatizaciones de este modelo
print("=" * 100)
print("TODAS LAS AUTOMATIZACIONES DE PURCHASE.ORDER")
print("=" * 100)

automations = odoo.search_read(
    'base.automation',
    [['model_id', '=', model_id]],
    ['id', 'name', 'trigger', 'active', 'filter_domain', 'create_uid', 'state'],
    limit=100
)

print(f"\nTotal automatizaciones: {len(automations)}\n")

for auto in automations:
    creator = auto.get('create_uid')
    creator_name = creator[1] if isinstance(creator, (list, tuple)) else creator
    
    print("=" * 90)
    print(f"ID: {auto['id']}")
    print(f"Nombre: {auto.get('name', '')}")
    print(f"Trigger: {auto.get('trigger', '')}")
    print(f"Estado: {auto.get('state', '')}")
    print(f"Activa: {auto.get('active', False)}")
    print(f"Creada por: {creator_name}")
    
    if auto.get('filter_domain'):
        print(f"Dominio: {auto.get('filter_domain', '')}")
    
    # Intentar leer las acciones child (a veces están en child_ids o action_server_id)
    # Leer el registro completo para ver qué campos tiene
    try:
        full_auto = odoo.models.execute_kw(
            odoo.db, odoo.uid, odoo.password,
            'base.automation', 'read',
            [[auto['id']]],
            {}
        )
        
        if full_auto:
            record = full_auto[0]
            
            # Buscar campos que puedan contener acciones
            action_fields = ['action_server_id', 'child_ids', 'server_action_ids']
            
            for field in action_fields:
                if field in record and record[field]:
                    action_id = None
                    if isinstance(record[field], (list, tuple)):
                        if len(record[field]) > 0:
                            if isinstance(record[field][0], int):
                                action_id = record[field][0]
                            else:
                                action_id = record[field]
                    elif isinstance(record[field], int):
                        action_id = record[field]
                    
                    if action_id:
                        print(f"\n   Tiene campo '{field}': {action_id}")
                        
                        # Leer la acción
                        if isinstance(action_id, (list, tuple)):
                            action_ids = action_id
                        else:
                            action_ids = [action_id]
                        
                        try:
                            actions = odoo.search_read(
                                'ir.actions.server',
                                [['id', 'in', action_ids]],
                                ['id', 'name', 'state', 'activity_type_id', 'activity_summary',
                                 'activity_user_type', 'activity_user_id', 'code'],
                                limit=10
                            )
                            
                            for act in actions:
                                print(f"\n      Acción ID: {act['id']}")
                                print(f"      Nombre: {act.get('name', '')}")
                                print(f"      Tipo: {act.get('state', '')}")
                                
                                if act.get('activity_type_id'):
                                    activity_type = act.get('activity_type_id')
                                    activity_type_name = activity_type[1] if isinstance(activity_type, (list, tuple)) else activity_type
                                    print(f"      🎯 CREA ACTIVIDAD: {activity_type_name}")
                                    
                                    if act.get('activity_summary'):
                                        print(f"      Resumen: {act.get('activity_summary', '')}")
                                    
                                    if act.get('activity_user_type'):
                                        print(f"      Tipo usuario: {act.get('activity_user_type', '')}")
                                    
                                    if act.get('activity_user_id'):
                                        user = act.get('activity_user_id')
                                        user_name = user[1] if isinstance(user, (list, tuple)) else user
                                        print(f"      Usuario: {user_name}")
                                
                                if act.get('code'):
                                    print(f"\n      Código (primeras 500 chars):")
                                    print("      " + act.get('code', '')[:500].replace('\n', '\n      '))
                        except Exception as e:
                            print(f"      Error al leer acción: {e}")
    except Exception as e:
        print(f"   Error al leer detalles: {e}")
    
    print()

print("\n" + "=" * 100)
print("DONE")
print("=" * 100)
