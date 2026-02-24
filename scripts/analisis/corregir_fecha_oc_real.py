"""
CORREGIR: Columna "Fecha Recepción" → "Fecha OC" con date_order correcto
Template: l10n_cl.report_invoice_document_copy_1_copy_2 (ID 4735)
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

TEMPLATE_ID = 4735

print("=" * 100)
print("CORREGIR COLUMNA FECHA EN TEMPLATE DE FACTURA")
print("=" * 100)

# Obtener template actual
template = models.execute_kw(db, uid, password,
    'ir.ui.view', 'read',
    [[TEMPLATE_ID]],
    {'fields': ['arch_db', 'name', 'key']}
)

if not template:
    print("❌ Template no encontrado")
    exit()

arch = template[0]['arch_db']
print(f"\n📄 Template: {template[0]['name']}")
print(f"   Key: {template[0]['key']}")

# ============================================================
# CORRECCIÓN 1: Cambiar header "Fecha Recepción" → "Fecha OC"
# ============================================================
arch_new = arch.replace(
    '<th><span>Fecha Recepción</span></th>',
    '<th><span>Fecha OC</span></th>'
)

# ============================================================
# CORRECCIÓN 2: Cambiar la celda de fecha para usar purchase_order_id.date_order
# ============================================================

# Buscar el bloque problemático de fecha recepción
old_fecha_block = '''<!-- 🟦 Fecha Recepción -->
                                    <td>
                                        <t t-if="line.purchase_line_id                                                 and line.purchase_line_id.order_id                                                 and line.purchase_line_id.order_id.picking_ids">
                                            <span t-field="line.purchase_line_id.order_id.picking_ids[0].date" t-options-widget="'date'"/>
                                        </t>
                                        <t t-else="">—</t>
                                    </td>'''

new_fecha_block = '''<!-- 🟦 Fecha OC (date_planned de la línea de compra) -->
                                    <td>
                                        <t t-if="line.purchase_line_id and line.purchase_line_id.date_planned">
                                            <span t-esc="line.purchase_line_id.date_planned" t-options="{'widget': 'date'}"/>
                                        </t>
                                        <t t-else="">—</t>
                                    </td>'''

if old_fecha_block in arch_new:
    arch_new = arch_new.replace(old_fecha_block, new_fecha_block)
    print("\n✅ Bloque de fecha reemplazado correctamente")
else:
    # Intentar con variantes de espaciado
    print("\n⚠️  Bloque exacto no encontrado, intentando reemplazo flexible...")
    
    # Buscar y reemplazar usando regex-like approach
    import re
    
    # Patrón más flexible
    pattern = r'<!-- 🟦 Fecha Recepción -->.*?<td>.*?picking_ids\[0\]\.date.*?</td>'
    replacement = '''<!-- 🟦 Fecha OC (date_planned de la línea de compra) -->
                                    <td>
                                        <t t-if="line.purchase_line_id and line.purchase_line_id.date_planned">
                                            <span t-esc="line.purchase_line_id.date_planned" t-options="{'widget': 'date'}"/>
                                        </t>
                                        <t t-else="">—</t>
                                    </td>'''
    
    arch_new_test = re.sub(pattern, replacement, arch_new, flags=re.DOTALL)
    
    if arch_new_test != arch_new:
        arch_new = arch_new_test
        print("✅ Reemplazo flexible exitoso")
    else:
        # Reemplazo línea por línea
        print("⚠️  Intentando reemplazo línea por línea...")
        
        # Cambiar la línea específica del picking
        arch_new = arch_new.replace(
            'line.purchase_line_id.order_id.picking_ids[0].date',
            'line.purchase_line_id.date_planned'
        )
        
        # Cambiar la condición del t-if
        arch_new = arch_new.replace(
            't-if="line.purchase_line_id                                                 and line.purchase_line_id.order_id                                                 and line.purchase_line_id.order_id.picking_ids"',
            't-if="line.purchase_line_id and line.purchase_line_id.date_planned"'
        )
        
        # Cambiar el comentario
        arch_new = arch_new.replace(
            '<!-- 🟦 Fecha Recepción -->',
            '<!-- 🟦 Fecha OC -->'
        )
        
        print("✅ Reemplazo línea por línea aplicado")

# ============================================================
# Verificar cambios
# ============================================================
if arch_new != arch:
    print("\n📝 Cambios detectados:")
    
    # Mostrar el fragmento nuevo
    if 'Fecha OC' in arch_new:
        print("   ✓ Header cambiado a 'Fecha OC'")
    if 'purchase_line_id.date_planned' in arch_new:
        print("   ✓ Celda usa purchase_line_id.date_planned")
    
    # Aplicar cambios
    print("\n🔧 Aplicando cambios...")
    
    try:
        result = models.execute_kw(db, uid, password,
            'ir.ui.view', 'write',
            [[TEMPLATE_ID], {'arch_db': arch_new}]
        )
        
        if result:
            print(f"✅ Template ID {TEMPLATE_ID} actualizado correctamente")
        else:
            print("❌ No se pudo actualizar")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        
        # Guardar para revisión manual
        with open('template_corregido_4735.xml', 'w', encoding='utf-8') as f:
            f.write(arch_new)
        print("📄 Template guardado en: template_corregido_4735.xml")
        print("   Aplicar manualmente en Odoo si es necesario")
else:
    print("\n⚠️  No se detectaron cambios a aplicar")


# ============================================================
# Verificación final
# ============================================================
print("\n" + "-" * 80)
print("VERIFICACIÓN")
print("-" * 80)

template_verificar = models.execute_kw(db, uid, password,
    'ir.ui.view', 'read',
    [[TEMPLATE_ID]],
    {'fields': ['arch_db']}
)

arch_final = template_verificar[0]['arch_db']

checks = [
    ('Header "Fecha OC"', 'Fecha OC</span></th>' in arch_final),
    ('Usa purchase_line_id.date_planned', 'purchase_line_id.date_planned' in arch_final),
    ('No usa picking_ids[0].date', 'picking_ids[0].date' not in arch_final),
]

for check_name, passed in checks:
    status = "✅" if passed else "❌"
    print(f"   {status} {check_name}")

print("\n🎉 COMPLETADO - Intenta previsualizar el PDF de FAC 000849 nuevamente")
