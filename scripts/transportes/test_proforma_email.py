"""
Script de prueba para generar y visualizar el correo de proforma
Genera un ejemplo del PDF y HTML template que se envía a los transportistas
"""

import io
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

# Datos de prueba
datos_prueba = {
    'TRANSPORTES RODRIGUEZ LIMITADA': {
        'ocs': [
            {
                'oc_name': 'PO00123',
                'fecha': '2026-01-15',
                'ruta': 'San José - La Granja',
                'kms': 450,
                'kilos': 12500,
                'costo': 225000,
                'costo_por_km': 500,
                'tipo_camion': '🚛 Camión 12-14 Ton'
            },
            {
                'oc_name': 'PO00145',
                'fecha': '2026-01-20',
                'ruta': 'Temuco - La Granja',
                'kms': 680,
                'kilos': 18000,
                'costo': 340000,
                'costo_por_km': 500,
                'tipo_camion': '🚛 Camión 12-14 Ton'
            },
            {
                'oc_name': 'PO00167',
                'fecha': '2026-01-28',
                'ruta': 'Curicó - La Granja',
                'kms': 250,
                'kilos': 9000,
                'costo': 125000,
                'costo_por_km': 500,
                'tipo_camion': '🚚 Camión 8 Ton'
            }
        ],
        'totales': {
            'kms': 1380,
            'kilos': 39500,
            'costo': 690000
        }
    }
}

fecha_desde_str = '2026-01-01'
fecha_hasta_str = '2026-01-31'


def generar_pdf_proforma_test():
    """Genera PDF de prueba"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=11,
        spaceAfter=6,
        alignment=TA_CENTER
    )
    
    transportista_style = ParagraphStyle(
        'Transportista',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#2c5aa0'),
        spaceAfter=8,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    for transportista, data in datos_prueba.items():
        # Header principal
        story.append(Paragraph("PROFORMA CONSOLIDADA DE FLETES", title_style))
        story.append(Paragraph(f"Período: {fecha_desde_str} al {fecha_hasta_str}", subtitle_style))
        story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", subtitle_style))
        story.append(Spacer(1, 0.3*inch))
        
        # Nombre del transportista
        story.append(Paragraph(f"Transportista: {transportista}", transportista_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Tabla de datos
        table_data = [
            ['OC', 'Fecha', 'Ruta', 'Kms', 'Kilos', 'Costo', '$/km', 'Tipo Camión']
        ]
        
        for oc_data in data['ocs']:
            table_data.append([
                oc_data['oc_name'],
                oc_data['fecha'],
                oc_data['ruta'][:25] if oc_data['ruta'] else 'Sin ruta',
                f"{oc_data['kms']:.0f}" if oc_data['kms'] else '0',
                f"{oc_data['kilos']:.1f}" if oc_data['kilos'] else '0',
                f"${oc_data['costo']:,.0f}",
                f"${oc_data['costo_por_km']:.0f}" if oc_data['costo_por_km'] else '$0',
                oc_data['tipo_camion'][:15] if oc_data['tipo_camion'] else 'N/A'
            ])
        
        # Fila de totales
        promedio_km = data['totales']['costo'] / data['totales']['kms'] if data['totales']['kms'] > 0 else 0
        table_data.append([
            'TOTALES',
            '',
            '',
            f"{data['totales']['kms']:.0f}",
            f"{data['totales']['kilos']:.1f}",
            f"${data['totales']['costo']:,.0f}",
            f"${promedio_km:.0f}",
            ''
        ])
        
        # Crear tabla
        table = Table(table_data, colWidths=[0.8*inch, 0.8*inch, 1.5*inch, 0.6*inch, 0.6*inch, 0.9*inch, 0.7*inch, 1.1*inch])
        
        # Estilo de tabla
        table.setStyle(TableStyle([
            # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4a90e2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Datos
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            
            # Totales (última fila)
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d3d3d3')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 9),
            
            # Bordes
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('LINEBELOW', (0, 0), (-1, 0), 2, colors.HexColor('#4a90e2')),
            ('LINEABOVE', (0, -1), (-1, -1), 2, colors.grey),
        ]))
        
        story.append(table)
        
        # Info adicional
        story.append(Spacer(1, 0.3*inch))
        info_text = f"Total de OCs: {len(data['ocs'])} | Total Kms: {data['totales']['kms']:,.0f} | Total Kilos: {data['totales']['kilos']:,.1f}"
        story.append(Paragraph(info_text, subtitle_style))
    
    # Construir PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def generar_html_template_test():
    """Genera template HTML de prueba"""
    transportista = 'TRANSPORTES RODRIGUEZ LIMITADA'
    data = datos_prueba[transportista]
    cant_ocs = len(data['ocs'])
    total_costo = data['totales']['costo']
    
    mensaje_html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .header {{ background-color: #1f4788; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .summary {{ background-color: #f0f0f0; padding: 15px; margin: 20px 0; border-radius: 5px; }}
            .footer {{ text-align: center; color: #666; padding: 20px; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Proforma Consolidada de Fletes</h2>
        </div>
        <div class="content">
            <p>Estimado/a,</p>
            <p>Adjuntamos la proforma consolidada de servicios de flete correspondiente al período <strong>{fecha_desde_str}</strong> al <strong>{fecha_hasta_str}</strong>.</p>
            
            <div class="summary">
                <h3>Resumen del Período</h3>
                <ul>
                    <li><strong>Cantidad de Órdenes de Compra:</strong> {cant_ocs}</li>
                    <li><strong>Total Kilómetros:</strong> {data['totales']['kms']:,.0f} km</li>
                    <li><strong>Total Kilos:</strong> {data['totales']['kilos']:,.1f} kg</li>
                    <li><strong>Monto Total:</strong> ${total_costo:,.0f}</li>
                </ul>
            </div>
            
            <p>En el documento adjunto encontrará el detalle completo de todas las órdenes de compra incluidas en este período.</p>
            
            <p>Cualquier consulta, no dude en contactarnos.</p>
            
            <p>Saludos cordiales,<br>
            <strong>Río Futuro</strong></p>
        </div>
        <div class="footer">
            Este es un correo automático generado por el sistema de gestión de Río Futuro.<br>
            Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}
        </div>
    </body>
    </html>
    """
    return mensaje_html


if __name__ == '__main__':
    print("=" * 80)
    print("GENERANDO PROFORMA DE PRUEBA")
    print("=" * 80)
    
    # Generar PDF
    print("\n1. Generando PDF...")
    pdf_bytes = generar_pdf_proforma_test()
    pdf_filename = f'proforma_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
    with open(pdf_filename, 'wb') as f:
        f.write(pdf_bytes)
    print(f"   ✅ PDF generado: {pdf_filename}")
    print(f"   📊 Tamaño: {len(pdf_bytes):,} bytes")
    
    # Generar HTML
    print("\n2. Generando template HTML...")
    html_content = generar_html_template_test()
    html_filename = f'proforma_email_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    print(f"   ✅ HTML generado: {html_filename}")
    print(f"   📧 Tamaño: {len(html_content):,} caracteres")
    
    print("\n" + "=" * 80)
    print("RESUMEN DEL CORREO QUE SE ENVIARÍA:")
    print("=" * 80)
    print(f"Para: TRANSPORTES RODRIGUEZ LIMITADA")
    print(f"Asunto: Proforma Consolidada de Fletes - {fecha_desde_str} al {fecha_hasta_str}")
    print(f"Adjuntos: Proforma_Fletes_{fecha_desde_str}_{fecha_hasta_str}.pdf")
    print("\nContenido:")
    print("- Header corporativo azul (color #1f4788)")
    print("- Saludo personalizado")
    print("- Resumen del período:")
    print(f"  • {len(datos_prueba['TRANSPORTES RODRIGUEZ LIMITADA']['ocs'])} OCs")
    print(f"  • {datos_prueba['TRANSPORTES RODRIGUEZ LIMITADA']['totales']['kms']:,.0f} km")
    print(f"  • {datos_prueba['TRANSPORTES RODRIGUEZ LIMITADA']['totales']['kilos']:,.1f} kg")
    print(f"  • ${datos_prueba['TRANSPORTES RODRIGUEZ LIMITADA']['totales']['costo']:,.0f}")
    print("- Mensaje profesional")
    print("- Footer con timestamp")
    
    print("\n✅ Archivos generados exitosamente!")
    print("   Puedes abrirlos para revisar el formato y contenido exacto.")
