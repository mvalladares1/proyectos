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
print("LEER CÓDIGO COMPLETO DE CHECK 1 Y CHECK 2")
print("=" * 80)

# Leer Check 1
print("\n1. CHECK 1 (Acción ID 1015):")
print("-" * 80)
try:
    check1 = models.execute_kw(db, uid, password, 'ir.actions.server', 'read',
        [1015], {'fields': ['name', 'code', 'state']})
    
    if check1:
        print(f"  Nombre: {check1[0]['name']}")
        print(f"  Estado: {check1[0].get('state')}")
        print(f"\n  CÓDIGO:")
        print("  " + "─" * 76)
        codigo = check1[0].get('code', 'Sin código')
        for linea in codigo.split('\n'):
            print(f"  {linea}")
except Exception as e:
    print(f"  ❌ Error: {e}")

# Leer Check 2
print("\n\n2. CHECK 2 (Acción ID 1016):")
print("-" * 80)
try:
    check2 = models.execute_kw(db, uid, password, 'ir.actions.server', 'read',
        [1016], {'fields': ['name', 'code', 'state']})
    
    if check2:
        print(f"  Nombre: {check2[0]['name']}")
        print(f"  Estado: {check2[0].get('state')}")
        print(f"\n  CÓDIGO:")
        print("  " + "─" * 76)
        codigo = check2[0].get('code', 'Sin código')
        for linea in codigo.split('\n'):
            print(f"  {linea}")
except Exception as e:
    print(f"  ❌ Error: {e}")

print("\n" + "=" * 80)
