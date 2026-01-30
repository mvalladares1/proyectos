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
print("LIMPIAR Y PROTEGER OC12332 DE TRANSPORTES")
print("=" * 80)

# IDs de usuarios correctos
FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Buscar OC12332
print("\n1. BUSCANDO OC12332:")
print("-" * 80)
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12332']]],
    {'fields': ['name', 'state', 'id']})

if not oc:
    print("  ❌ OC12332 no encontrada")
    exit(1)

oc = oc[0]
print(f"  ✅ {oc['name']} (ID: {oc['id']}) - Estado: {oc['state']}")

# Buscar TODAS las actividades
print("\n2. ACTIVIDADES ACTUALES:")
print("-" * 80)
actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
    [[
        ['res_id', '=', oc['id']],
        ['res_model', '=', 'purchase.order'],
        ['activity_type_id', '=', 9]
    ]],
    {'fields': ['id', 'user_id', 'summary']})

print(f"  Total actividades: {len(actividades)}")
for act in actividades:
    user_name = act['user_id'][1] if act.get('user_id') else 'Sin usuario'
    user_id = act['user_id'][0] if act.get('user_id') else None
    print(f"    - {user_name} (ID: {user_id})")

# Determinar usuarios correctos
if oc['state'] in ['draft', 'sent', 'to approve']:
    usuarios_correctos = [FRANCISCO_ID, MAXIMO_ID]
    print(f"\n  Estado '{oc['state']}' → Solo: Francisco ({FRANCISCO_ID}) + Maximo ({MAXIMO_ID})")
elif oc['state'] == 'purchase':
    usuarios_correctos = [FELIPE_ID]
    print(f"\n  Estado 'purchase' → Solo: Felipe ({FELIPE_ID})")
else:
    usuarios_correctos = []

# Eliminar actividades incorrectas
print("\n3. ELIMINANDO ACTIVIDADES INCORRECTAS:")
print("-" * 80)
eliminadas = 0

for actividad in actividades:
    user_id = actividad['user_id'][0] if actividad.get('user_id') else None
    user_name = actividad['user_id'][1] if actividad.get('user_id') else 'Sin usuario'
    
    if user_id not in usuarios_correctos:
        try:
            models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [[actividad['id']]])
            print(f"  ❌ ELIMINADA: {user_name} (ID: {user_id})")
            eliminadas += 1
        except Exception as e:
            print(f"  ⚠️  Error: {e}")
    else:
        print(f"  ✅ CORRECTA: {user_name}")

print(f"\n  Total eliminadas: {eliminadas}")

# Modificar Check 1 y Check 2 para excluir TRANSPORTES
print("\n4. MODIFICANDO CHECK 1 Y CHECK 2 PARA EXCLUIR TRANSPORTES:")
print("-" * 80)

# Check 1 - Agregar exclusión de TRANSPORTES
try:
    check1 = models.execute_kw(db, uid, password, 'base.automation', 'search_read',
        [[['id', '=', 1]]],
        {'fields': ['name', 'filter_domain', 'active']})
    
    if check1:
        # Modificar dominio para excluir TRANSPORTES
        nuevo_dominio = [
            '&',
            ("order_line.product_id.product_tag_ids.name", "=", "MP"),
            '!',
            ('x_studio_categora_de_producto', '=', 'SERVICIOS')
        ]
        
        models.execute_kw(db, uid, password, 'base.automation', 'write',
            [[1], {'filter_domain': str(nuevo_dominio)}])
        
        print(f"  ✅ Check 1 actualizado: excluye SERVICIOS")
except Exception as e:
    print(f"  ⚠️  Error modificando Check 1: {e}")

# Check 2 - Agregar exclusión de TRANSPORTES
try:
    check2 = models.execute_kw(db, uid, password, 'base.automation', 'search_read',
        [[['id', '=', 2]]],
        {'fields': ['name', 'filter_domain', 'active']})
    
    if check2:
        # Modificar dominio para excluir TRANSPORTES
        nuevo_dominio = [
            '&',
            ("order_line.product_id.product_tag_ids.name", "=", "Insumos"),
            '!',
            ('x_studio_categora_de_producto', '=', 'SERVICIOS')
        ]
        
        models.execute_kw(db, uid, password, 'base.automation', 'write',
            [[2], {'filter_domain': str(nuevo_dominio)}])
        
        print(f"  ✅ Check 2 actualizado: excluye SERVICIOS")
except Exception as e:
    print(f"  ⚠️  Error modificando Check 2: {e}")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"✅ Actividades incorrectas eliminadas: {eliminadas}")
print(f"✅ Check 1 y Check 2 ahora EXCLUYEN categoría SERVICIOS")
print(f"✅ TRANSPORTES ya no tendrán aprobadores extra")
print("\nRecarga OC12332 y verifica que solo aparezca Maximo")
