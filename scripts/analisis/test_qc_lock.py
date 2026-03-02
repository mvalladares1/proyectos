"""
Test: Verificar que la restricción de QC cerrado funciona
=========================================================
Intenta escribir en un QC cerrado con el usuario actual (Quality Admin).
Debería funcionar. Luego verifica la automated action está activa.
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from xmlrpc import client as xmlrpc_client

# Conexion
url = "https://riofuturo.server98c6e.oerpondemand.net"
db = "riofuturo-master"
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

common = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')
print(f"Conectado como UID={uid}")

def search_read(model, domain, fields, limit=100, order=None):
    kwargs = {'fields': fields, 'limit': limit}
    if order:
        kwargs['order'] = order
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], kwargs)

def write(model, ids, vals):
    return models.execute_kw(db, uid, password, model, 'write', [ids, vals])

# =============================================
# 1. Verificar automated action existe y activa
# =============================================
print("=" * 70)
print("TEST 1: Verificar Automated Action")
print("=" * 70)

aa = search_read('base.automation', 
    [['name', '=', 'RF: Bloquear edicion QC cerrado']], 
    ['id', 'name', 'active', 'trigger', 'filter_domain', 'state', 'code'])
if aa:
    print(f"  PASS: Automated Action encontrada (ID={aa[0]['id']})")
    print(f"    Active: {aa[0]['active']}")
    print(f"    Trigger: {aa[0]['trigger']}")
    print(f"    Domain: {aa[0]['filter_domain']}")
else:
    print("  FAIL: Automated Action NO encontrada")
    sys.exit(1)

# =============================================
# 2. Buscar un QC cerrado de Recepcion MP
# =============================================
print("\n" + "=" * 70)
print("TEST 2: Buscar QC cerrado de Recepcion MP")
print("=" * 70)

closed_qc = search_read('quality.check', 
    [['quality_state', '=', 'pass'], 
     ['x_studio_titulo_control_calidad', '=', 'Control de calidad Recepcion MP']],
    ['id', 'name', 'quality_state', 'x_studio_titulo_control_calidad', 'x_studio_observaciones'],
    limit=1, order='id desc')

if closed_qc:
    qc = closed_qc[0]
    print(f"  QC encontrado: ID={qc['id']}, ref={qc['name']}, state={qc['quality_state']}")
    print(f"  Titulo: {qc['x_studio_titulo_control_calidad']}")
    old_obs = qc.get('x_studio_observaciones', '') or ''
    print(f"  Observaciones actuales: '{old_obs[:80]}'")
else:
    print("  No se encontro QC cerrado de Recepcion MP")
    sys.exit(1)

# =============================================
# 3. TEST como Quality Admin (debe funcionar)
# =============================================
print("\n" + "=" * 70)
print("TEST 3: Escribir en QC cerrado como Quality Admin (mvalladares)")
print("  (Este usuario ES Quality Admin, debe FUNCIONAR)")
print("=" * 70)

test_marker = "[TEST-QC-LOCK]"
try:
    # Agregar y luego quitar el marcador
    new_obs = old_obs + test_marker if old_obs else test_marker
    result = write('quality.check', [qc['id']], {'x_studio_observaciones': new_obs})
    print(f"  PASS: Write exitoso (result={result})")
    
    # Revertir el cambio
    write('quality.check', [qc['id']], {'x_studio_observaciones': old_obs})
    print(f"  Revertido a valor original")
except Exception as e:
    error_msg = str(e)
    if "No tiene permisos" in error_msg:
        print(f"  UNEXPECTED: Bloqueo activado para Quality Admin!")
        print(f"  Error: {error_msg[:300]}")
    else:
        print(f"  ERROR: {error_msg[:300]}")

# =============================================
# 4. Verificar el grupo del usuario actual
# =============================================
print("\n" + "=" * 70)
print("TEST 4: Verificar que el usuario actual es Quality Admin")
print("=" * 70)

user_info = search_read('res.users', [['id', '=', uid]], ['name', 'groups_id'], limit=1)
if user_info:
    is_admin = 87 in user_info[0].get('groups_id', [])
    print(f"  Usuario: {user_info[0]['name']} (UID={uid})")
    print(f"  Es Quality Admin (grupo 87): {is_admin}")

# =============================================
# 5. Buscar un QC que NO sea Recepcion MP (no debería estar protegido)
# =============================================
print("\n" + "=" * 70)
print("TEST 5: QC de otro tipo (Control de Proceso) - NO debe estar protegido")
print("=" * 70)

other_qc = search_read('quality.check', 
    [['quality_state', '=', 'pass'], 
     ['x_studio_titulo_control_calidad', '!=', 'Control de calidad Recepcion MP'],
     ['x_studio_titulo_control_calidad', '!=', False]],
    ['id', 'name', 'quality_state', 'x_studio_titulo_control_calidad', 'x_studio_observaciones'],
    limit=1, order='id desc')

if other_qc:
    oqc = other_qc[0]
    print(f"  QC encontrado: ID={oqc['id']}, ref={oqc['name']}, tipo={oqc['x_studio_titulo_control_calidad']}")
    old_obs2 = oqc.get('x_studio_observaciones', '') or ''
    try:
        new_obs2 = old_obs2 + test_marker if old_obs2 else test_marker
        result2 = write('quality.check', [oqc['id']], {'x_studio_observaciones': new_obs2})
        print(f"  PASS: Write exitoso en QC de otro tipo (no protegido)")
        # Revertir
        write('quality.check', [oqc['id']], {'x_studio_observaciones': old_obs2})
        print(f"  Revertido a valor original")
    except Exception as e:
        print(f"  FAIL: No deberia estar bloqueado: {str(e)[:200]}")
else:
    print("  No se encontro QC de otro tipo cerrado")

print("\n" + "=" * 70)
print("RESUMEN DE TESTS")
print("=" * 70)
print("  Test 1 (AA existe): PASS")
print("  Test 2 (QC cerrado encontrado): PASS")
print("  Test 3 (Admin puede editar QC cerrado): verificado arriba")
print("  Test 4 (Usuario es admin): verificado arriba")
print("  Test 5 (Otro tipo QC no protegido): verificado arriba")
print("\nNOTA: Para verificar completamente que usuarios NO admin son bloqueados,")
print("se necesita ejecutar el test con credenciales de un usuario sin grupo Quality/Admin.")
