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
print("LIMPIAR ACTIVIDADES EXTRA DE OC12393")
print("=" * 80)

# IDs de usuarios correctos
FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Buscar OC12393
print("\n1. BUSCANDO OC12393:")
print("-" * 80)
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[['name', '=', 'OC12393']]],
    {'fields': ['name', 'state', 'partner_id']})

if not oc:
    print("  ❌ OC12393 no encontrada")
    exit(1)

oc = oc[0]
print(f"  ✅ Encontrada: {oc['name']} - Estado: {oc['state']}")

# Buscar TODAS las actividades de aprobación
print("\n2. ACTIVIDADES ACTUALES:")
print("-" * 80)
actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
    [[
        ['res_id', '=', oc['id']],
        ['res_model', '=', 'purchase.order'],
        ['activity_type_id', '=', 9]  # Grant Approval
    ]],
    {'fields': ['id', 'user_id', 'summary']})

print(f"  Total actividades encontradas: {len(actividades)}")
for act in actividades:
    print(f"    - {act['user_id'][1]} (ID: {act['user_id'][0]})")

# Determinar usuarios correctos según estado
if oc['state'] in ['draft', 'sent', 'to approve']:
    usuarios_correctos = [FRANCISCO_ID, MAXIMO_ID]
    print(f"\n  Estado '{oc['state']}' → Correctos: Francisco ({FRANCISCO_ID}) + Maximo ({MAXIMO_ID})")
elif oc['state'] == 'purchase':
    usuarios_correctos = [FELIPE_ID]
    print(f"\n  Estado 'purchase' → Correcto: Felipe ({FELIPE_ID})")
else:
    usuarios_correctos = []
    print(f"\n  Estado '{oc['state']}' → Sin aprobadores")

# Eliminar actividades incorrectas
print("\n3. ELIMINANDO ACTIVIDADES EXTRA:")
print("-" * 80)
eliminadas = 0

for actividad in actividades:
    user_id = actividad['user_id'][0] if actividad.get('user_id') else None
    
    if user_id not in usuarios_correctos:
        try:
            models.execute_kw(db, uid, password, 'mail.activity', 'unlink', [[actividad['id']]])
            print(f"  ❌ ELIMINADA: {actividad['user_id'][1]} (ID: {user_id})")
            eliminadas += 1
        except Exception as e:
            print(f"  ⚠️  Error eliminando {actividad['id']}: {e}")
    else:
        print(f"  ✅ MANTENER: {actividad['user_id'][1]} (ID: {user_id})")

print("\n" + "=" * 80)
print("RESUMEN")
print("=" * 80)
print(f"Actividades eliminadas: {eliminadas}")
print(f"\n✅ Recarga OC12393 en Odoo y verifica el botón CONFIRMAR PEDIDO")
