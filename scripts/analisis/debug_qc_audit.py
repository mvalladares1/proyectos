"""
Diagnostico: Probar lectura de valores anteriores via nueva transaccion
=======================================================================
Simula lo que la automation haría: abre cursor nuevo, lee valores con ORM.
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
# 1. Obtener el codigo actual de la automation
# =============================================
print("=" * 70)
print("1. CODIGO ACTUAL DE LA AUTOMATION")
print("=" * 70)

auto = search_read('base.automation', 
    [['name', '=', 'RF: Audit linea Lineas nuevas Frambuesa']],
    ['id', 'code'], limit=1)
if auto:
    print(f"  ID: {auto[0]['id']}")
    print(f"  Code:\n{auto[0]['code']}")

# =============================================
# 2. Actualizar para mostrar error real
# =============================================
print(f"\n{'='*70}")
print("2. ACTUALIZANDO PARA MOSTRAR ERROR REAL")
print(f"{'='*70}")

# Código temporal que muestra el error completo
debug_code = '''# RF: Audit DEBUG - Lineas nuevas Frambuesa
import traceback as tb

MODEL = 'x_quality_check_line_46726'
CAMPOS = ['x_studio_frutos_inmaduros', 'x_studio_dao_mecanico', 'x_studio_frutos_sobre_maduros', 'x_studio_drupeolos_blancos']
LABELS = {'x_studio_frutos_inmaduros': 'Inmadura(grs)', 'x_studio_dao_mecanico': 'Daño Mecanico', 'x_studio_frutos_sobre_maduros': 'Sobremaduros(grs)', 'x_studio_drupeolos_blancos': 'Drupeolos blancos'}

for rec in records:
    parent = rec.x_quality_check_id
    if not parent:
        continue
    if parent.x_studio_titulo_control_calidad != 'Control de calidad Recepcion MP':
        continue

    changes = []
    error_msg = ''
    try:
        new_cr = env.registry.cursor()
        try:
            new_env = env(cr=new_cr)
            old_rec = new_env[MODEL].browse(rec.id)
            old_vals = old_rec.read(CAMPOS)
            if old_vals:
                old_data = old_vals[0]
                for fname in CAMPOS:
                    old_val = old_data.get(fname)
                    new_val = rec[fname]
                    if isinstance(old_val, (list, tuple)):
                        old_val = old_val[0] if old_val else False
                    old_s = str(old_val) if old_val is not None and old_val is not False else ''
                    new_s = str(new_val) if new_val is not None and new_val is not False else ''
                    if old_s != new_s:
                        lbl = LABELS.get(fname, fname)
                        changes.append("<li><b>" + lbl + "</b>: " + old_s + " &#8594; " + new_s + "</li>")
            else:
                error_msg = 'read() retorno vacio'
        finally:
            new_cr.close()
    except Exception as e:
        error_msg = str(e) + " | " + tb.format_exc()[-200:]

    linea = rec.x_name or str(rec.id)
    if changes:
        body = "<p><b>&#9998; Linea [" + str(linea) + "] modificada por " + env.user.name + ":</b></p>"
        body += "<ul>" + "".join(changes) + "</ul>"
    elif error_msg:
        body = "<p><b>&#9998; DEBUG ERROR [" + str(linea) + "]:</b></p><pre>" + error_msg + "</pre>"
    else:
        body = "<p><b>&#9998; Linea [" + str(linea) + "] modificada por " + env.user.name + " (sin cambios detectados en campos monitoreados)</b></p>"
    
    parent.sudo().message_post(body=body, message_type='notification', subtype_xmlid='mail.mt_note')
'''

auto_id = auto[0]['id']
result = models.execute_kw(db, uid, password, 'base.automation', 'write', 
    [[auto_id], {'code': debug_code}])
print(f"  Actualizada ID={auto_id}: {result}")
print(f"\nAhora edita un campo en Lineas nuevas Frambuesa y mira el chatter")
print(f"Mostrara el error completo para diagnosticar")
