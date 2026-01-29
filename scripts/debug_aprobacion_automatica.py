"""
Script de debug para investigar aprobaciones automáticas en OCs
Objetivo: Identificar qué gatilla la actividad "Otorgar Aprobación" para Máximo

Uso:
    python scripts/debug_aprobacion_automatica.py
"""

import sys
import os
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Credenciales
USERNAME = input("Usuario Odoo: ")
PASSWORD = input("API Key: ")

def debug_oc(odoo, oc_name):
    """Debug completo de una OC y sus actividades."""
    print("\n" + "=" * 100)
    print(f"DEBUG: Orden de Compra {oc_name}")
    print("=" * 100)
    
    # 1. Buscar la OC
    ocs = odoo.search_read(
        'purchase.order',
        [['name', '=', oc_name]],
        ['id', 'name', 'partner_id', 'amount_total', 'state', 'date_order', 
         'user_id', 'create_uid', 'create_date', 'write_uid', 'write_date',
         'activity_ids', 'message_ids'],
        limit=1
    )
    
    if not ocs:
        print(f"❌ No se encontró la OC {oc_name}")
        return
    
    oc = ocs[0]
    print(f"\n📋 INFORMACIÓN DE LA OC:")
    print(f"   ID: {oc['id']}")
    print(f"   Nombre: {oc['name']}")
    print(f"   Estado: {oc['state']}")
    print(f"   Monto: ${oc['amount_total']:,.0f}")
    print(f"   Fecha: {oc.get('date_order', '')}")
    
    user_id = oc.get('user_id')
    user_name = user_id[1] if isinstance(user_id, (list, tuple)) else user_id
    print(f"   Usuario: {user_name}")
    
    partner_id = oc.get('partner_id')
    partner_name = partner_id[1] if isinstance(partner_id, (list, tuple)) else partner_id
    print(f"   Proveedor: {partner_name}")
    
    create_uid = oc.get('create_uid')
    create_name = create_uid[1] if isinstance(create_uid, (list, tuple)) else create_uid
    print(f"   Creado por: {create_name} el {oc.get('create_date', '')}")
    
    write_uid = oc.get('write_uid')
    write_name = write_uid[1] if isinstance(write_uid, (list, tuple)) else write_uid
    print(f"   Modificado por: {write_name} el {oc.get('write_date', '')}")
    
    # 2. Actividades asociadas
    print(f"\n📌 ACTIVIDADES:")
    activity_ids = oc.get('activity_ids', [])
    
    if activity_ids:
        activities = odoo.search_read(
            'mail.activity',
            [['id', 'in', activity_ids]],
            ['id', 'activity_type_id', 'summary', 'note', 'date_deadline', 
             'user_id', 'create_uid', 'create_date', 'res_model', 'res_id',
             'automated', 'res_name'],
            limit=50
        )
        
        print(f"   Total actividades: {len(activities)}\n")
        
        for act in activities:
            act_type = act.get('activity_type_id')
            act_type_name = act_type[1] if isinstance(act_type, (list, tuple)) else act_type
            
            assigned_to = act.get('user_id')
            assigned_name = assigned_to[1] if isinstance(assigned_to, (list, tuple)) else assigned_to
            
            created_by = act.get('create_uid')
            created_name = created_by[1] if isinstance(created_by, (list, tuple)) else created_by
            
            print(f"   {'─' * 90}")
            print(f"   ID: {act['id']}")
            print(f"   Tipo: {act_type_name}")
            print(f"   Resumen: {act.get('summary', 'N/A')}")
            print(f"   Asignada a: {assigned_name}")
            print(f"   Creada por: {created_name}")
            print(f"   Fecha creación: {act.get('create_date', '')}")
            print(f"   Fecha límite: {act.get('date_deadline', '')}")
            print(f"   ¿Automatizada?: {act.get('automated', False)}")
            if act.get('note'):
                print(f"   Nota: {act.get('note', '')[:100]}")
    else:
        print("   Sin actividades asociadas")
    
    # 3. Tipos de actividad disponibles
    print(f"\n📋 TIPOS DE ACTIVIDAD EN PURCHASE.ORDER:")
    try:
        activity_types = odoo.search_read(
            'mail.activity.type',
            [],
            ['id', 'name', 'category', 'summary'],
            limit=100
        )
        
        print(f"   {'Nombre':<40} {'Categoría':<20} {'Resumen':<40}")
        print(f"   {'-' * 100}")
        for atype in activity_types:
            if 'aprobaci' in atype.get('name', '').lower() or 'approval' in atype.get('name', '').lower():
                print(f"   {atype.get('name', '')[:38]:<40} {atype.get('category', ''):<20} {(atype.get('summary') or '')[:38]:<40}")
    except Exception as e:
        print(f"   Error al obtener tipos de actividad: {e}")
    
    # 4. Buscar reglas de aprobación
    print(f"\n🔍 BUSCANDO REGLAS DE APROBACIÓN:")
    
    # Buscar en purchase.approval.rule si existe
    try:
        approval_rules = odoo.search_read(
            'purchase.approval.rule',
            [],
            ['id', 'name', 'amount_threshold', 'user_id', 'active'],
            limit=100
        )
        
        if approval_rules:
            print(f"   Reglas encontradas: {len(approval_rules)}\n")
            print(f"   {'Regla':<40} {'Umbral':<15} {'Usuario':<40} {'Activa':<10}")
            print(f"   {'-' * 105}")
            for rule in approval_rules:
                user = rule.get('user_id')
                user_name = user[1] if isinstance(user, (list, tuple)) else user
                print(f"   {rule.get('name', '')[:38]:<40} ${rule.get('amount_threshold', 0):>13,.0f} {str(user_name)[:38]:<40} {rule.get('active', False):<10}")
        else:
            print("   ❌ No se encontraron reglas de aprobación")
    except Exception as e:
        print(f"   ℹ️  No existe modelo 'purchase.approval.rule': {e}")
    
    # 5. Buscar automatizaciones (ir.cron, automated actions)
    print(f"\n🤖 AUTOMATIZACIONES RELACIONADAS CON PURCHASE.ORDER:")
    
    try:
        # Buscar acciones de servidor
        server_actions = odoo.search_read(
            'ir.actions.server',
            [['model_id.model', '=', 'purchase.order']],
            ['id', 'name', 'state', 'usage', 'code'],
            limit=50
        )
        
        if server_actions:
            print(f"   Acciones de servidor: {len(server_actions)}\n")
            for action in server_actions:
                print(f"   {'─' * 90}")
                print(f"   ID: {action['id']}")
                print(f"   Nombre: {action.get('name', '')}")
                print(f"   Estado: {action.get('state', '')}")
                print(f"   Uso: {action.get('usage', '')}")
                if action.get('code'):
                    print(f"   Código (primeras 200 chars):")
                    print(f"   {action.get('code', '')[:200]}")
    except Exception as e:
        print(f"   Error al buscar acciones de servidor: {e}")
    
    # 6. Buscar acciones automáticas base
    try:
        base_automations = odoo.search_read(
            'base.automation',
            [['model_id.model', '=', 'purchase.order']],
            ['id', 'name', 'trigger', 'filter_pre_domain', 'filter_domain', 'active', 'state'],
            limit=50
        )
        
        if base_automations:
            print(f"\n   Automatizaciones base: {len(base_automations)}\n")
            for auto in base_automations:
                print(f"   {'─' * 90}")
                print(f"   ID: {auto['id']}")
                print(f"   Nombre: {auto.get('name', '')}")
                print(f"   Trigger: {auto.get('trigger', '')}")
                print(f"   Activa: {auto.get('active', False)}")
                print(f"   Estado: {auto.get('state', '')}")
                if auto.get('filter_domain'):
                    print(f"   Dominio: {auto.get('filter_domain', '')}")
    except Exception as e:
        print(f"   Error al buscar automatizaciones base: {e}")
    
    # 7. Mensajes/historial
    print(f"\n💬 MENSAJES RECIENTES (últimos 5):")
    message_ids = oc.get('message_ids', [])
    
    if message_ids:
        messages = odoo.search_read(
            'mail.message',
            [['id', 'in', message_ids[:5]]],
            ['id', 'date', 'author_id', 'body', 'message_type', 'subtype_id'],
            limit=5,
            order='date desc'
        )
        
        for msg in messages:
            author = msg.get('author_id')
            author_name = author[1] if isinstance(author, (list, tuple)) else 'Sistema'
            
            subtype = msg.get('subtype_id')
            subtype_name = subtype[1] if isinstance(subtype, (list, tuple)) else ''
            
            print(f"   {'─' * 90}")
            print(f"   Fecha: {msg.get('date', '')}")
            print(f"   Autor: {author_name}")
            print(f"   Tipo: {msg.get('message_type', '')} - {subtype_name}")
            if msg.get('body'):
                # Limpiar HTML
                body = msg.get('body', '').replace('<p>', '').replace('</p>', '').replace('<br/>', '\n')
                print(f"   Contenido: {body[:200]}")
    
    return oc

def buscar_usuarios_aprobadores(odoo):
    """Busca usuarios con rol de aprobador."""
    print("\n" + "=" * 100)
    print("USUARIOS CON ROL DE APROBADOR")
    print("=" * 100)
    
    # Buscar grupos relacionados con aprobación
    grupos = odoo.search_read(
        'res.groups',
        [['name', 'ilike', 'approv']],
        ['id', 'name', 'users'],
        limit=50
    )
    
    print(f"\nGrupos encontrados: {len(grupos)}\n")
    
    for grupo in grupos:
        print(f"   📁 {grupo.get('name', '')}")
        user_ids = grupo.get('users', [])
        if user_ids:
            users = odoo.search_read(
                'res.users',
                [['id', 'in', user_ids]],
                ['id', 'name', 'login', 'active'],
                limit=100
            )
            for user in users:
                print(f"      - {user.get('name', '')} ({user.get('login', '')})")
        print()

def main():
    """Main debug."""
    
    print("\n" + "=" * 100)
    print("DEBUG DE APROBACIONES AUTOMÁTICAS - RÍO FUTURO")
    print("=" * 100)
    
    # Conectar
    print("\nConectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("✓ Conectado\n")
    
    # OC específica a debuggear
    oc_name = input("Nombre de la OC a debuggear (ej: OC12214): ").strip()
    
    if not oc_name:
        print("❌ Debes ingresar el nombre de una OC")
        return
    
    # Debug de la OC
    oc = debug_oc(odoo, oc_name)
    
    # Buscar usuarios aprobadores
    buscar_usuarios_aprobadores(odoo)
    
    print("\n" + "=" * 100)
    print("DEBUG COMPLETADO")
    print("=" * 100)
    print("""
ÁREAS A INVESTIGAR:
===================
1. Revisa las automatizaciones (base.automation) que tengan trigger en 'purchase.order'
2. Busca acciones de servidor (ir.actions.server) que creen actividades
3. Verifica si hay campos custom que gatillen workflows (x_studio_*)
4. Revisa el código de las acciones para ver condiciones de aprobación
5. Compara el monto de la OC con los umbrales de aprobación encontrados
    """)

if __name__ == "__main__":
    main()
