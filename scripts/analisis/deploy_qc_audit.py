"""
Fix v6: Snapshot de valores actuales (safe_eval compatible)
============================================================
safe_eval de Odoo bloquea env.registry.cursor() e imports.
No es posible leer valores anteriores desde la automation.

Solución: Registra TODOS los valores actuales del registro modificado
como snapshot. Comparando snapshots consecutivos se puede ver qué cambió.
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

def get_editable_fields(child_model):
    child_fields = models_proxy.execute_kw(db, uid, password, child_model, 'fields_get', [],
        {'attributes': ['string', 'type', 'readonly', 'store']})
    if 'x_quality_check_id' not in child_fields:
        return None, []
    candidates = {}
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
        # Solo tipos con valores simples que se puedan mostrar
        if ftype in ('float', 'integer', 'char', 'text', 'selection', 'boolean', 'date', 'datetime'):
            candidates[fname] = {'label': finfo['string'], 'type': ftype}
    return candidates, list(candidates.keys())

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
        print(f"  SKIP: No encontrado")
        continue
    child_model_id = model_info[0]['id']
    
    field_info, trigger_field_names = get_editable_fields(child_model)
    if field_info is None:
        print(f"  SKIP: Sin campo padre")
        continue
    if not field_info:
        print(f"  SKIP: Sin campos")
        continue
    
    print(f"  Campos: {len(field_info)}")
    
    field_records = search_read('ir.model.fields',
        [['model', '=', child_model], ['name', 'in', trigger_field_names]],
        ['id'], limit=100)
    trigger_ids = [f['id'] for f in field_records]
    
    # Separar campos numéricos (float/int) de texto para mejor presentación
    numeric_fields = {k: v for k, v in field_info.items() if v['type'] in ('float', 'integer')}
    other_fields = {k: v for k, v in field_info.items() if v['type'] not in ('float', 'integer')}
    
    campos_list_str = repr(list(field_info.keys()))
    labels_dict_str = repr({k: v['label'] for k, v in field_info.items()})
    numeric_list_str = repr(list(numeric_fields.keys()))
    
    # Código simple, safe_eval compatible
    # Muestra snapshot de valores numéricos (que son los importantes en QC)
    audit_code = f'''# RF: Audit v6 - {label}
CAMPOS = {campos_list_str}
LABELS = {labels_dict_str}
NUMERICOS = {numeric_list_str}

for rec in records:
    parent = rec.x_quality_check_id
    if not parent:
        continue
    if parent.x_studio_titulo_control_calidad != 'Control de calidad Recepcion MP':
        continue

    linea = rec.x_name or str(rec.id)
    
    # Construir tabla con valores actuales (solo los que tienen valor)
    rows = []
    for fname in CAMPOS:
        val = rec[fname]
        if val is not None and val is not False and str(val).strip() and str(val) != '0' and str(val) != '0.0':
            lbl = LABELS.get(fname, fname)
            rows.append("<tr><td><b>" + lbl + "</b></td><td>" + str(val) + "</td></tr>")
    
    if rows:
        body = "<p><b>&#9998; Linea {label} [" + str(linea) + "] modificada por " + env.user.name + "</b></p>"
        body += "<table border='1' style='border-collapse:collapse;font-size:12px;'>"
        body += "<tr><th>Campo</th><th>Valor actual</th></tr>"
        body += "".join(rows)
        body += "</table>"
    else:
        body = "<p><b>&#9998; Linea {label} [" + str(linea) + "] modificada por " + env.user.name + "</b></p>"
    
    parent.sudo().message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
'''
    
    existing = search_read('base.automation', [['name', '=', automation_name]], ['id'], limit=1)
    
    if existing:
        auto_id = existing[0]['id']
        models_proxy.execute_kw(db, uid, password, 'base.automation', 'write', [[auto_id], {
            'code': audit_code,
            'trigger_field_ids': [(6, 0, trigger_ids)],
        }])
        print(f"  ACTUALIZADA: ID={auto_id}")
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
        print(f"  CREADA: ID={auto_id}")

print(f"\n{'='*70}")
print("DESPLIEGUE v6 COMPLETADO")
print(f"{'='*70}")
print(f"\nCambio: Muestra tabla con valores actuales despues de cada edicion")
print(f"Comparando dos entradas consecutivas se puede ver que cambio")
