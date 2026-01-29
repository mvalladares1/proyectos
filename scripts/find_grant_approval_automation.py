"""
Script para buscar la automatización exacta que crea actividades "Grant Approval"
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

print("=" * 100)
print("BUSCANDO AUTOMATIZACIÓN QUE CREA 'Grant Approval'")
print("=" * 100)

# Primero, buscar el ID del tipo de actividad "Grant Approval"
activity_types = odoo.search_read(
    'mail.activity.type',
    [['name', '=', 'Grant Approval']],
    ['id', 'name'],
    limit=1
)

if not activity_types:
    print("❌ No se encontró el tipo de actividad 'Grant Approval'")
    sys.exit(1)

grant_approval_type_id = activity_types[0]['id']
print(f"✓ Tipo de actividad 'Grant Approval' encontrado (ID: {grant_approval_type_id})\n")

# Buscar acciones de servidor que usen este tipo de actividad
print("Buscando acciones de servidor que crean actividades 'Grant Approval'...\n")

server_actions = odoo.search_read(
    'ir.actions.server',
    [['activity_type_id', '=', grant_approval_type_id]],
    ['id', 'name', 'model_id', 'state', 'activity_summary', 'activity_user_type', 
     'activity_user_id', 'activity_user_field_name', 'code'],
    limit=50
)

print(f"Acciones encontradas: {len(server_actions)}\n")

for action in server_actions:
    print("=" * 90)
    print(f"🎯 ACCIÓN QUE CREA GRANT APPROVAL:")
    print(f"   ID: {action['id']}")
    print(f"   Nombre: {action.get('name', '')}")
    
    model = action.get('model_id')
    model_name = model[1] if isinstance(model, (list, tuple)) else model
    print(f"   Modelo: {model_name}")
    
    print(f"   Estado: {action.get('state', '')}")
    print(f"   Resumen actividad: {action.get('activity_summary', '')}")
    print(f"   Tipo de usuario: {action.get('activity_user_type', '')}")
    
    if action.get('activity_user_id'):
        user = action.get('activity_user_id')
        user_name = user[1] if isinstance(user, (list, tuple)) else user
        print(f"   Usuario específico: {user_name}")
    
    if action.get('activity_user_field_name'):
        print(f"   Campo de usuario: {action.get('activity_user_field_name', '')}")
    
    if action.get('code'):
        print(f"\n   Código Python:")
        print("   " + "─" * 85)
        for line in action.get('code', '').split('\n'):
            print(f"   {line}")
    
    # Ahora buscar qué automatización usa esta acción
    print(f"\n   Buscando automatizaciones que usan esta acción...")
    
    # Buscar en base.automation
    automations = odoo.search_read(
        'base.automation',
        [],
        ['id', 'name', 'model_id', 'trigger', 'filter_domain', 'active'],
        limit=200
    )
    
    # Filtrar las que sean del modelo correcto
    related_automations = [a for a in automations if a.get('model_id') and 
                          (isinstance(a['model_id'], (list, tuple)) and 'purchase.order' in a['model_id'][1].lower()
                           if isinstance(a['model_id'], (list, tuple)) else False)]
    
    print(f"\n   Automatizaciones relacionadas con Purchase Order: {len(related_automations)}")
    
    for auto in related_automations:
        # Para cada automatización, necesitamos ver sus child_ids (acciones)
        # Esto requiere leer el registro completo
        auto_detail = odoo.search_read(
            'base.automation',
            [['id', '=', auto['id']]],
            ['id', 'name', 'trigger', 'filter_domain', 'active', 'create_uid'],
            limit=1
        )
        
        if auto_detail:
            detail = auto_detail[0]
            creator = detail.get('create_uid')
            creator_name = creator[1] if isinstance(creator, (list, tuple)) else creator
            
            print(f"\n      {'─' * 80}")
            print(f"      ID: {detail['id']}")
            print(f"      Nombre: {detail.get('name', '')}")
            print(f"      Trigger: {detail.get('trigger', '')}")
            print(f"      Activa: {detail.get('active', False)}")
            print(f"      Creada por: {creator_name}")
            if detail.get('filter_domain'):
                print(f"      Dominio: {detail.get('filter_domain', '')}")

print("\n" + "=" * 100)

# Buscar específicamente automatizaciones de MARCELO JARAMILLO
print("\nAutomatizaciones creadas por MARCELO JARAMILLO CADEGAN:")
print("=" * 100)

# Primero obtener el ID del usuario
users = odoo.search_read(
    'res.users',
    [['name', 'ilike', 'MARCELO JARAMILLO']],
    ['id', 'name'],
    limit=1
)

if users:
    marcelo_id = users[0]['id']
    print(f"Usuario encontrado: {users[0]['name']} (ID: {marcelo_id})\n")
    
    marcelo_automations = odoo.search_read(
        'base.automation',
        [['create_uid', '=', marcelo_id]],
        ['id', 'name', 'model_id', 'trigger', 'active', 'filter_domain'],
        limit=50
    )
    
    print(f"Total automatizaciones creadas: {len(marcelo_automations)}\n")
    
    for auto in marcelo_automations:
        model = auto.get('model_id')
        model_name = model[1] if isinstance(model, (list, tuple)) else model
        
        print(f"{'─' * 90}")
        print(f"ID: {auto['id']}")
        print(f"Nombre: {auto.get('name', '')}")
        print(f"Modelo: {model_name}")
        print(f"Trigger: {auto.get('trigger', '')}")
        print(f"Activa: {auto.get('active', False)}")
        if auto.get('filter_domain'):
            print(f"Dominio: {auto.get('filter_domain', '')}")
        print()

print("\n" + "=" * 100)
print("DONE")
print("=" * 100)
