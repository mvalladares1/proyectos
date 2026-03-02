"""
Fix v2: Restringir trigger_field_ids para que no bloquee picking
================================================================
Problema: Cuando un albarán (stock.picking) se valida, Odoo escribe 
campos del sistema (picking_id, etc.) en QCs ya aprobados. Nuestra 
automated action se dispara y bloquea la operación.

Solución: Agregar trigger_field_ids para que la automation SOLO se 
dispare cuando cambien campos de DATOS editables por el usuario 
(observaciones, defectos, temperatura, etc.), NO campos del sistema
(picking_id, quality_state, write_date, etc.).

También optimiza el código: has_group() se evalúa UNA vez fuera del loop.
"""
import sys
import io
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

def search_read(model, domain, fields, limit=500, order=None):
    kwargs = {'fields': fields, 'limit': limit}
    if order:
        kwargs['order'] = order
    return models.execute_kw(db, uid, password, model, 'search_read', [domain], kwargs)

AUTO_ID = 134

# =============================================
# 1. Obtener TODOS los campos de quality.check
# =============================================
print("\n1. Obteniendo campos editables del modelo quality.check...")
all_fields = models.execute_kw(db, uid, password, 'quality.check', 'fields_get', [], 
    {'attributes': ['string', 'type', 'readonly', 'store']})

# Campos del SISTEMA que NO deben disparar la automation
# (son los que modifican picking, manufacturing, ORM, estado, etc.)
SYSTEM_FIELDS = {
    'picking_id', 'production_id', 'lot_id', 'lot_name',
    'quality_state', 'measure_success',
    'write_date', 'write_uid', 'create_date', 'create_uid',
    'message_main_attachment_id', 'message_ids', 'message_follower_ids',
    'activity_ids', 'activity_state', 'activity_user_id',
    'activity_type_id', 'activity_date_deadline', 'activity_summary',
    'company_id', 'point_id', 'test_type_id', 'test_type',
    'workorder_id', 'finished_product_sequence',
    'product_id', 'move_line_id', 'component_id',
    'team_id', 'user_id', 'name', 'title',
    'additional', 'norm', 'norm_unit', 'measure',
    'picture', 'note', 'failure_message',
    'qty_line', 'qty_to_consume',
    'component_tracking', 'component_is_byproduct',
    'is_expired', 'control_date',
    # Campos Studio que son computed/readonly del sistema
    'x_studio_titulo_control_calidad',
    'x_studio_fecha_recepcion',
    'x_studio_kg_brutos_1', 'x_studio_kg_recepcionados',
    'x_studio_acopio', 'x_studio_acopio_1',
    'x_studio_tipo_de_fruta',
    'x_studio_ficha_control_recepcion',
    'x_studio_gua_de_despacho',
    'x_studio_calific_final', 'x_studio_calificacin_final',
    'x_studio_jefe_de_calidad_y_aseguramiento_',
    # Campos many2one/many2many que el sistema modifica
    'x_studio_many2one_field_IDSox',
    'x_studio_many2one_field_dXiL5',
    'x_studio_many2one_field_i5IZ5',
    'x_studio_many2one_field_s7ZJZ',
    'x_studio_many2one_field_xfEyu',
    'x_studio_many2one_field_9pP0l',
    'x_studio_many2one_field_wqxf5',
    'x_studio_many2many_field_3IgmX',
    'x_studio_many2many_field_QonKy',
    'x_studio_many2many_field_S8gTE',
    'x_studio_many2many_field_mQUKA',
    'x_studio_many2many_field_wqxf5',
    'x_studio_related_field_DuBi8',
    'x_studio_related_field_clMwF',
    'x_studio_related_field_j9bxJ',
    'x_studio_related_field_qRMS8',
}

# Campos de DATOS editables por el usuario (los que SÍ deben disparar la automation)
data_fields = []
for fname, finfo in all_fields.items():
    if fname in SYSTEM_FIELDS:
        continue
    if fname.startswith('__'):
        continue
    # Solo campos stored y no readonly (editables por usuario)
    ftype = finfo.get('type', '')
    is_readonly = finfo.get('readonly', False)
    is_stored = finfo.get('store', True)
    
    # Incluir campos editables (no readonly) que son stored
    # También incluir campos x_studio editables
    if not is_readonly and is_stored and ftype not in ('one2many',):
        data_fields.append(fname)

print(f"   Total campos quality.check: {len(all_fields)}")
print(f"   Campos sistema (excluidos): {len(SYSTEM_FIELDS)}")
print(f"   Campos datos (trigger): {len(data_fields)}")

# Obtener los ir.model.fields IDs para estos campos
print("\n2. Obteniendo IDs de ir.model.fields...")
field_records = search_read('ir.model.fields', 
    [['model', '=', 'quality.check'], ['name', 'in', data_fields]], 
    ['id', 'name', 'field_description'],
    limit=500)

trigger_field_ids = [f['id'] for f in field_records]
print(f"   Fields encontrados en ir.model.fields: {len(trigger_field_ids)}")

# Mostrar algunos ejemplos
print("\n   Ejemplos de campos que dispararán la automation:")
for f in field_records[:15]:
    print(f"     [{f['id']}] {f['name']} ({f['field_description']})")
if len(field_records) > 15:
    print(f"     ... y {len(field_records) - 15} campos más")

# =============================================
# 3. Código optimizado del servidor
# =============================================
OPTIMIZED_CODE = '''# RF: Bloquear edicion de QC cerrados (Recepcion MP)
# has_group() se evalua UNA sola vez (mismo usuario en todo el request)
if not env.user.has_group('quality.group_quality_manager'):
    for rec in records:
        if rec.quality_state in ('pass', 'fail') and rec.x_studio_titulo_control_calidad == 'Control de calidad Recepcion MP':
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
# 4. Actualizar la automated action
# =============================================
print(f"\n3. Actualizando Automated Action ID={AUTO_ID}...")
result = models.execute_kw(db, uid, password, 'base.automation', 'write', [[AUTO_ID], {
    'code': OPTIMIZED_CODE,
    'trigger_field_ids': [(6, 0, trigger_field_ids)],  # Solo disparar con cambios a campos de datos
}])
print(f"   Write result: {result}")

# =============================================
# 5. Verificar
# =============================================
print(f"\n4. Verificando...")
verify = search_read('base.automation', [['id', '=', AUTO_ID]], 
    ['name', 'active', 'trigger', 'filter_domain', 'filter_pre_domain', 
     'trigger_field_ids', 'code'], limit=1)

if verify:
    v = verify[0]
    print(f"   Nombre: {v['name']}")
    print(f"   Active: {v['active']}")
    print(f"   Trigger: {v['trigger']}")
    print(f"   filter_pre_domain: {v['filter_pre_domain']}")
    print(f"   trigger_field_ids: {len(v['trigger_field_ids'])} campos configurados")
    print(f"   Código (preview): {v['code'][:150]}...")

print(f"\n{'='*70}")
print("FIX APLICADO")
print(f"{'='*70}")
print(f"\nCambios:")
print(f"  1. trigger_field_ids: {len(trigger_field_ids)} campos de DATOS (excluye picking_id, quality_state, etc.)")
print(f"  2. Código optimizado: has_group() evaluado UNA vez fuera del loop")
print(f"\nAhora:")
print(f"  - Validar picking -> escribe picking_id en QC cerrado -> NO dispara automation -> OK")
print(f"  - Editar datos de QC cerrado manualmente -> SÍ dispara automation -> BLOQUEADO")
print(f"  - Quality Admin edita QC cerrado -> SÍ dispara pero has_group pasa -> PERMITIDO")
