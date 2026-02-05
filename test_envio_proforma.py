"""
Test de envío de proforma a correo de prueba
Envía la proforma FAC 000001 a mvalladares@riofuturo.cl
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import get_facturas_borrador, enviar_proforma_email
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
import io

# Credenciales (API Key)
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("🧪 TEST: Envío de Proforma a Correo de Prueba")
print("=" * 70)

# 1. Buscar la factura FAC 000001
print("\n1️⃣ Buscando factura FAC 000001...")
try:
    facturas = get_facturas_borrador(USERNAME, PASSWORD)
    
    factura_test = None
    for f in facturas:
        if f['nombre'] == 'FAC 000001':
            factura_test = f
            break
    
    if not factura_test:
        print("❌ No se encontró la factura FAC 000001")
        print(f"   Facturas disponibles: {', '.join([f['nombre'] for f in facturas[:5]])}")
        sys.exit(1)
    
    print(f"✅ Factura encontrada:")
    print(f"   ID: {factura_test['id']}")
    print(f"   Nombre: {factura_test['nombre']}")
    print(f"   Proveedor: {factura_test['proveedor_nombre']}")
    print(f"   Total USD: ${factura_test['total_usd']:,.2f}")
    print(f"   Total CLP: ${factura_test['total_clp']:,.0f}")
    print(f"   Líneas: {factura_test['num_lineas']}")
    
except Exception as e:
    print(f"❌ Error obteniendo factura: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Generar PDF
print("\n2️⃣ Generando PDF...")

def generar_pdf_test(factura: dict) -> bytes:
    """Genera PDF de prueba."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                          topMargin=0.5*inch, bottomMargin=0.5*inch,
                          leftMargin=0.5*inch, rightMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('CustomTitle', 
                                parent=styles['Heading1'], 
                                fontSize=18, 
                                alignment=TA_CENTER,
                                textColor=colors.HexColor('#2E7D32'),
                                spaceAfter=20)
    
    elements = []
    
    # Título
    elements.append(Paragraph("PROFORMA DE PROVEEDOR - TEST", title_style))
    elements.append(Spacer(1, 12))
    
    # Información
    info_data = [
        ["Factura:", factura['nombre'], "", "Fecha:", factura.get('fecha_factura', '-')],
        ["Proveedor:", factura['proveedor_nombre'][:50], "", "Moneda:", "USD / CLP"],
        ["TEST:", "ENVIADO A mvalladares@riofuturo.cl", "", "TC:", f"{factura['tipo_cambio']:,.2f}"],
    ]
    
    info_table = Table(info_data, colWidths=[1*inch, 3*inch, 0.5*inch, 1*inch, 1.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tabla de líneas
    table_data = [["Descripción", "Cantidad", "P.Unit\nUSD", "P.Unit\nCLP", "Subtotal\nUSD", "Subtotal\nCLP"]]
    
    for linea in factura['lineas'][:10]:  # Max 10 líneas para test
        cant = linea['cantidad']
        p_unit_clp = linea['subtotal_clp'] / cant if cant else 0
        
        table_data.append([
            linea['nombre'][:45] if linea['nombre'] else "-",
            f"{cant:,.2f}",
            f"${linea['precio_usd']:,.2f}",
            f"${p_unit_clp:,.0f}",
            f"${linea['subtotal_usd']:,.2f}",
            f"${linea['subtotal_clp']:,.0f}"
        ])
    
    table_data.append(["", "", "", "", "", ""])
    table_data.append(["", "", "", "Base:", f"${factura['base_usd']:,.2f}", f"${factura['base_clp']:,.0f}"])
    table_data.append(["", "", "", "IVA 19%:", f"${factura['iva_usd']:,.2f}", f"${factura['iva_clp']:,.0f}"])
    table_data.append(["", "", "", "TOTAL:", f"${factura['total_usd']:,.2f}", f"${factura['total_clp']:,.0f}"])
    
    main_table = Table(table_data, colWidths=[3.5*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1.0*inch, 1.0*inch])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, len(factura['lineas'][:10])), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (3, -3), (-1, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (3, -3), (-1, -3), 1.5, colors.black),
    ]))
    elements.append(main_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()

try:
    pdf_bytes = generar_pdf_test(factura_test)
    print(f"✅ PDF generado: {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"❌ Error generando PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Enviar por correo
print("\n3️⃣ Enviando proforma a mvalladares@riofuturo.cl...")

try:
    resultado = enviar_proforma_email(
        username=USERNAME,
        password=PASSWORD,
        factura_id=factura_test['id'],
        email_destino="mvalladares@riofuturo.cl",  # EMAIL DE PRUEBA
        pdf_bytes=pdf_bytes,
        nombre_factura=factura_test['nombre'],
        proveedor_nombre=f"TEST - {factura_test['proveedor_nombre']}"
    )
    
    if resultado.get("success"):
        print(f"✅ Proforma enviada exitosamente!")
        print(f"   Mail ID: {resultado.get('mail_id')}")
        print(f"   Attachment ID: {resultado.get('attachment_id')}")
        print(f"   Destinatario: {resultado.get('email_destino')}")
        print("\n📧 Revisa tu correo: mvalladares@riofuturo.cl")
        print("   Asunto: Proforma FAC 000001 - Rio Futuro")
    else:
        print(f"❌ Error al enviar: {resultado.get('error')}")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ Test completado")
print("=" * 70)
