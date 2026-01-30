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
print("TODAS LAS ACTIVIDADES DE APROBACIÓN PENDIENTES PARA MIGUEL (217)")
print("=" * 80)

# Buscar TODAS las actividades de aprobación asignadas a Miguel
print("\n1. ACTIVIDADES DE APROBACIÓN PARA MIGUEL:")
print("-" * 80)
actividades = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
    [[
        ['user_id', '=', 217],  # Miguel
        ['activity_type_id', '=', 9],  # Grant Approval
        ['res_model', '=', 'purchase.order']
    ]],
    {'fields': ['id', 'res_id', 'res_name', 'summary', 'user_id'], 'limit': 50})

print(f"Total actividades encontradas: {len(actividades)}")

if actividades:
    for act in actividades:
        print(f"\n  ID: {act['id']}")
        print(f"  OC: {act.get('res_name', 'Sin nombre')} (ID: {act['res_id']})")
        print(f"  Resumen: {act.get('summary', 'Sin resumen')}")
        print(f"  Usuario: {act.get('user_id', ['?', 'Sin usuario'])[1]}")

# El popup muestra aprobaciones de CUALQUIER usuario, no solo Miguel
# Buscar actividades de Paulina y Felipe
print("\n\n2. ACTIVIDADES DE PAULINA (27) Y FELIPE (17):")
print("-" * 80)
actividades_otros = models.execute_kw(db, uid, password, 'mail.activity', 'search_read',
    [[
        ['user_id', 'in', [27, 17]],
        ['activity_type_id', '=', 9],
        ['res_model', '=', 'purchase.order']
    ]],
    {'fields': ['id', 'res_id', 'res_name', 'summary', 'user_id'], 'limit': 10})

print(f"Total actividades: {len(actividades_otros)}")
for act in actividades_otros:
    print(f"\n  OC: {act.get('res_name')} - Usuario: {act.get('user_id', ['?', '?'])[1]}")

print("\n" + "=" * 80)
print("INTERPRETACIÓN:")
print("-" * 80)
print("El popup del botón CONFIRMAR PEDIDO muestra:")
print("  - Las actividades de aprobación pendientes")
print("  - Agrupadas por CATEGORÍA del grupo del usuario (Aprobaciones/Finanzas, Control)")
print("  - NO es de esta OC específica, son de TODAS las OCs pendientes")
print("\nPara OC12332 específicamente, solo debería pedir aprobación de Maximo.")
print("=" * 80)
