"""
Fix v3: Columnas reales + mensajes no-borrables
================================================
1. Valida columnas vs information_schema antes de SQL
2. Usa sudo().message_post() para que el autor sea OdooBot (no borrable)
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
models_proxy = xmlrpc_client.ServerProxy(f'{url}/xmlrpc/2/object')
print(f"Conectado como UID={uid}")

def search_read(model, domain, fields, limit=500, order=None):
    kwargs = {'fields': fields, 'limit': limit}
    if order:
        kwargs['order'] = order
    return models_proxy.execute_kw(db, uid, password, model, 'search_read', [domain], kwargs)

ALL_CHILD_MODELS = {
    'x_quality_check_line_35406': 'Arandano',
    'x_quality_check_line_1d183': 'Frambuesa/Mora',
    'x_quality_check_line_14b00': 'Frambuesa',
    'x_quality_check_line_89a53': 'Frutilla',
    'x_quality_check_line_19657': 'MP',
    'x_quality_check_line_46726': 'Lineas nuevas Frambuesa',
    'x_quality_check_line_2efd1': 'Lineas nuevas 1',
    'x_quality_check_line_0d011': 'Lineas nuevas 2',
    'x_quality_check_line_17bfb': 'Lineas nuevas 3',
    'x_quality_check_line_f0f7b': 'Lineas nuevas 4',
    'x_quality_check_line_2a594': 'Despacho PT',
}

for child_model, label in ALL_CHILD_MODELS.items():
    automation_name = f"RF: Audit linea {label}"
    
    print(f"\n{'='*60}")
    print(f"  {label} ({child_model})")
    print(f"{'='*60}")
    
    model_info = search_read('ir.model', [['model', '=', child_model]], ['id'], limit=1)
    if not model_info:
        print(f"  SKIP: Modelo no encontrado")
        continue
    child_model_id = model_info[0]['id']
    
    child_fields = models_proxy.execute_kw(db, uid, password, child_model, 'fields_get', [],
        {'attributes': ['string', 'type', 'readonly', 'store', 'related', 'compute']})
    if 'x_quality_check_id' not in child_fields:
        print(f"  SKIP: Sin campo padre")
        continue
    
    # Solo campos que son STORED, NO readonly, NO computed, NO related
    editable_fields = {}
    trigger_field_names = []
    for fname, finfo in child_fields.items():
        if not fname.startswith('x_studio'):
            continue
        if finfo.get('readonly', False):
            continue
        if not finfo.get('store', True):
            continue
        ftype = finfo.get('type', '')
        if ftype in ('one2many', 'many2many', 'binary'):
            continue
        # Excluir campos computed y related (no son columnas reales)
        if finfo.get('compute') or finfo.get('related'):
            continue
        editable_fields[fname] = finfo['string']
        trigger_field_names.append(fname)
    
    if not editable_fields:
        print(f"  SKIP: Sin campos editables")
        continue
    
    field_records = search_read('ir.model.fields',
        [['model', '=', child_model], ['name', 'in', trigger_field_names]],
        ['id'], limit=100)
    trigger_ids = [f['id'] for f in field_records]
    
    labels_dict_str = repr(editable_fields)
    campos_list_str = repr(list(editable_fields.keys()))
    
    # Código mejorado: valida columnas reales + sudo() para no-borrable
    audit_code = f'''# RF: Audit detallado - {label}
TABLE = '{child_model}'
CAMPOS = {campos_list_str}
LABELS = {labels_dict_str}

for rec in records:
    parent = rec.x_quality_check_id
    if not parent:
        continue
    if parent.x_studio_titulo_control_calidad != 'Control de calidad Recepcion MP':
        continue

    changes = []
    try:
        new_cr = env.registry.cursor()
        try:
            # Obtener columnas REALES de la tabla
            new_cr.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (TABLE,)
            )
            real_cols = set(r[0] for r in new_cr.fetchall())
            valid = [c for c in CAMPOS if c in real_cols]

            if valid:
                cols_sql = ', '.join(valid)
                new_cr.execute("SELECT " + cols_sql + " FROM " + TABLE + " WHERE id = %s", (rec.id,))
                old_row = new_cr.fetchone()
                if old_row:
                    for i, fname in enumerate(valid):
                        old_val = old_row[i]
                        new_val = rec[fname]
                        if str(old_val or '') != str(new_val or ''):
                            lbl = LABELS.get(fname, fname)
                            changes.append(
                                "<li><b>" + lbl + "</b>: " +
                                str(old_val if old_val is not None else '') +
                                " &#8594; " +
                                str(new_val if new_val is not None else '') +
                                "</li>"
                            )
        finally:
            new_cr.close()
    except Exception as e:
        changes = ["<li>Linea modificada (error: " + str(e)[:60] + ")</li>"]

    if changes:
        linea = rec.x_name or str(rec.id)
        body = "<p><b>&#9998; Linea {label} [" + str(linea) + "] modificada por " + env.user.name + ":</b></p>"
        body += "<ul>" + "".join(changes) + "</ul>"
        # sudo() para que el autor sea OdooBot -> no borrable por usuarios
        parent.sudo().message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
'''
    
    existing = search_read('base.automation', [['name', '=', automation_name]], ['id'], limit=1)
    
    if existing:
        auto_id = existing[0]['id']
        models_proxy.execute_kw(db, uid, password, 'base.automation', 'write', [[auto_id], {
            'code': audit_code,
            'trigger_field_ids': [(6, 0, trigger_ids)],
        }])
        print(f"  ACTUALIZADA: ID={auto_id} | {len(trigger_ids)} triggers | {len(editable_fields)} labels")
    else:
        auto_id = models_proxy.execute_kw(db, uid, password, 'base.automation', 'create', [{
            'name': automation_name,
            'model_id': child_model_id,
            'trigger': 'on_write',
            'state': 'code',
            'code': audit_code,
            'active': True,
            'trigger_field_ids': [(6, 0, trigger_ids)],
        }])
        print(f"  CREADA: ID={auto_id} | {len(trigger_ids)} triggers | {len(editable_fields)} labels")

# También actualizar las automations ON CREATE para usar sudo()
print(f"\n{'='*60}")
print("  Actualizando ON CREATE para usar sudo() (no-borrable)")
print(f"{'='*60}")

for child_model, label in ALL_CHILD_MODELS.items():
    automation_name = f"RF: Audit nueva linea {label}"
    existing = search_read('base.automation', [['name', '=', automation_name]], ['id'], limit=1)
    if not existing:
        continue
    
    create_code = f'''# RF: Audit nueva linea {label}
for rec in records:
    parent = rec.x_quality_check_id
    if not parent:
        continue
    if parent.x_studio_titulo_control_calidad != 'Control de calidad Recepcion MP':
        continue
    linea = rec.x_name or str(rec.id)
    body = "<p><b>&#10010; Nueva linea {label} [" + str(linea) + "] creada por " + env.user.name + "</b></p>"
    parent.sudo().message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
'''
    models_proxy.execute_kw(db, uid, password, 'base.automation', 'write', 
        [[existing[0]['id']], {'code': create_code}])
    print(f"  {label}: actualizada (sudo)")

print(f"\n{'='*70}")
print("DESPLIEGUE v3 COMPLETADO")
print(f"{'='*70}")
print(f"\nCambios:")
print(f"  1. Solo usa columnas REALES de la BD (evita error information_schema)")
print(f"  2. sudo().message_post() -> autor es OdooBot -> NO borrable por usuarios")
print(f"  3. message_type='notification' -> protegido contra eliminacion")
