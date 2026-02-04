"""
Servicio para generar reportes PDF del Monitor de Producción Diario
"""
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


def generate_monitor_report_pdf(
    fecha_inicio: str,
    fecha_fin: str,
    planta: str,
    sala: str,
    procesos_pendientes: List[Dict],
    procesos_cerrados: List[Dict],
    evolucion: List[Dict],
    totales: Dict[str, Any]
) -> bytes:
    """
    Genera un reporte PDF completo del monitor de producción.
    
    Args:
        fecha_inicio: Fecha inicio del período
        fecha_fin: Fecha fin del período
        planta: Planta filtrada
        sala: Sala filtrada
        procesos_pendientes: Lista de procesos pendientes
        procesos_cerrados: Lista de procesos cerrados
        evolucion: Datos de evolución por día
        totales: Totales calculados
    
    Returns:
        bytes del PDF generado
    """
    buffer = BytesIO()
    
    # Crear documento en landscape para más espacio
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=20,
        textColor=colors.HexColor('#1a365d')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        alignment=TA_LEFT,
        spaceBefore=15,
        spaceAfter=10,
        textColor=colors.HexColor('#2d3748')
    )
    
    info_style = ParagraphStyle(
        'InfoStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a5568')
    )
    
    elements = []
    
    # === ENCABEZADO ===
    elements.append(Paragraph("📊 Reporte Monitor de Producción Diario", title_style))
    elements.append(Paragraph(
        f"Período: {fecha_inicio} al {fecha_fin} | Planta: {planta} | Sala: {sala}",
        info_style
    ))
    elements.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        info_style
    ))
    elements.append(Spacer(1, 20))
    
    # === RESUMEN EJECUTIVO ===
    elements.append(Paragraph("📈 Resumen Ejecutivo", subtitle_style))
    
    total_pendientes = len(procesos_pendientes)
    total_cerrados = len(procesos_cerrados)
    kg_pendientes = sum(p.get('product_qty', 0) - p.get('qty_produced', 0) for p in procesos_pendientes)
    kg_producidos = totales.get('total_kg_producidos', 0)
    
    resumen_data = [
        ['Métrica', 'Valor'],
        ['Total Procesos Pendientes', str(total_pendientes)],
        ['KG Pendientes', f"{kg_pendientes:,.0f} kg"],
        ['Total Procesos Cerrados (período)', str(total_cerrados)],
        ['KG Producidos (período)', f"{kg_producidos:,.0f} kg"],
        ['Promedio Procesos/Día', f"{totales.get('total_creados', 0) / max(len(evolucion), 1):.1f}"],
    ]
    
    resumen_table = Table(resumen_data, colWidths=[3*inch, 2*inch])
    resumen_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f7fafc')),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f7fafc')]),
    ]))
    elements.append(resumen_table)
    elements.append(Spacer(1, 20))
    
    # === EVOLUCIÓN DIARIA ===
    if evolucion:
        elements.append(Paragraph("📅 Evolución Diaria de Procesos", subtitle_style))
        
        evol_header = ['Fecha', 'Creados', 'Cerrados', 'KG Programados', 'KG Producidos', 'Balance']
        evol_data = [evol_header]
        
        for e in evolucion:
            evol_data.append([
                e.get('fecha_display', ''),
                str(e.get('procesos_creados', 0)),
                str(e.get('procesos_cerrados', 0)),
                f"{e.get('kg_programados', 0):,.0f}",
                f"{e.get('kg_producidos', 0):,.0f}",
                str(e.get('pendientes_acumulados', 0))
            ])
        
        # Fila de totales
        evol_data.append([
            'TOTAL',
            str(totales.get('total_creados', 0)),
            str(totales.get('total_cerrados', 0)),
            f"{totales.get('total_kg_programados', 0):,.0f}",
            f"{totales.get('total_kg_producidos', 0):,.0f}",
            str(totales.get('total_creados', 0) - totales.get('total_cerrados', 0))
        ])
        
        evol_table = Table(evol_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1.5*inch, 1.5*inch, 1*inch])
        evol_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3182ce')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#ebf8ff')]),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#2d3748')),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        elements.append(evol_table)
        elements.append(Spacer(1, 20))
    
    # === PROCESOS PENDIENTES ===
    if procesos_pendientes:
        elements.append(Paragraph("🔄 Detalle de Procesos Pendientes", subtitle_style))
        
        pend_header = ['OF', 'Producto', 'Sala', 'KG Prog.', 'KG Prod.', 'Pendiente', '% Avance']
        pend_data = [pend_header]
        
        for p in procesos_pendientes[:30]:  # Limitar a 30 para el PDF
            producto = p.get('product_id', {})
            if isinstance(producto, dict):
                prod_name = producto.get('name', 'N/A')[:35]
            else:
                prod_name = str(producto)[:35]
            
            kg_prog = p.get('product_qty', 0) or 0
            kg_prod = p.get('qty_produced', 0) or 0
            pendiente = kg_prog - kg_prod
            avance = (kg_prod / kg_prog * 100) if kg_prog > 0 else 0
            
            pend_data.append([
                str(p.get('name', ''))[:15],
                prod_name,
                str(p.get('x_studio_sala_de_proceso', 'N/A'))[:20],
                f"{kg_prog:,.0f}",
                f"{kg_prod:,.0f}",
                f"{pendiente:,.0f}",
                f"{avance:.1f}%"
            ])
        
        if len(procesos_pendientes) > 30:
            pend_data.append([f"... y {len(procesos_pendientes) - 30} más", '', '', '', '', '', ''])
        
        pend_table = Table(pend_data, colWidths=[1*inch, 2.5*inch, 1.5*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
        pend_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e53e3e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
        ]))
        elements.append(pend_table)
        elements.append(Spacer(1, 20))
    
    # === PROCESOS CERRADOS ===
    if procesos_cerrados:
        elements.append(Paragraph("✅ Detalle de Procesos Cerrados (en el período)", subtitle_style))
        
        cerr_header = ['OF', 'Producto', 'Sala', 'KG Producidos', 'Fecha Cierre']
        cerr_data = [cerr_header]
        
        for p in procesos_cerrados[:30]:
            producto = p.get('product_id', {})
            if isinstance(producto, dict):
                prod_name = producto.get('name', 'N/A')[:35]
            else:
                prod_name = str(producto)[:35]
            
            fecha_cierre = p.get('date_finished', '')
            if fecha_cierre:
                try:
                    fecha_cierre = datetime.strptime(fecha_cierre[:10], '%Y-%m-%d').strftime('%d/%m/%Y')
                except:
                    pass
            
            cerr_data.append([
                str(p.get('name', ''))[:15],
                prod_name,
                str(p.get('x_studio_sala_de_proceso', 'N/A'))[:20],
                f"{p.get('qty_produced', 0):,.0f}",
                fecha_cierre[:10] if fecha_cierre else 'N/A'
            ])
        
        if len(procesos_cerrados) > 30:
            cerr_data.append([f"... y {len(procesos_cerrados) - 30} más", '', '', '', ''])
        
        cerr_table = Table(cerr_data, colWidths=[1.2*inch, 3*inch, 1.8*inch, 1.3*inch, 1.2*inch])
        cerr_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#38a169')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0fff4')]),
        ]))
        elements.append(cerr_table)
    
    # === PIE DE PÁGINA ===
    elements.append(Spacer(1, 30))
    elements.append(Paragraph(
        "Rio Futuro - Sistema de Dashboards | Monitor de Producción",
        info_style
    ))
    
    # Generar PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
