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
print("INTENTAR CONFIRMAR OC12332 DIRECTAMENTE")
print("=" * 80)

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

# Intentar ejecutar button_confirm
print("\n2. INTENTANDO EJECUTAR button_confirm:")
print("-" * 80)
try:
    result = models.execute_kw(db, uid, password, 'purchase.order', 'button_confirm',
        [[oc['id']]])
    print(f"  ✅ button_confirm ejecutado: {result}")
except Exception as e:
    error_msg = str(e)
    print(f"  ❌ Error al ejecutar button_confirm:")
    print(f"     {error_msg}")
    
    # Buscar mensajes de validación específicos
    if "pending" in error_msg.lower() or "approval" in error_msg.lower():
        print("\n  ⚠️  Hay validaciones de aprobación pendientes")
    elif "tier" in error_msg.lower():
        print("\n  ⚠️  Hay validaciones de tier pendientes")

# Verificar campos de validación de la OC
print("\n3. CAMPOS DE VALIDACIÓN DE LA OC:")
print("-" * 80)
try:
    oc_full = models.execute_kw(db, uid, password, 'purchase.order', 'read',
        [oc['id']],
        {'fields': ['need_validation', 'validated', 'to_validate', 'state']})
    
    if oc_full:
        for field, value in oc_full[0].items():
            print(f"  {field}: {value}")
except Exception as e:
    print(f"  ℹ️  Algunos campos no existen: {e}")

print("\n" + "=" * 80)
