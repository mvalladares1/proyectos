"""
Debug v2: Identificar el modelo correcto y probar la automation
===============================================================
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
# 1. Buscar QC16101 (el que el usuario está editando)
# =============================================
print("=" * 70)
print("1. BUSCAR QC16101")
print("=" * 70)

qc = search_read('quality.check', [['name', '=', 'QC16101']], 
    ['id', 'name', 'quality_state', 'x_studio_titulo_control_calidad',
     'x_studio_frambuesa', 'x_studio_frutilla', 'x_studio_mp',
     'x_studio_one2many_field_ipdDS', 'x_studio_one2many_field_rgA7I',
     'x_studio_one2many_field_RdQtm', 'x_studio_one2many_field_eNeCg',
     'x_studio_one2many_field_nsxt0', 'x_studio_one2many_field_vloaS',
     'x_studio_one2many_field_3jSXq', 'x_studio_one2many_field_mZmK2'],
    limit=1)

if qc:
    q = qc[0]
    print(f"  QC: {q['name']} (ID={q['id']}) | state={q['quality_state']}")
    print(f"  Tipo: {q['x_studio_titulo_control_calidad']}")
    
    # Mostrar cada one2many y cuantas lineas tiene
    o2m_fields = {
        'x_studio_frambuesa': 'x_quality_check_line_14b00',
        'x_studio_frutilla': 'x_quality_check_line_89a53',
        'x_studio_mp': 'x_quality_check_line_19657',
        'x_studio_one2many_field_ipdDS': 'x_quality_check_line_35406 (Arandano)',
        'x_studio_one2many_field_rgA7I': 'x_quality_check_line_1d183 (Frambuesa/Mora)',
        'x_studio_one2many_field_RdQtm': 'x_quality_check_line_2efd1 (Lineas nuevas)',
        'x_studio_one2many_field_eNeCg': 'x_quality_check_line_0d011 (Lineas nuevas)',
        'x_studio_one2many_field_nsxt0': 'x_quality_check_line_17bfb (Lineas nuevas)',
        'x_studio_one2many_field_vloaS': 'x_quality_check_line_f0f7b (Lineas nuevas)',
        'x_studio_one2many_field_3jSXq': 'x_quality_check_line_2a594 (Despacho)',
        'x_studio_one2many_field_mZmK2': 'x_quality_check_line_46726',
    }
    
    for field_name, model_name in o2m_fields.items():
        ids = q.get(field_name, [])
        if ids:
            print(f"  {field_name} -> {model_name}: {len(ids)} lineas (IDs: {ids[:5]})")

# =============================================
# 2. Buscar campos de los modelos con "dao_mecanico" o "inmadura"
# =============================================
print(f"\n{'='*70}")
print("2. BUSCAR CAMPOS 'dao_mecanico' e 'inmadura' EN TODOS LOS MODELOS HIJOS")
print(f"{'='*70}")

child_model_names = [
    'x_quality_check_line_14b00',
    'x_quality_check_line_89a53',
    'x_quality_check_line_19657',
    'x_quality_check_line_35406',
    'x_quality_check_line_1d183',
    'x_quality_check_line_2efd1',
    'x_quality_check_line_0d011',
    'x_quality_check_line_17bfb',
    'x_quality_check_line_f0f7b',
    'x_quality_check_line_2a594',
    'x_quality_check_line_46726',
]

for cm in child_model_names:
    try:
        cf = models.execute_kw(db, uid, password, cm, 'fields_get', [],
            {'attributes': ['string', 'type']})
        
        # Buscar campos específicos
        relevant = {k: v for k, v in cf.items() 
                    if 'mecanico' in k.lower() or 'mecanico' in v.get('string', '').lower()
                    or 'inmadu' in k.lower() or 'inmadu' in v.get('string', '').lower()
                    or 'dao_mec' in k.lower()
                    or k == 'x_studio_inmadura_1' or k == 'x_studio_inmadura'}
        
        if relevant:
            print(f"\n  {cm}:")
            for k, v in relevant.items():
                print(f"    {k}: {v['type']} | '{v['string']}'")
    except Exception as e:
        print(f"\n  {cm}: ERROR - {str(e)[:60]}")

# =============================================
# 3. Verificar cuál modelo corresponde a "Líneas nuevas Frambuesa"
# =============================================
print(f"\n{'='*70}")
print("3. MODELO QUE CORRESPONDE A 'Lineas nuevas Frambuesa'")
print(f"{'='*70}")

# Buscar por el campo x_studio_one2many que tiene los records del QC16101
if qc:
    qc_id = qc[0]['id']
    
    # Probar cada modelo con registros del QC16101
    for cm in child_model_names:
        try:
            recs = search_read(cm, [['x_quality_check_id', '=', qc_id]], ['id', 'x_name'], limit=5)
            if recs:
                # Intentar leer campos específicos que aparecen en el screenshot
                fields_to_check = []
                cf = models.execute_kw(db, uid, password, cm, 'fields_get', [],
                    {'attributes': ['string', 'type']})
                
                for fname, finfo in cf.items():
                    label_lower = finfo.get('string', '').lower()
                    if 'inmadura' in label_lower or 'daño mecanico' in label_lower or 'sobremaduros' in label_lower or 'drupeolo' in label_lower:
                        fields_to_check.append(fname)
                
                if fields_to_check:
                    print(f"\n  {cm}: {len(recs)} registros con parent QC16101")
                    print(f"    Campos relevantes encontrados: {fields_to_check}")
                    # Leer primer registro con esos campos
                    sample = search_read(cm, [['x_quality_check_id', '=', qc_id]], 
                        ['id', 'x_name'] + fields_to_check, limit=1)
                    if sample:
                        print(f"    Sample: {sample[0]}")
        except Exception as e:
            pass

# =============================================
# 4. Probar si la automation tiene error de runtime
# =============================================
print(f"\n{'='*70}")
print("4. VERIFICAR ERRORES DE LA AUTOMATION")
print(f"{'='*70}")

# Buscar errores recientes
try:
    errors = search_read('ir.logging',
        [['type', '=', 'server'], ['level', 'in', ['ERROR', 'WARNING']]],
        ['name', 'message', 'create_date', 'func', 'path', 'line'],
        limit=15, order='id desc')
    
    if errors:
        for e in errors:
            msg = str(e.get('message', ''))[:200]
            if 'audit' in msg.lower() or 'automation' in msg.lower() or 'datetime' in msg.lower() or 'quality' in msg.lower() or 'RF:' in msg:
                print(f"  [{e.get('create_date')}] {e.get('name')}")
                print(f"    {msg}")
                print()
    else:
        print("  No hay errores recientes")
except Exception as ex:
    # Try looking for traceback in another way
    print(f"  No se puede acceder a ir.logging: {str(ex)[:100]}")
    
    # Check mail.mail for error notifications
    try:
        mail_errors = search_read('mail.mail', 
            [['state', '=', 'exception']],
            ['email_to', 'subject', 'body_html', 'failure_reason'],
            limit=5, order='id desc')
        if mail_errors:
            print(f"\n  Correos con error: {len(mail_errors)}")
            for m in mail_errors:
                print(f"    Subject: {m.get('subject', '')[:80]}")
    except:
        pass

print(f"\n{'='*70}")
print("DEBUG v2 COMPLETADO")
print(f"{'='*70}")
