"""
Script para investigar la automatización específica que crea actividades de aprobación.
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

# Buscar automatizaciones base que puedan crear actividades
print("=" * 100)
print("AUTOMATIZACIONES QUE CREAN ACTIVIDADES")
print("=" * 100)

automations = odoo.search_read(
    'base.automation',
    [['model_id.model', '=', 'purchase.order']],
    ['id', 'name', 'trigger', 'filter_domain', 'active', 'state', 'action_server_ids'],
    limit=100
)

print(f"\nTotal automatizaciones: {len(automations)}\n")

for auto in automations:
    print(f"{'='*90}")
    print(f"ID: {auto['id']}")
    print(f"Nombre: {auto.get('name', '')}")
    print(f"Trigger: {auto.get('trigger', '')}")
    print(f"Activa: {auto.get('active', False)}")
    print(f"Estado: {auto.get('state', '')}")
    if auto.get('filter_domain'):
        print(f"Dominio: {auto.get('filter_domain', '')}")
    
    # Buscar acciones asociadas
    action_ids = auto.get('action_server_ids', [])
    if action_ids:
        print(f"\nAcciones asociadas ({len(action_ids)}):")
        actions = odoo.search_read(
            'ir.actions.server',
            [['id', 'in', action_ids]],
            ['id', 'name', 'state', 'code', 'activity_type_id', 'activity_summary', 'activity_user_id'],
            limit=50
        )
        
        for act in actions:
            print(f"\n  {'─'*85}")
            print(f"  Acción ID: {act['id']}")
            print(f"  Nombre: {act.get('name', '')}")
            print(f"  Estado: {act.get('state', '')}")
            
            # Si es una actividad
            if act.get('activity_type_id'):
                activity_type = act.get('activity_type_id')
                activity_type_name = activity_type[1] if isinstance(activity_type, (list, tuple)) else activity_type
                print(f"  🔔 CREA ACTIVIDAD: {activity_type_name}")
                print(f"  Resumen: {act.get('activity_summary', '')}")
                
                activity_user = act.get('activity_user_id')
                if activity_user:
                    user_name = activity_user[1] if isinstance(activity_user, (list, tuple)) else activity_user
                    print(f"  Usuario: {user_name}")
            
            # Mostrar código si existe
            if act.get('code'):
                print(f"\n  Código:")
                print("  " + "\n  ".join(act.get('code', '').split('\n')[:20]))  # Primeras 20 líneas
    
    print()

# Buscar también actividades creadas recientemente
print("\n" + "=" * 100)
print("ACTIVIDADES DE APROBACIÓN CREADAS RECIENTEMENTE")
print("=" * 100)

recent_activities = odoo.search_read(
    'mail.activity',
    [
        ['res_model', '=', 'purchase.order'],
        ['activity_type_id.name', 'ilike', 'approval'],
        ['create_date', '>=', '2026-01-29']
    ],
    ['id', 'activity_type_id', 'summary', 'user_id', 'create_uid', 'create_date', 
     'res_id', 'res_name', 'automated'],
    limit=50,
    order='create_date desc'
)

print(f"\nActividades de aprobación hoy: {len(recent_activities)}\n")

for act in recent_activities:
    act_type = act.get('activity_type_id')
    act_type_name = act_type[1] if isinstance(act_type, (list, tuple)) else act_type
    
    user = act.get('user_id')
    user_name = user[1] if isinstance(user, (list, tuple)) else user
    
    creator = act.get('create_uid')
    creator_name = creator[1] if isinstance(creator, (list, tuple)) else creator
    
    print(f"{'─'*90}")
    print(f"OC: {act.get('res_name', '')} (ID: {act.get('res_id', '')})")
    print(f"Tipo: {act_type_name}")
    print(f"Asignada a: {user_name}")
    print(f"Creada por: {creator_name}")
    print(f"Fecha: {act.get('create_date', '')}")
    print(f"¿Automatizada?: {act.get('automated', False)}")
    print()

print("\n" + "=" * 100)
print("DONE")
print("=" * 100)
