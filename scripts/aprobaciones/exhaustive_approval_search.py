"""
Búsqueda exhaustiva de qué crea actividades Grant Approval en Purchase Orders
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("Conectando...")
odoo = OdooClient(username=USERNAME, password=PASSWORD)
print("OK\n")

# 1. Buscar campos custom (x_studio) en purchase.order que puedan gatillar aprobaciones
print("=" * 100)
print("1. CAMPOS CUSTOM (x_studio_*) EN PURCHASE.ORDER")
print("=" * 100)

try:
    fields = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'ir.model.fields', 'search_read',
        [[['model', '=', 'purchase.order'], ['name', 'like', 'x_studio']]],
        {'fields': ['name', 'field_description', 'ttype', 'relation']}
    )
    
    print(f"\nCampos custom encontrados: {len(fields)}\n")
    
    for field in fields:
        print(f"  {field['name']:<40} | {field['field_description']:<40} | {field['ttype']}")
        if 'approval' in field['name'].lower() or 'aprobac' in field['name'].lower():
            print(f"    >>> RELEVANTE PARA APROBACIONES <<<")
except Exception as e:
    print(f"Error: {e}")

# 2. Buscar studio.approval.rule si existe
print("\n" + "=" * 100)
print("2. REGLAS DE APROBACION DE STUDIO")
print("=" * 100)

try:
    approval_rules = odoo.search_read(
        'studio.approval.rule',
        [],
        ['id', 'name', 'model_id', 'group_id', 'responsible_id', 'domain', 'active'],
        limit=100
    )
    
    print(f"\nReglas encontradas: {len(approval_rules)}\n")
    
    for rule in approval_rules:
        model = rule.get('model_id')
        model_name = model[1] if isinstance(model, (list, tuple)) else model
        
        if 'purchase' in model_name.lower():
            print(f"  {'='*90}")
            print(f"  ID: {rule['id']}")
            print(f"  Nombre: {rule.get('name', '')}")
            print(f"  Modelo: {model_name}")
            print(f"  Activa: {rule.get('active', False)}")
            
            if rule.get('group_id'):
                group = rule.get('group_id')
                group_name = group[1] if isinstance(group, (list, tuple)) else group
                print(f"  Grupo: {group_name}")
            
            if rule.get('responsible_id'):
                responsible = rule.get('responsible_id')
                responsible_name = responsible[1] if isinstance(responsible, (list, tuple)) else responsible
                print(f"  Responsable: {responsible_name}")
            
            if rule.get('domain'):
                print(f"  Dominio: {rule.get('domain')}")
except Exception as e:
    print(f"No existe modelo studio.approval.rule: {e}")

# 3. Buscar approval.request relacionado con purchase.order
print("\n" + "=" * 100)
print("3. SOLICITUDES DE APROBACION (approval.request)")
print("=" * 100)

try:
    approval_requests = odoo.search_read(
        'approval.request',
        [['res_model', '=', 'purchase.order']],
        ['id', 'name', 'res_id', 'res_name', 'request_status', 'approver_ids'],
        limit=10,
        order='id desc'
    )
    
    print(f"\nSolicitudes encontradas: {len(approval_requests)}\n")
    
    for req in approval_requests:
        print(f"  OC: {req.get('res_name', '')} (ID: {req.get('res_id', '')})")
        print(f"  Estado: {req.get('request_status', '')}")
        print()
except Exception as e:
    print(f"No existe modelo approval.request: {e}")

# 4. Buscar en studio.approval.entry
print("\n" + "=" * 100)
print("4. ENTRADAS DE APROBACION DE STUDIO")
print("=" * 100)

try:
    approval_entries = odoo.search_read(
        'studio.approval.entry',
        [['model', '=', 'purchase.order']],
        ['id', 'name', 'model', 'res_id', 'rule_id', 'user_id', 'approved'],
        limit=20,
        order='id desc'
    )
    
    print(f"\nEntradas encontradas: {len(approval_entries)}\n")
    
    for entry in approval_entries:
        print(f"  {'─'*85}")
        print(f"  ID: {entry['id']}")
        print(f"  OC ID: {entry.get('res_id', '')}")
        
        if entry.get('rule_id'):
            rule = entry.get('rule_id')
            rule_name = rule[1] if isinstance(rule, (list, tuple)) else rule
            print(f"  Regla: {rule_name}")
        
        if entry.get('user_id'):
            user = entry.get('user_id')
            user_name = user[1] if isinstance(user, (list, tuple)) else user
            print(f"  Usuario: {user_name}")
        
        print(f"  Aprobado: {entry.get('approved', False)}")
except Exception as e:
    print(f"No existe modelo studio.approval.entry: {e}")

# 5. Buscar todas las ir.actions.server que crean actividades
print("\n" + "=" * 100)
print("5. TODAS LAS ACCIONES QUE CREAN ACTIVIDADES 'Grant Approval'")
print("=" * 100)

# Primero obtener el ID del tipo de actividad
activity_types = odoo.search_read(
    'mail.activity.type',
    [['name', '=', 'Grant Approval']],
    ['id', 'name'],
    limit=1
)

if activity_types:
    grant_approval_id = activity_types[0]['id']
    
    # Buscar TODAS las acciones que usan este tipo
    all_actions = odoo.search_read(
        'ir.actions.server',
        [['activity_type_id', '=', grant_approval_id]],
        ['id', 'name', 'model_id', 'usage', 'state'],
        limit=100
    )
    
    print(f"\nAcciones que crean Grant Approval: {len(all_actions)}\n")
    
    for action in all_actions:
        model = action.get('model_id')
        model_name = model[1] if isinstance(model, (list, tuple)) else model
        
        print(f"  ID: {action['id']:<6} | {action.get('name', ''):<50} | Modelo: {model_name}")
        print(f"    Uso: {action.get('usage', '')} | Estado: {action.get('state', '')}")
        
        # Buscar qué automatización usa esta acción
        try:
            # Buscar en base.automation donde esta acción esté referenciada
            # Necesitamos buscar en todos los registros y ver cuál tiene esta acción
            pass
        except:
            pass

# 6. Buscar workflows/transiciones
print("\n" + "=" * 100)
print("6. WORKFLOWS Y TRANSICIONES")
print("=" * 100)

try:
    workflows = odoo.search_read(
        'workflow',
        [['osv', '=', 'purchase.order']],
        ['id', 'name', 'osv'],
        limit=10
    )
    
    print(f"\nWorkflows encontrados: {len(workflows)}\n")
    for wf in workflows:
        print(f"  {wf['id']}: {wf.get('name', '')}")
except Exception as e:
    print(f"No existen workflows (versión Odoo moderna): {e}")

# 7. Buscar en res.groups usuarios con permisos de aprobación
print("\n" + "=" * 100)
print("7. MARCELO JARAMILLO - GRUPOS Y PERMISOS")
print("=" * 100)

marcelo = odoo.search_read(
    'res.users',
    [['name', 'ilike', 'MARCELO JARAMILLO']],
    ['id', 'name', 'groups_id'],
    limit=1
)

if marcelo:
    user_id = marcelo[0]['id']
    group_ids = marcelo[0].get('groups_id', [])
    
    print(f"Usuario: {marcelo[0]['name']} (ID: {user_id})")
    print(f"Total grupos: {len(group_ids)}\n")
    
    if group_ids:
        groups = odoo.search_read(
            'res.groups',
            [['id', 'in', group_ids]],
            ['id', 'name', 'category_id'],
            limit=100
        )
        
        print("Grupos relevantes:")
        for group in groups:
            if any(keyword in group.get('name', '').lower() for keyword in ['approv', 'manager', 'admin', 'officer']):
                category = group.get('category_id')
                cat_name = category[1] if isinstance(category, (list, tuple)) else ''
                print(f"  - {group.get('name', ''):<50} | {cat_name}")

print("\n" + "=" * 100)
print("DONE")
print("=" * 100)
