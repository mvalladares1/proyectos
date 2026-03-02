"""
Debug: Explorar modelo quality.check - campos, estados, reglas de acceso, grupos
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

def fields_get(model, attributes=None):
    attrs = attributes or ['string', 'type', 'selection', 'relation', 'required', 'readonly']
    return models.execute_kw(db, uid, password, model, 'fields_get', [], {'attributes': attrs})

# =============================================
# 1. CAMPOS del modelo quality.check
# =============================================
print("\n" + "=" * 80)
print("1. CAMPOS DEL MODELO quality.check")
print("=" * 80)

qc_fields = fields_get('quality.check')
# Campos relevantes
important_fields = ['quality_state', 'name', 'title', 'control_date', 'team_id', 
                    'product_id', 'picking_id', 'lot_id', 'company_id', 'user_id',
                    'write_uid', 'create_uid', 'write_date', 'create_date',
                    'test_type_id', 'test_type', 'point_id', 'measure',
                    'x_studio_']

for fname, finfo in sorted(qc_fields.items()):
    is_important = any(fname.startswith(p) or fname == p for p in important_fields)
    if is_important or fname.startswith('x_'):
        sel = f" | selection={finfo.get('selection')}" if finfo.get('selection') else ""
        rel = f" | relation={finfo.get('relation')}" if finfo.get('relation') else ""
        ro = " | READONLY" if finfo.get('readonly') else ""
        print(f"  {fname}: type={finfo.get('type')} | label='{finfo.get('string')}'{sel}{rel}{ro}")

# =============================================
# 2. REGLAS DE ACCESO (ir.model.access)
# =============================================
print("\n" + "=" * 80)
print("2. REGLAS DE ACCESO (ir.model.access) para quality.check")
print("=" * 80)

# Buscar el model_id para quality.check
model_ids = search_read('ir.model', [['model', '=', 'quality.check']], ['id', 'name'], limit=1)
if model_ids:
    model_id = model_ids[0]['id']
    access_rules = search_read('ir.model.access', 
        [['model_id', '=', model_id]], 
        ['name', 'group_id', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink'],
        limit=50)
    for rule in access_rules:
        group = rule.get('group_id', [False, 'Todos'])[1] if rule.get('group_id') else 'TODOS (sin grupo)'
        print(f"  {rule['name']}: grupo={group} | R={rule['perm_read']} W={rule['perm_write']} C={rule['perm_create']} D={rule['perm_unlink']}")

# =============================================
# 3. REGLAS DE REGISTRO (ir.rule) 
# =============================================
print("\n" + "=" * 80)
print("3. REGLAS DE REGISTRO (ir.rule) para quality.check")
print("=" * 80)

record_rules = search_read('ir.rule', 
    [['model_id', '=', model_id]], 
    ['name', 'domain_force', 'groups', 'perm_read', 'perm_write', 'perm_create', 'perm_unlink', 'active'],
    limit=50)
for rule in record_rules:
    groups = rule.get('groups', [])
    print(f"  Regla: {rule['name']}")
    print(f"    domain={rule.get('domain_force')}")
    print(f"    grupos={groups}")
    print(f"    R={rule['perm_read']} W={rule['perm_write']} C={rule['perm_create']} D={rule['perm_unlink']} active={rule['active']}")

# =============================================
# 4. GRUPOS relacionados con calidad
# =============================================
print("\n" + "=" * 80)
print("4. GRUPOS DE CALIDAD Y PERMISOS")
print("=" * 80)

quality_groups = search_read('res.groups', 
    [['category_id.name', 'ilike', 'calidad']], 
    ['id', 'name', 'full_name', 'category_id', 'implied_ids', 'users'],
    limit=20)

if not quality_groups:
    quality_groups = search_read('res.groups', 
        [['category_id.name', 'ilike', 'quality']], 
        ['id', 'name', 'full_name', 'category_id', 'implied_ids', 'users'],
        limit=20)

if not quality_groups:
    # Buscar por nombre del grupo
    quality_groups = search_read('res.groups', 
        [['name', 'ilike', 'quality']], 
        ['id', 'name', 'full_name', 'category_id', 'implied_ids', 'users'],
        limit=20)

for g in quality_groups:
    user_count = len(g.get('users', []))
    print(f"  [{g['id']}] {g.get('full_name', g['name'])} | users={user_count}")
    if user_count > 0 and user_count <= 20:
        users = search_read('res.users', [['id', 'in', g['users']]], ['id', 'name', 'login'], limit=20)
        for u in users:
            print(f"      -> {u['name']} ({u['login']})")

# =============================================
# 5. EJEMPLO: Quality checks en estado 'pass' o 'fail'
# =============================================
print("\n" + "=" * 80)
print("5. EJEMPLO DE QUALITY CHECKS CERRADOS (aprobados/fallidos)")
print("=" * 80)

closed_qcs = search_read('quality.check', 
    [['quality_state', 'in', ['pass', 'fail']]], 
    ['id', 'name', 'title', 'quality_state', 'control_date', 'product_id', 'team_id', 'picking_id', 'write_uid', 'write_date'],
    limit=5, order='write_date desc')

for qc in closed_qcs:
    print(f"  [{qc['id']}] {qc.get('name', '')} | state={qc['quality_state']} | product={qc.get('product_id', ['',''])[1][:30]}")
    print(f"      ultimo_edit={qc.get('write_uid', ['',''])[1]} | write_date={qc.get('write_date')}")

# =============================================
# 6. MODULOS INSTALADOS de calidad
# =============================================
print("\n" + "=" * 80)
print("6. MODULOS DE CALIDAD INSTALADOS")
print("=" * 80)

quality_modules = search_read('ir.module.module', 
    [['name', 'ilike', 'quality'], ['state', '=', 'installed']], 
    ['name', 'shortdesc', 'state'],
    limit=20)

for m in quality_modules:
    print(f"  {m['name']}: {m['shortdesc']} [{m['state']}]")

# =============================================
# 7. VISTAS del modelo quality.check 
# =============================================
print("\n" + "=" * 80)
print("7. VISTAS DEL MODELO quality.check")
print("=" * 80)

views = search_read('ir.ui.view', 
    [['model', '=', 'quality.check']], 
    ['id', 'name', 'type', 'mode', 'priority', 'active', 'arch_db'],
    limit=30,
    order='type, priority')

for v in views:
    arch_preview = str(v.get('arch_db', ''))[:200] if v.get('arch_db') else 'N/A'
    print(f"  [{v['id']}] {v['name']} | type={v['type']} | mode={v['mode']} | priority={v['priority']} | active={v['active']}")
    if 'attrs' in arch_preview or 'readonly' in arch_preview or 'invisible' in arch_preview:
        print(f"      TIENE attrs/readonly/invisible: {arch_preview[:300]}")

# =============================================
# 8. SERVER ACTIONS y Automated Actions para quality.check
# =============================================
print("\n" + "=" * 80)
print("8. SERVER ACTIONS / AUTOMATED ACTIONS para quality.check")
print("=" * 80)

server_actions = search_read('ir.actions.server', 
    [['model_id', '=', model_id]], 
    ['id', 'name', 'state', 'code'],
    limit=20)

for sa in server_actions:
    print(f"  [{sa['id']}] {sa['name']} | state={sa['state']}")
    if sa.get('code'):
        print(f"      code: {str(sa['code'])[:200]}")

# Automated actions (base.automation)
try:
    auto_actions = search_read('base.automation', 
        [['model_id', '=', model_id]], 
        ['id', 'name', 'trigger', 'active', 'filter_domain'],
        limit=20)
    for aa in auto_actions:
        print(f"  AUTO [{aa['id']}] {aa['name']} | trigger={aa['trigger']} | active={aa['active']}")
        if aa.get('filter_domain'):
            print(f"      domain: {aa['filter_domain']}")
except:
    print("  (base.automation no disponible)")

print("\n" + "=" * 80)
print("DIAGNOSTICO COMPLETADO")
print("=" * 80)
