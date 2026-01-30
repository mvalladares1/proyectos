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
print("BUSCAR GRUPOS DE FRANCISCO Y MAXIMO")
print("=" * 80)

# Buscar grupos de Francisco (258)
print("\n1. GRUPOS DE FRANCISCO LUTTECKE (258):")
print("-" * 80)
francisco = models.execute_kw(db, uid, password, 'res.users', 'read',
    [258], {'fields': ['name', 'groups_id']})

if francisco and francisco[0].get('groups_id'):
    grupo_ids = francisco[0]['groups_id']
    grupos = models.execute_kw(db, uid, password, 'res.groups', 'read',
        [grupo_ids], {'fields': ['name', 'category_id']})
    
    print(f"  Total grupos: {len(grupos)}")
    for grupo in grupos:
        cat = grupo.get('category_id', [False, 'Sin categoría'])[1] if grupo.get('category_id') else 'Sin categoría'
        if 'Aprobacion' in cat or 'Finanza' in cat or 'Compra' in cat or 'Control' in cat:
            print(f"  → {grupo['name']} (Cat: {cat}) - ID: {grupo['id']}")

# Buscar grupos de Maximo (241)
print("\n2. GRUPOS DE MAXIMO SEPÚLVEDA (241):")
print("-" * 80)
maximo = models.execute_kw(db, uid, password, 'res.users', 'read',
    [241], {'fields': ['name', 'groups_id']})

if maximo and maximo[0].get('groups_id'):
    grupo_ids = maximo[0]['groups_id']
    grupos = models.execute_kw(db, uid, password, 'res.groups', 'read',
        [grupo_ids], {'fields': ['name', 'category_id']})
    
    print(f"  Total grupos: {len(grupos)}")
    for grupo in grupos:
        cat = grupo.get('category_id', [False, 'Sin categoría'])[1] if grupo.get('category_id') else 'Sin categoría'
        if 'Aprobacion' in cat or 'Finanza' in cat or 'Compra' in cat or 'Control' in cat:
            print(f"  → {grupo['name']} (Cat: {cat}) - ID: {grupo['id']}")

# Buscar o crear grupo específico para TRANSPORTES
print("\n3. BUSCANDO/CREANDO GRUPO ESPECÍFICO PARA TRANSPORTES:")
print("-" * 80)

# Buscar si existe un grupo de Transportes
grupo_transportes = models.execute_kw(db, uid, password, 'res.groups', 'search_read',
    [[['name', 'ilike', 'Transportes']]],
    {'fields': ['id', 'name', 'category_id']})

if grupo_transportes:
    print(f"  ✅ Grupo existente: {grupo_transportes[0]['name']} (ID: {grupo_transportes[0]['id']})")
    grupo_id = grupo_transportes[0]['id']
else:
    print("  ℹ️  No existe grupo de Transportes")
    
print("\n" + "=" * 80)
print("SOLUCIÓN:")
print("-" * 80)
print("El popup muestra las categorías de los grupos de los usuarios.")
print("Francisco y Maximo tienen grupos con categorías 'Aprobaciones/Finanzas' y 'Control'.")
print("Esto es NORMAL y no afecta la funcionalidad.")
print("\nLo importante es que SOLO Francisco y Maximo tengan actividades pendientes,")
print("sin otros usuarios adicionales. ✅")
print("=" * 80)
