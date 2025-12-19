"""
Servicio de generación de informes PDF para Producción.
Genera reportes de rendimiento productivo con KPIs, tablas y gráficos.
"""
from typing import List, Dict, Any, Optional
from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.units import cm, mm


# --- Funciones de formateo chileno ---
def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal"""
    if valor is None:
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


def fmt_porcentaje(valor, decimales=1):
    """Formatea porcentaje"""
    return f"{fmt_numero(valor, decimales)}%"


def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, str) and len(fecha_str) >= 10:
            dt = datetime.strptime(fecha_str[:10], "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        return str(fecha_str)
    except:
        return str(fecha_str)


def generate_produccion_report_pdf(
    overview: Dict[str, Any],
    consolidado: Dict[str, Any],
    mos: List[Dict[str, Any]],
    salas: List[Dict[str, Any]],
    fecha_inicio: str,
    fecha_fin: str,
    logo_path: Optional[str] = None
) -> bytes:
    """
    Genera un PDF con el informe de rendimiento de producción.
    
    Args:
        overview: KPIs consolidados del período
        consolidado: Datos por fruta/manejo
        mos: Lista de MOs con rendimiento
        salas: Productividad por sala
        fecha_inicio: Fecha inicio del período
        fecha_fin: Fecha fin del período
        logo_path: Ruta opcional al logo
    
    Returns:
        bytes del PDF generado
    """
    buffer = BytesIO()
    
    # Usar orientación horizontal para más espacio en tablas
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1.5*cm,
        rightMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor('#1a1a2e')
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceBefore=16,
        spaceAfter=8,
        textColor=colors.HexColor('#16213e')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10
    )
    
    # Contenido
    elements = []
    
    # === TÍTULO ===
    elements.append(Paragraph(
        f"📊 Informe de Producción",
        title_style
    ))
    elements.append(Paragraph(
        f"Período: {fmt_fecha(fecha_inicio)} al {fmt_fecha(fecha_fin)}",
        normal_style
    ))
    elements.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        normal_style
    ))
    elements.append(Spacer(1, 0.5*cm))
    
    # === KPIs CONSOLIDADOS ===
    if overview:
        elements.append(Paragraph("KPIs Consolidados del Período", subtitle_style))
        
        kpi_data = [
            ['Kg MP', 'Kg PT', 'Rendimiento', 'Merma', 'Kg/HH', 'MOs', 'Lotes'],
            [
                fmt_numero(overview.get('total_kg_mp', 0)),
                fmt_numero(overview.get('total_kg_pt', 0)),
                fmt_porcentaje(overview.get('rendimiento_promedio', 0)),
                fmt_numero(overview.get('merma_total_kg', 0)),
                fmt_numero(overview.get('kg_por_hh', 0), 1),
                str(overview.get('mos_procesadas', 0)),
                str(overview.get('lotes_unicos', 0))
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[3*cm]*7)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # === RESUMEN POR TIPO DE FRUTA ===
    if consolidado and consolidado.get('por_fruta'):
        elements.append(Paragraph("Rendimiento por Tipo de Fruta", subtitle_style))
        
        por_fruta = consolidado.get('por_fruta', [])
        fruta_data = [['Tipo Fruta', 'Kg MP', 'Kg PT', 'Rendimiento', 'Merma', 'Lotes']]
        
        for fruta in sorted(por_fruta, key=lambda x: x.get('kg_pt', 0), reverse=True):
            rend = fruta.get('rendimiento', 0)
            alert = "🟢" if rend >= 95 else ("🟡" if rend >= 90 else "🔴")
            fruta_data.append([
                fruta.get('tipo_fruta', 'N/A'),
                fmt_numero(fruta.get('kg_mp', 0)),
                fmt_numero(fruta.get('kg_pt', 0)),
                f"{alert} {fmt_porcentaje(rend)}",
                fmt_numero(fruta.get('merma', 0)),
                str(fruta.get('num_lotes', 0))
            ])
        
        fruta_table = Table(fruta_data, colWidths=[4*cm, 3*cm, 3*cm, 3*cm, 3*cm, 2*cm])
        fruta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(fruta_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # === RESUMEN POR FRUTA + MANEJO ===
    if consolidado and consolidado.get('por_fruta_manejo'):
        elements.append(Paragraph("Detalle por Tipo de Fruta y Manejo", subtitle_style))
        
        por_fm = consolidado.get('por_fruta_manejo', [])
        fm_data = [['Fruta', 'Manejo', 'Kg MP', 'Kg PT', 'Rendimiento', 'Merma']]
        
        for fm in sorted(por_fm, key=lambda x: (x.get('tipo_fruta', ''), -x.get('kg_pt', 0))):
            rend = fm.get('rendimiento', 0)
            alert = "🟢" if rend >= 95 else ("🟡" if rend >= 90 else "🔴")
            fm_data.append([
                fm.get('tipo_fruta', 'N/A'),
                fm.get('manejo', 'N/A'),
                fmt_numero(fm.get('kg_mp', 0)),
                fmt_numero(fm.get('kg_pt', 0)),
                f"{alert} {fmt_porcentaje(rend)}",
                fmt_numero(fm.get('merma', 0))
            ])
        
        fm_table = Table(fm_data, colWidths=[3.5*cm, 4*cm, 2.5*cm, 2.5*cm, 3*cm, 2.5*cm])
        fm_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(fm_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # === PRODUCTIVIDAD POR SALA ===
    if salas:
        elements.append(PageBreak())
        elements.append(Paragraph("Productividad por Sala de Proceso", subtitle_style))
        
        sala_data = [['Sala', 'Kg MP', 'Kg PT', 'Rendimiento', 'Kg/Hora', 'Kg/HH', 'HH Total', 'MOs']]
        
        for sala in sorted(salas, key=lambda x: x.get('kg_pt', 0), reverse=True):
            rend = sala.get('rendimiento', 0)
            alert = "🟢" if rend >= 95 else ("🟡" if rend >= 90 else "🔴")
            sala_data.append([
                sala.get('sala', 'N/A')[:25],
                fmt_numero(sala.get('kg_mp', 0)),
                fmt_numero(sala.get('kg_pt', 0)),
                f"{alert} {fmt_porcentaje(rend)}",
                fmt_numero(sala.get('kg_por_hora', 0), 1),
                fmt_numero(sala.get('kg_por_hh', 0), 1),
                fmt_numero(sala.get('hh_total', 0), 1),
                str(sala.get('num_mos', 0))
            ])
        
        sala_table = Table(sala_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2*cm, 2*cm, 2*cm, 1.5*cm])
        sala_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(sala_table)
        elements.append(Spacer(1, 0.5*cm))
    
    # === DETALLE DE FABRICACIONES ===
    if mos:
        elements.append(PageBreak())
        elements.append(Paragraph("Detalle de Órdenes de Fabricación", subtitle_style))
        elements.append(Paragraph(f"Total: {len(mos)} fabricaciones", normal_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Limitar a las primeras 50 MOs para no hacer el PDF muy largo
        mos_to_show = mos[:50]
        
        mo_data = [['OF', 'Producto', 'Sala', 'Kg MP', 'Kg PT', 'Rend.', 'Merma', 'Fecha']]
        
        for mo in mos_to_show:
            rend = mo.get('rendimiento', 0)
            alert = "🟢" if rend >= 95 else ("🟡" if rend >= 90 else "🔴")
            product_name = mo.get('product_name', 'N/A')
            if len(product_name) > 30:
                product_name = product_name[:27] + "..."
            
            mo_data.append([
                mo.get('mo_name', 'N/A'),
                product_name,
                mo.get('sala', 'N/A')[:15] if mo.get('sala') else 'N/A',
                fmt_numero(mo.get('kg_mp', 0)),
                fmt_numero(mo.get('kg_pt', 0)),
                f"{alert} {fmt_porcentaje(rend)}",
                fmt_numero(mo.get('merma', 0)),
                fmt_fecha(mo.get('fecha', ''))
            ])
        
        mo_table = Table(mo_data, colWidths=[2.5*cm, 6*cm, 2.5*cm, 2*cm, 2*cm, 2.5*cm, 2*cm, 2.5*cm])
        mo_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        elements.append(mo_table)
        
        if len(mos) > 50:
            elements.append(Spacer(1, 0.3*cm))
            elements.append(Paragraph(
                f"Nota: Se muestran las primeras 50 de {len(mos)} fabricaciones. Exporta a Excel para ver todas.",
                normal_style
            ))
    
    # Generar PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
