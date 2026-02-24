"""
CORREGIR: Agregar columna Fecha OC en tabla de líneas (xpath corregido)
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
print("AGREGAR COLUMNA FECHA OC EN TABLA DE LÍNEAS")
print("=" * 80)

# Verificar si ya existe
existing = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['name', '=', 'account.report_invoice_document.po_date_column']]],
    {'fields': ['id', 'name']}
)

if existing:
    print(f"\n⚠️  Ya existe la herencia. Eliminando ID: {existing[0]['id']}")
    models.execute_kw(db, uid, password, 'ir.ui.view', 'unlink', [[existing[0]['id']]])

# Obtener ID del template base
template_doc = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search',
    [[['key', '=', 'account.report_invoice_document']]]
)

if template_doc:
    # Xpath corregido basado en la estructura real del template
    arch_table = '''<data inherit_id="account.report_invoice_document" priority="99">
    
    <!-- Agregar header de columna después de Description -->
    <xpath expr="//th[@name='th_description']" position="after">
        <th name="th_po_date" class="text-start">Fecha OC</th>
    </xpath>
    
    <!-- Agregar celda de datos después del nombre de línea -->
    <xpath expr="//td[@name='account_invoice_line_name']" position="after">
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
        print(f"\n✅ Creada herencia para tabla: ir.ui.view ID {new_view_id}")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
        # Si falla, intentar con un xpath alternativo más simple
        print("\n🔄 Intentando xpath alternativo...")
        
        arch_table_alt = '''<data inherit_id="account.report_invoice_document" priority="99">
    
    <!-- Agregar header de columna -->
    <xpath expr="//table[@name='invoice_line_table']/thead/tr/th[@name='th_description']" position="after">
        <th name="th_po_date" class="text-start">Fecha OC</th>
    </xpath>
    
    <!-- Agregar celda después del nombre - usando posición relativa -->
    <xpath expr="//t[@name='account_invoice_line_accountable']/td[1]" position="after">
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
                    'arch_db': arch_table_alt,
                    'priority': 99,
                    'active': True
                }]
            )
            print(f"✅ Creada herencia (xpath alternativo): ir.ui.view ID {new_view_id}")
        except Exception as e2:
            print(f"❌ Error alternativo: {e2}")

else:
    print("❌ No se encontró template account.report_invoice_document")


# Verificación
print("\n" + "=" * 80)
print("VERIFICACIÓN FINAL")
print("=" * 80)

vistas = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search_read',
    [[['name', 'in', [
        'l10n_cl.informations.po_date',
        'account.report_invoice_document.po_date_column'
    ]]]],
    {'fields': ['id', 'name', 'active', 'inherit_id']}
)

print(f"\n✅ Vistas activas: {len(vistas)}")
for v in vistas:
    print(f"   ID: {v['id']} | {v['name']} | hereda de: {v['inherit_id']}")
