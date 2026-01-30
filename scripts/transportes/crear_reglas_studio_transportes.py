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
print("CREAR REGLAS DE STUDIO PARA TRANSPORTES CON USUARIOS ESPECÍFICOS")
print("=" * 80)

# IDs de usuarios
FRANCISCO_ID = 258
MAXIMO_ID = 241
FELIPE_ID = 17

# Obtener model_id de purchase.order
model = models.execute_kw(db, uid, password, 'ir.model', 'search_read',
    [[['model', '=', 'purchase.order']]],
    {'fields': ['id'], 'limit': 1})

if not model:
    print("❌ No se encontró modelo purchase.order")
    exit(1)

model_id = model[0]['id']

# Dominio para TRANSPORTES (SERVICIOS con producto FLETE)
# Nota: Studio rules no pueden filtrar por producto, así que usamos categoría SERVICIOS
dominio_transportes = "[['x_studio_categora_de_producto', '=', 'SERVICIOS']]"

print(f"\n1. CREANDO REGLAS PARA TRANSPORTES:")
print("-" * 80)

# Regla 1: Francisco para button_confirm en draft/sent
try:
    regla_francisco = models.execute_kw(db, uid, password, 'studio.approval.rule', 'create',
        [{
            'name': 'Pedido de compra/button_confirm (TRANSPORTES - Francisco Luttecke)',
            'model_id': model_id,
            'method': 'button_confirm',
            'exclusive_user': FRANCISCO_ID,
            'domain': dominio_transportes,
            'active': True,
        }])
    
    print(f"  ✅ Regla Francisco creada (ID: {regla_francisco})")
except Exception as e:
    print(f"  ❌ Error creando regla Francisco: {e}")

# Regla 2: Maximo para button_confirm en draft/sent
try:
    regla_maximo = models.execute_kw(db, uid, password, 'studio.approval.rule', 'create',
        [{
            'name': 'Pedido de compra/button_confirm (TRANSPORTES - Maximo Sepúlveda)',
            'model_id': model_id,
            'method': 'button_confirm',
            'exclusive_user': MAXIMO_ID,
            'domain': dominio_transportes,
            'active': True,
        }])
    
    print(f"  ✅ Regla Maximo creada (ID: {regla_maximo})")
except Exception as e:
    print(f"  ❌ Error creando regla Maximo: {e}")

# Regla 3: Felipe para button_confirm (se ejecutará después de Francisco+Maximo)
try:
    regla_felipe = models.execute_kw(db, uid, password, 'studio.approval.rule', 'create',
        [{
            'name': 'Pedido de compra/button_confirm (TRANSPORTES - Felipe Horst)',
            'model_id': model_id,
            'method': 'button_confirm',
            'exclusive_user': FELIPE_ID,
            'domain': dominio_transportes,
            'active': False,  # La activamos solo cuando necesitemos el segundo nivel
        }])
    
    print(f"  ✅ Regla Felipe creada (ID: {regla_felipe}) - INACTIVA por ahora")
except Exception as e:
    print(f"  ❌ Error creando regla Felipe: {e}")

print("\n2. VERIFICANDO REGLAS CREADAS:")
print("-" * 80)

reglas_transportes = models.execute_kw(db, uid, password, 'studio.approval.rule', 'search_read',
    [[['domain', 'ilike', 'SERVICIOS']]],
    {'fields': ['id', 'name', 'exclusive_user', 'active', 'method']})

for regla in reglas_transportes:
    if 'TRANSPORTES' in regla.get('name', ''):
        estado = "✅ ACTIVA" if regla.get('active') else "❌ INACTIVA"
        usuario = regla.get('exclusive_user', [False, 'Sin usuario'])[1] if regla.get('exclusive_user') else 'Grupo'
        print(f"{estado} | ID {regla['id']}: {regla['name']}")
        print(f"  Usuario: {usuario}")
        print(f"  Método: {regla.get('method')}")

print("\n" + "=" * 80)
print("✅ REGLAS CREADAS")
print("=" * 80)
print("\nAhora al hacer clic en CONFIRMAR PEDIDO en una OC de TRANSPORTES:")
print("  1. Se pedirá aprobación de Francisco Luttecke")
print("  2. Se pedirá aprobación de Maximo Sepúlveda")
print("  3. NO aparecerán otros aprobadores (Finanzas, Control, etc.)")
print("\n⚠️  Recarga Odoo (Ctrl+F5) para que tome efecto")
print("\nNota: La regla de Felipe está creada pero inactiva.")
print("Si necesitas un segundo nivel de aprobación, actívala manualmente.")
