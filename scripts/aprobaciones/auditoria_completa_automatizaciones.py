import xmlrpc.client

# Conexión a Odoo
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("AUDITORÍA COMPLETA DE AUTOMATIZACIONES - PURCHASE.ORDER")
print("=" * 80)

# 1. TODAS las automatizaciones activas
print("\n1. AUTOMATIZACIONES ACTIVAS:")
print("-" * 80)
autos = models.execute_kw(db, uid, password, 'base.automation', 'search_read',
    [[['model_id.model', '=', 'purchase.order'], ['active', '=', True]]],
    {'fields': ['id', 'name', 'trigger', 'filter_domain', 'action_server_id', 'trigger_field_ids'], 'limit': 50})

print(f"Total: {len(autos)}\n")
for auto in autos:
    print(f"ID: {auto['id']} | {auto['name']}")
    print(f"  Trigger: {auto.get('trigger')}")
    print(f"  Dominio: {auto.get('filter_domain')}")
    if auto.get('action_server_id'):
        print(f"  Acción: {auto['action_server_id'][1]} (ID: {auto['action_server_id'][0]})")
    if auto.get('trigger_field_ids'):
        print(f"  Campos trigger: {auto['trigger_field_ids']}")
    print()

# 2. Leer CÓDIGO de todas las acciones
print("\n2. CÓDIGO DE TODAS LAS ACCIONES SERVER:")
print("-" * 80)
action_ids = [auto['action_server_id'][0] for auto in autos if auto.get('action_server_id')]

for action_id in action_ids:
    action = models.execute_kw(db, uid, password, 'ir.actions.server', 'read',
        [action_id], {'fields': ['id', 'name', 'code', 'state']})
    
    if action:
        print(f"\nACCIÓN ID {action_id}: {action[0]['name']}")
        print("─" * 80)
        codigo = action[0].get('code', '')
        if codigo and len(codigo.strip()) > 10:
            # Buscar si crea actividades
            if 'mail.activity' in codigo or 'activity' in codigo.lower():
                print("⚠️ CREA ACTIVIDADES:")
                for linea in codigo.split('\n'):
                    if 'mail.activity' in linea or 'create' in linea.lower():
                        print(f"  {linea.strip()}")
            else:
                print("  (No crea actividades)")
        else:
            print("  (Código vacío)")

# 3. Automatizaciones en mail.activity
print("\n\n3. AUTOMATIZACIONES EN MAIL.ACTIVITY:")
print("-" * 80)
activity_autos = models.execute_kw(db, uid, password, 'base.automation', 'search_read',
    [[['model_id.model', '=', 'mail.activity'], ['active', '=', True]]],
    {'fields': ['id', 'name', 'trigger', 'filter_domain', 'action_server_id']})

print(f"Total: {len(activity_autos)}\n")
for auto in activity_autos:
    print(f"ID: {auto['id']} | {auto['name']}")
    print(f"  Trigger: {auto.get('trigger')}")
    print(f"  Dominio: {auto.get('filter_domain')}")
    if auto.get('action_server_id'):
        action_id = auto['action_server_id'][0]
        action = models.execute_kw(db, uid, password, 'ir.actions.server', 'read',
            [action_id], {'fields': ['code']})
        if action and action[0].get('code'):
            print(f"  CÓDIGO:")
            for linea in action[0]['code'].split('\n')[:15]:
                print(f"    {linea}")
    print()

# 4. Buscar workflows en purchase.order
print("\n4. WORKFLOWS/TRANSICIONES:")
print("-" * 80)
try:
    workflows = models.execute_kw(db, uid, password, 'workflow', 'search_read',
        [[['osv', '=', 'purchase.order']]],
        {'fields': ['id', 'name', 'osv']})
    
    if workflows:
        print(f"Workflows encontrados: {len(workflows)}")
        for wf in workflows:
            print(f"  - {wf}")
    else:
        print("  No hay workflows")
except:
    print("  Modelo workflow no existe (Odoo 13+)")

print("\n" + "=" * 80)
print("ANÁLISIS COMPLETO")
print("=" * 80)
