"""
Crear herencias QWeb para mostrar Fecha OC en factura proveedor
=================================================================

Este script crea las vistas heredadas directamente en Odoo via API.
Agrega:
1. Campo "Fecha(s) OC" en header (sección informaciones)
2. Columna "Fecha OC" en tabla de líneas de producto

USO: python aplicar_fecha_oc_reporte.py
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 80)
print("APLICAR FECHA OC EN REPORTE DE FACTURA PROVEEDOR")
print("=" * 80)

# ============================================================
# Verificar si ya existen las herencias
# ============================================================
existing = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['name', 'in', [
        'l10n_cl.informations.po_date',
        'account.report_invoice_document.po_date_column'
    ]]]],
    {'fields': ['id', 'name', 'active']}
)

if existing:
    print("\n⚠️  Ya existen herencias previas:")
    for e in existing:
        print(f"   ID: {e['id']} | {e['name']} | active: {e['active']}")
    
    respuesta = input("\n¿Desea eliminar las existentes y recrear? (s/n): ")
    if respuesta.lower() == 's':
        for e in existing:
            models.execute_kw(db, uid, password, 'ir.ui.view', 'unlink', [[e['id']]])
            print(f"   ✅ Eliminada vista ID: {e['id']}")
    else:
        print("   Cancelado. No se aplicaron cambios.")
        exit()

# ============================================================
# HERENCIA 1: Fecha OC en header (l10n_cl.informations)
# ============================================================
print("\n" + "-" * 80)
print("PASO 1: Crear herencia para HEADER (sección informaciones)")
print("-" * 80)

# Obtener ID del template base
template_info = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search',
    [[['key', '=', 'l10n_cl.informations']]]
)

if template_info:
    arch_header = '''<data inherit_id="l10n_cl.informations" priority="99">
    <xpath expr="//div[@id='informations']/div[2]" position="inside">
        
        <t t-set="po_orders" t-value="o.invoice_line_ids.mapped('purchase_order_id')"/>
        <t t-set="po_dates" t-value="[po.date_order for po in po_orders if po.date_order]"/>
        
        <t t-if="po_dates">
            <br/>
            <strong>Fecha(s) OC:</strong>
            <t t-if="len(set(str(d)[:10] for d in po_dates)) == 1">
                <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
            </t>
            <t t-else="">
                <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
                <span> - </span>
                <span t-esc="max(po_dates)" t-options="{'widget': 'date'}"/>
            </t>
        </t>
        
    </xpath>
</data>'''

    try:
        new_view_id = models.execute_kw(db, uid, password,
            'ir.ui.view', 'create',
            [{
                'name': 'l10n_cl.informations.po_date',
                'type': 'qweb',
                'inherit_id': template_info[0],
                'arch_db': arch_header,
                'priority': 99,
                'active': True
            }]
        )
        print(f"✅ Creada herencia para header: ir.ui.view ID {new_view_id}")
    except Exception as e:
        print(f"❌ Error creando herencia header: {e}")
else:
    print("⚠️  No se encontró template l10n_cl.informations")

# ============================================================
# HERENCIA 2: Columna Fecha OC en tabla de líneas
# ============================================================
print("\n" + "-" * 80)
print("PASO 2: Crear herencia para TABLA DE LÍNEAS")
print("-" * 80)

template_doc = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search',
    [[['key', '=', 'account.report_invoice_document']]]
)

if template_doc:
    arch_table = '''<data inherit_id="account.report_invoice_document" priority="99">
    
    <xpath expr="//table//thead//th[@name='th_description']" position="after">
        <th name="th_po_date" class="text-start">Fecha OC</th>
    </xpath>
    
    <xpath expr="//table//tbody//td[@name='td_name']" position="after">
        <td name="td_po_date" class="text-start">
            <t t-if="line.purchase_order_id">
                <span t-esc="line.purchase_order_id.date_order" t-options="{'widget': 'date'}"/>
            </t>
        </td>
    </xpath>
    
</data>'''

    try:
        new_view_id = models.execute_kw(db, uid, password,
            'ir.ui.view', 'create',
            [{
                'name': 'account.report_invoice_document.po_date_column',
                'type': 'qweb',
                'inherit_id': template_doc[0],
                'arch_db': arch_table,
                'priority': 99,
                'active': True
            }]
        )
        print(f"✅ Creada herencia para tabla: ir.ui.view ID {new_view_id}")
    except Exception as e:
        print(f"❌ Error creando herencia tabla: {e}")
else:
    print("⚠️  No se encontró template account.report_invoice_document")


# ============================================================
# Verificación final
# ============================================================
print("\n" + "=" * 80)
print("VERIFICACIÓN FINAL")
print("=" * 80)

vistas_creadas = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['name', 'in', [
        'l10n_cl.informations.po_date',
        'account.report_invoice_document.po_date_column'
    ]]]],
    {'fields': ['id', 'name', 'active', 'inherit_id', 'priority']}
)

print(f"\n✅ Vistas creadas: {len(vistas_creadas)}")
for v in vistas_creadas:
    print(f"   ID: {v['id']}")
    print(f"   Nombre: {v['name']}")
    print(f"   Hereda de: {v['inherit_id']}")
    print(f"   Prioridad: {v['priority']}")
    print(f"   Activa: {v['active']}")
    print()

print("\n🎉 COMPLETADO!")
print("   Abre una factura de proveedor con OC vinculada y genera el PDF.")
print("   Deberías ver:")
print("   - 'Fecha(s) OC' en la cabecera (junto a Due Date)")
print("   - Columna 'Fecha OC' en la tabla de líneas")
