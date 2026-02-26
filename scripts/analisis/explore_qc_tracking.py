"""
Explorar: Tracking y modelos hijos de quality.check
====================================================
1. Verificar si ir.model.fields tiene campo 'tracking'
2. Identificar campos clave de quality.check para tracking
3. Identificar modelos hijos (líneas de análisis)
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from xmlrpc import client as xmlrpc_client

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

# =============================================
# 1. ¿ir.model.fields tiene campo 'tracking'?
# =============================================
print("=" * 70)
print("1. CAMPO 'tracking' EN ir.model.fields")
print("=" * 70)

imf_fields = models.execute_kw(db, uid, password, 'ir.model.fields', 'fields_get', [],
    {'attributes': ['string', 'type']})

tracking_related = {k: v for k, v in imf_fields.items() if 'track' in k.lower()}
print(f"Campos con 'track' en ir.model.fields: {len(tracking_related)}")
for k, v in tracking_related.items():
    print(f"  {k}: type={v['type']} | label='{v['string']}'")

# =============================================
# 2. Verificar tracking actual en quality.check
# =============================================
print("\n" + "=" * 70)
print("2. TRACKING ACTUAL EN quality.check")
print("=" * 70)

if 'tracking' in imf_fields:
    tracked_fields = search_read('ir.model.fields',
        [['model', '=', 'quality.check'], ['tracking', '!=', 0]],
        ['name', 'field_description', 'tracking', 'ttype'],
        limit=100)
    print(f"Campos con tracking activo: {len(tracked_fields)}")
    for f in tracked_fields:
        print(f"  {f['name']}: tracking={f['tracking']} | {f['field_description']} ({f['ttype']})")
else:
    print("  Campo 'tracking' NO existe en ir.model.fields")

# =============================================
# 3. Modelos hijos (líneas de análisis)
# =============================================
print("\n" + "=" * 70)
print("3. MODELOS HIJOS (one2many en quality.check)")
print("=" * 70)

qc_fields_all = models.execute_kw(db, uid, password, 'quality.check', 'fields_get', [],
    {'attributes': ['string', 'type', 'relation']})

o2m_fields = {k: v for k, v in qc_fields_all.items() if v.get('type') == 'one2many'}
print(f"Campos one2many: {len(o2m_fields)}")
for k, v in sorted(o2m_fields.items()):
    print(f"  {k}: relation={v['relation']} | label='{v['string']}'")

# =============================================
# 4. Explorar campos de los modelos hijos clave
# =============================================
print("\n" + "=" * 70)
print("4. CAMPOS DE MODELOS HIJOS (análisis de calidad)")
print("=" * 70)

# Los modelos hijos principales (de la notebook Calidad)
child_models = [
    ('x_studio_one2many_field_ipdDS', 'x_quality_check_line_35406', 'Arandano'),
    ('x_studio_one2many_field_rgA7I', 'x_quality_check_line_1d183', 'Frambuesa o Mora'),
    ('x_studio_frambuesa', 'x_quality_check_line_14b00', 'Frambuesa'),
    ('x_studio_frutilla', 'x_quality_check_line_89a53', 'Frutilla'),
    ('x_studio_mp', 'x_quality_check_line_19657', 'MP'),
]

for field_name, model_name, label in child_models:
    print(f"\n  --- {label} ({model_name}) ---")
    try:
        child_fields = models.execute_kw(db, uid, password, model_name, 'fields_get', [],
            {'attributes': ['string', 'type', 'readonly', 'store']})
        editable_fields = []
        for fname, finfo in sorted(child_fields.items()):
            if fname.startswith('x_') and not finfo.get('readonly', False) and finfo.get('store', True):
                editable_fields.append(fname)
                if len(editable_fields) <= 10:
                    print(f"    {fname}: {finfo['type']} | '{finfo['string']}'")
        if len(editable_fields) > 10:
            print(f"    ... y {len(editable_fields) - 10} campos more")
        print(f"  Total campos editables: {len(editable_fields)}")
    except Exception as e:
        print(f"    ERROR: {str(e)[:100]}")

# =============================================
# 5. ¿quality.check hereda de mail.thread?
# =============================================
print("\n" + "=" * 70)
print("5. ¿quality.check HEREDA de mail.thread (chatter)?")
print("=" * 70)

# Check if message_post is available
has_chatter = 'message_ids' in qc_fields_all
print(f"  Tiene message_ids (chatter): {has_chatter}")
print(f"  Tiene message_follower_ids: {'message_follower_ids' in qc_fields_all}")

# Try to read a message from a QC
if has_chatter:
    qc_with_msgs = search_read('quality.check', 
        [['quality_state', '=', 'pass'], ['x_studio_titulo_control_calidad', '=', 'Control de calidad Recepcion MP']],
        ['id', 'name', 'message_ids'],
        limit=1, order='id desc')
    if qc_with_msgs:
        msg_ids = qc_with_msgs[0].get('message_ids', [])
        print(f"  QC {qc_with_msgs[0]['name']}: {len(msg_ids)} mensajes en chatter")
        if msg_ids:
            msgs = search_read('mail.message', [['id', 'in', msg_ids[:3]]], 
                ['id', 'body', 'message_type', 'subtype_id', 'tracking_value_ids', 'author_id', 'date'],
                limit=3)
            for m in msgs:
                print(f"    msg[{m['id']}] type={m['message_type']} | tracking_values={m.get('tracking_value_ids')} | {str(m.get('body',''))[:80]}")

print("\n" + "=" * 70)
print("EXPLORACION COMPLETADA")
print("=" * 70)
