"""
Generar PDF de factura proveedor y adjuntarlo al chatter (sin enviar email)
Factura: FAC 000849
"""
import xmlrpc.client
import base64
from datetime import datetime

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

print("=" * 100)
print("GENERAR PDF DE FACTURA PROVEEDOR")
print("=" * 100)

# ============================================================
# PASO 1: Buscar la factura FAC 000849
# ============================================================
print("\n" + "-" * 80)
print("PASO 1: Buscar factura FAC 000849")
print("-" * 80)

factura = models.execute_kw(db, uid, password,
    'account.move', 'search_read',
    [[['name', 'ilike', 'FAC 000849']]],
    {'fields': ['id', 'name', 'move_type', 'partner_id', 'invoice_origin', 'state'], 'limit': 1}
)

if not factura:
    print("❌ No se encontró la factura FAC 000849")
    exit()

factura = factura[0]
factura_id = factura['id']
print(f"\n✅ Factura encontrada:")
print(f"   ID: {factura_id}")
print(f"   Nombre: {factura['name']}")
print(f"   Tipo: {factura['move_type']}")
print(f"   Proveedor: {factura['partner_id']}")
print(f"   Origen: {factura['invoice_origin']}")
print(f"   Estado: {factura['state']}")

# ============================================================
# PASO 2: Generar el PDF usando ir.actions.report
# ============================================================
print("\n" + "-" * 80)
print("PASO 2: Generar PDF del reporte")
print("-" * 80)

# Buscar el reporte de factura
reportes = models.execute_kw(db, uid, password,
    'ir.actions.report', 'search_read',
    [[
        ['model', '=', 'account.move'],
        ['report_type', '=', 'qweb-pdf'],
        ['report_name', 'ilike', 'invoice']
    ]],
    {'fields': ['id', 'name', 'report_name'], 'limit': 10}
)

print(f"\n📊 Reportes disponibles:")
for r in reportes:
    print(f"   ID: {r['id']} | {r['name']} | {r['report_name']}")

# Usar el reporte principal de factura con pagos
reporte_id = None
for r in reportes:
    if 'with_payments' in r['report_name'] and 'copy' not in r['report_name']:
        reporte_id = r['id']
        reporte_name = r['report_name']
        break

if not reporte_id:
    # Usar el primero disponible
    reporte_id = reportes[0]['id']
    reporte_name = reportes[0]['report_name']

print(f"\n🔧 Usando reporte: {reporte_name} (ID: {reporte_id})")

# ============================================================
# PASO 3: Renderizar el PDF
# ============================================================
print("\n" + "-" * 80)
print("PASO 3: Renderizar PDF")
print("-" * 80)

try:
    # Método 1: Usar _render_qweb_pdf via report
    pdf_data = models.execute_kw(db, uid, password,
        'ir.actions.report', 'render_qweb_pdf',
        [[reporte_id], [factura_id]],
        {}
    )
    
    if pdf_data:
        # El resultado es [pdf_bytes_base64, tipo]
        if isinstance(pdf_data, (list, tuple)):
            pdf_content = pdf_data[0]
            if isinstance(pdf_content, str):
                pdf_bytes = base64.b64decode(pdf_content)
            else:
                pdf_bytes = pdf_content
        else:
            pdf_bytes = pdf_data
            
        print(f"✅ PDF generado: {len(pdf_bytes)} bytes")
        
except Exception as e:
    print(f"⚠️  Método directo falló: {e}")
    print("\n🔄 Intentando método alternativo...")
    
    try:
        # Método alternativo: usar report_action
        pdf_data = models.execute_kw(db, uid, password,
            'ir.actions.report', '_render_qweb_pdf',
            [reporte_name, [factura_id]],
            {}
        )
        
        if pdf_data:
            pdf_bytes = pdf_data[0] if isinstance(pdf_data, tuple) else pdf_data
            print(f"✅ PDF generado (método alt): {len(pdf_bytes)} bytes")
    except Exception as e2:
        print(f"❌ Error alternativo: {e2}")
        pdf_bytes = None

# ============================================================
# PASO 4: Guardar localmente Y adjuntar al chatter
# ============================================================
if pdf_bytes:
    print("\n" + "-" * 80)
    print("PASO 4: Guardar PDF y adjuntar al chatter")
    print("-" * 80)
    
    # Guardar localmente
    filename = f"FAC_000849_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    filepath = f"c:/new/RIO FUTURO/DASHBOARD/proyectos/scripts/analisis/{filename}"
    
    # Si pdf_bytes es base64, decodificar
    if isinstance(pdf_bytes, str):
        pdf_bytes = base64.b64decode(pdf_bytes)
    
    with open(filepath, 'wb') as f:
        f.write(pdf_bytes)
    print(f"✅ PDF guardado localmente: {filepath}")
    
    # Adjuntar al chatter como attachment
    attachment_id = models.execute_kw(db, uid, password,
        'ir.attachment', 'create',
        [{
            'name': f'Factura_Proveedor_{factura["name"]}_TEST.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_bytes).decode('utf-8'),
            'res_model': 'account.move',
            'res_id': factura_id,
            'mimetype': 'application/pdf'
        }]
    )
    print(f"✅ Adjunto creado en chatter: ir.attachment ID {attachment_id}")
    
    # Crear mensaje en el chatter
    mensaje_id = models.execute_kw(db, uid, password,
        'mail.message', 'create',
        [{
            'body': '<p>📄 <b>PDF de prueba generado</b><br/>Este PDF incluye los cambios de "Fecha OC" en el reporte.</p>',
            'model': 'account.move',
            'res_id': factura_id,
            'message_type': 'notification',
            'subtype_id': 2,  # Note
            'attachment_ids': [(6, 0, [attachment_id])]
        }]
    )
    print(f"✅ Mensaje creado en chatter: mail.message ID {mensaje_id}")
    
    print("\n" + "=" * 100)
    print("🎉 COMPLETADO")
    print("=" * 100)
    print(f"\n📂 PDF guardado en: {filepath}")
    print(f"📎 PDF adjunto al chatter de: {factura['name']}")
    print(f"\n   Abre la factura en Odoo para ver el PDF en el chatter")
    
else:
    print("\n❌ No se pudo generar el PDF")
    print("   Intenta previsualizar manualmente desde Odoo")
