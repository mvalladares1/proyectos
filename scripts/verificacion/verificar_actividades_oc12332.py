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
print("VERIFICAR ACTIVIDADES EXACTAS DE OC12332")
print("=" * 80)

# Buscar OC12332
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12332']]],
    {'fields': ['id', 'name', 'state'], 'limit': 1})

oc_id = oc[0]['id']
print(f"\nOC12332 ID: {oc_id}, Estado: {oc[0]['state']}")

# Buscar TODAS las actividades de esta OC
print("\n1. TODAS LAS ACTIVIDADES DE OC12332:")
print("-" * 80)
actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
    [[
        ['res_id', '=', oc_id],
        ['res_model', '=', 'purchase.order']
    ]],
    {'fields': ['id', 'activity_type_id', 'summary', 'user_id', 'date_deadline', 'state']})

print(f"Total actividades: {len(actividades)}")
for act in actividades:
    tipo = act.get('activity_type_id', [False, 'Sin tipo'])[1] if act.get('activity_type_id') else 'Sin tipo'
    usuario = act.get('user_id', [False, 'Sin usuario'])[1] if act.get('user_id') else 'Sin usuario'
    user_id = act.get('user_id', [False])[0] if act.get('user_id') else None
    
    print(f"\n  ID: {act['id']}")
    print(f"  Tipo: {tipo}")
    print(f"  Usuario: {usuario} (ID: {user_id})")
    print(f"  Resumen: {act.get('summary', 'Sin resumen')}")
    print(f"  Estado: {act.get('state', 'Sin estado')}")
    
    # Leer grupos del usuario
    if user_id:
        try:
            usuario_grupos = models.execute_kw(db, uid, password, 'res.users', 'read',
                [user_id], {'fields': ['groups_id']})
            
            if usuario_grupos and usuario_grupos[0].get('groups_id'):
                grupo_ids = usuario_grupos[0]['groups_id']
                grupos = models.execute_kw(db, uid, password, 'res.groups', 'read',
                    [grupo_ids], {'fields': ['name', 'category_id']})
                
                print(f"  Grupos del usuario:")
                for grupo in grupos[:5]:  # Primeros 5
                    cat = grupo.get('category_id', [False, 'Sin cat'])[1] if grupo.get('category_id') else 'Sin cat'
                    if 'Aprobacion' in cat or 'Finanza' in cat or 'Control' in cat or 'Compra' in cat:
                        print(f"    → {grupo['name']} (Cat: {cat})")
        except:
            pass

print("\n" + "=" * 80)
print("Si ves Paulina o Felipe aquí, hay que eliminar sus actividades")
print("=" * 80)
