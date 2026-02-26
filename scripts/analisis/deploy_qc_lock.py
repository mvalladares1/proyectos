"""
Deploy: Bloquear edición de quality.check cerrados (Aprobado/Fallido)
=====================================================================
Crea una Automated Action (base.automation) que bloquea la edición de
quality.check en estado 'pass' o 'fail' para usuarios que NO sean
Quality / Administrator.

Aplica solo a QCs con x_studio_titulo_control_calidad = 'Control de calidad Recepcion MP'
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

def search_read(model, domain, fields, limit=100):
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], {'fields': fields, 'limit': limit})

def create(model, vals):
    return models.execute_kw(db, uid, password, model, 'create', [vals])

def write(model, ids, vals):
    return models.execute_kw(db, uid, password, model, 'write', [ids, vals])

# =============================================
# CONSTANTES
# =============================================
AUTOMATION_NAME = "RF: Bloquear edicion QC cerrado"

# Código Python que se ejecuta en el servidor cuando se intenta escribir
# en un QC cerrado. Verifica si el usuario es Quality/Administrator.
SERVER_CODE = '''# RF: Bloquear edicion de QC cerrados (Recepcion MP)
# Solo Quality/Administrator puede editar QCs aprobados/fallidos
QUALITY_ADMIN_GROUP_XMLID = 'quality.group_quality_manager'

for rec in records:
    if rec.quality_state in ('pass', 'fail'):
        if rec.x_studio_titulo_control_calidad == 'Control de calidad Recepcion MP':
            if not env.user.has_group(QUALITY_ADMIN_GROUP_XMLID):
                estado = 'Aprobado' if rec.quality_state == 'pass' else 'Fallido'
                raise UserError(
                    "No tiene permisos para modificar un control de calidad en estado '%s'.\\n\\n"
                    "Solo los Administradores de Calidad pueden realizar cambios "
                    "en controles de Recepcion MP cerrados.\\n"
                    "Contacte a su jefe de calidad si necesita realizar modificaciones."
                    % estado
                )
'''

# =============================================
# 1. Obtener model_id para quality.check
# =============================================
print("\n1. Obteniendo model_id para quality.check...")
model_info = search_read('ir.model', [['model', '=', 'quality.check']], ['id', 'name'], limit=1)
if not model_info:
    print("   ERROR: No se encontro el modelo quality.check")
    sys.exit(1)
model_id = model_info[0]['id']
print(f"   model_id = {model_id}")

# =============================================
# 2. Verificar si ya existe la automated action
# =============================================
print("\n2. Verificando si ya existe...")
existing = search_read('base.automation', [['name', '=', AUTOMATION_NAME]], ['id', 'name', 'active'])

if existing:
    auto_id = existing[0]['id']
    print(f"   Ya existe: ID={auto_id}, actualizando...")
    write('base.automation', [auto_id], {
        'active': True,
        'trigger': 'on_write',
        'state': 'code',
        'code': SERVER_CODE,
        'filter_pre_domain': '[("quality_state", "in", ["pass", "fail"]), ("x_studio_titulo_control_calidad", "=", "Control de calidad Recepcion MP")]',
        'filter_domain': '[]',
        'model_id': model_id,
    })
    print(f"   Automated Action actualizada: ID={auto_id}")
else:
    # =============================================
    # 3. Crear la Automated Action
    # =============================================
    print("\n3. Creando Automated Action...")
    auto_id = create('base.automation', {
        'name': AUTOMATION_NAME,
        'model_id': model_id,
        'trigger': 'on_write',
        'state': 'code',
        'code': SERVER_CODE,
        'filter_pre_domain': '[("quality_state", "in", ["pass", "fail"]), ("x_studio_titulo_control_calidad", "=", "Control de calidad Recepcion MP")]',
        'filter_domain': '[]',
        'active': True,
    })
    print(f"   Automated Action creada: ID={auto_id}")

# =============================================
# 4. Verificar la creacion
# =============================================
print("\n4. Verificando...")
verify = search_read('base.automation', [['id', '=', auto_id]], 
    ['id', 'name', 'trigger', 'active', 'filter_domain', 'state', 'code', 'model_name'])
if verify:
    aa = verify[0]
    print(f"   ID: {aa['id']}")
    print(f"   Nombre: {aa['name']}")
    print(f"   Modelo: {aa['model_name']}")
    print(f"   Trigger: {aa['trigger']}")
    print(f"   Active: {aa['active']}")
    print(f"   State: {aa['state']}")
    print(f"   Domain: {aa['filter_domain']}")
    print(f"   Code preview: {str(aa.get('code', ''))[:200]}...")

# =============================================
# 5. Verificar xmlid del grupo
# =============================================
print("\n5. Verificando grupo quality.group_quality_manager...")
group_check = search_read('ir.model.data', 
    [['module', '=', 'quality'], ['name', '=', 'group_quality_manager']], 
    ['id', 'res_id', 'model'], limit=1)
if group_check:
    gid = group_check[0]['res_id']
    group_info = search_read('res.groups', [['id', '=', gid]], ['id', 'name', 'users'], limit=1)
    if group_info:
        users_count = len(group_info[0].get('users', []))
        print(f"   Grupo: {group_info[0]['name']} (ID={gid}) con {users_count} usuarios")
        
        # Listar los usuarios
        if users_count <= 20:
            users = search_read('res.users', [['id', 'in', group_info[0]['users']]], ['id', 'name', 'login'], limit=20)
            for u in users:
                print(f"     -> {u['name']} ({u['login']})")
else:
    print("   ADVERTENCIA: No se encontro xmlid quality.group_quality_manager")

print("\n" + "=" * 80)
print("DESPLIEGUE COMPLETADO EXITOSAMENTE")
print("=" * 80)
print(f"\nResumen:")
print(f"  - Automated Action ID: {auto_id}")
print(f"  - Trigger: on_write")
print(f"  - Aplica a: QCs con estado 'pass'/'fail' Y titulo 'Control de calidad Recepcion MP'")
print(f"  - Grupo autorizado: Quality / Administrator")
print(f"\nUsuarios NO administradores de calidad recibiran un UserError")
print(f"al intentar modificar un QC de Recepcion MP cerrado.")
