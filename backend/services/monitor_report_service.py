"""
Servicio para generar reportes PDF del Monitor de Producción Diario
Diseño profesional con logo Rio Futuro, KPIs, tablas y resúmenes por planta.
"""
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, 
    Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT


# ==================== COLORES CORPORATIVOS ====================
AZUL_OSCURO = colors.HexColor('#0B3D5C')
AZUL_MEDIO = colors.HexColor('#1565A0')
AZUL_CLARO = colors.HexColor('#E3F2FD')
VERDE = colors.HexColor('#27AE60')
VERDE_CLARO = colors.HexColor('#E8F5E9')
ROJO = colors.HexColor('#E74C3C')
ROJO_CLARO = colors.HexColor('#FDEDED')
NARANJA = colors.HexColor('#F39C12')
NARANJA_CLARO = colors.HexColor('#FFF8E1')
GRIS_OSCURO = colors.HexColor('#2C3E50')
GRIS_MEDIO = colors.HexColor('#7F8C8D')
GRIS_CLARO = colors.HexColor('#F5F6FA')
BLANCO = colors.white


def _get_logo_path():
    """Obtiene la ruta del logo."""
    posibles = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'RFP - LOGO OFICIAL.png'),
        os.path.join(os.path.dirname(__file__), '..', '..', 'docs', 'LOGO.png'),
        '/app/data/RFP - LOGO OFICIAL.png',
        '/app/docs/LOGO.png',
    ]
    for p in posibles:
        if os.path.exists(p):
            return p
    return None


def _detectar_planta(proceso):
    """Detecta la planta de un proceso."""
    name = str(proceso.get('name', '')).upper()
    sala = str(proceso.get('x_studio_sala_de_proceso', '')).upper()
    origin = str(proceso.get('origin', '')).upper()
    
    for campo in [name, sala, origin]:
        if 'VLK' in campo or 'VILKUN' in campo:
            return 'VILKUN'
    return 'RIO FUTURO'


def _crear_estilos():
    """Crea los estilos del documento."""
    styles = getSampleStyleSheet()
    
    estilos = {
        'titulo': ParagraphStyle(
            'Titulo', parent=styles['Heading1'],
            fontSize=22, alignment=TA_CENTER, spaceAfter=5,
            textColor=AZUL_OSCURO, fontName='Helvetica-Bold'
        ),
        'subtitulo': ParagraphStyle(
            'Subtitulo', parent=styles['Heading2'],
            fontSize=11, alignment=TA_CENTER, spaceAfter=15,
            textColor=GRIS_MEDIO, fontName='Helvetica'
        ),
        'seccion': ParagraphStyle(
            'Seccion', parent=styles['Heading2'],
            fontSize=14, alignment=TA_LEFT, spaceBefore=20, spaceAfter=10,
            textColor=AZUL_OSCURO, fontName='Helvetica-Bold'
        ),
        'subseccion': ParagraphStyle(
            'Subseccion', parent=styles['Heading3'],
            fontSize=11, alignment=TA_LEFT, spaceBefore=10, spaceAfter=5,
            textColor=AZUL_MEDIO, fontName='Helvetica-Bold'
        ),
        'normal': ParagraphStyle(
            'NormalCustom', parent=styles['Normal'],
            fontSize=9, textColor=GRIS_OSCURO, fontName='Helvetica'
        ),
        'pie': ParagraphStyle(
            'Pie', parent=styles['Normal'],
            fontSize=8, alignment=TA_CENTER, textColor=GRIS_MEDIO
        ),
        'kpi_valor': ParagraphStyle(
            'KpiValor', parent=styles['Normal'],
            fontSize=20, alignment=TA_CENTER, textColor=AZUL_OSCURO,
            fontName='Helvetica-Bold', spaceBefore=5, spaceAfter=2
        ),
        'kpi_label': ParagraphStyle(
            'KpiLabel', parent=styles['Normal'],
            fontSize=8, alignment=TA_CENTER, textColor=GRIS_MEDIO,
            fontName='Helvetica', spaceAfter=5
        ),
    }
    return estilos


def _crear_encabezado(estilos, fecha_inicio, fecha_fin, planta, sala):
    """Crea el encabezado con logo y título."""
    elements = []
    
    # Logo
    logo_path = _get_logo_path()
    if logo_path:
        try:
            logo = Image(logo_path, width=2.2*inch, height=1.1*inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 10))
        except:
            pass
    
    # Título
    elements.append(Paragraph("INFORME DE PRODUCCION", estilos['titulo']))
    
    # Línea decorativa
    elements.append(HRFlowable(
        width="60%", thickness=2, color=AZUL_OSCURO,
        spaceAfter=8, spaceBefore=5, hAlign='CENTER'
    ))
    
    # Info del período
    try:
        f_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
        f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        f_inicio = fecha_inicio
        f_fin = fecha_fin
    
    filtros = f"Periodo: {f_inicio} al {f_fin}"
    if planta and planta != "Todas":
        filtros += f"  |  Planta: {planta}"
    if sala and sala != "Todas":
        filtros += f"  |  Sala: {sala}"
    
    elements.append(Paragraph(filtros, estilos['subtitulo']))
    
    generado = datetime.now().strftime('%d/%m/%Y %H:%M')
    elements.append(Paragraph(f"Generado el {generado}", estilos['pie']))
    elements.append(Spacer(1, 15))
    
    return elements


def _crear_kpis(estilos, procesos_pendientes, procesos_cerrados, totales):
    """Crea la sección de KPIs principales."""
    elements = []
    
    total_pend = len(procesos_pendientes)
    total_cerr = len(procesos_cerrados)
    kg_pend = sum(
        (p.get('product_qty', 0) or 0) - (p.get('qty_produced', 0) or 0)
        for p in procesos_pendientes
    )
    kg_prod = sum(p.get('qty_produced', 0) or 0 for p in procesos_cerrados)
    
    # Tabla de KPIs
    kpi_data = [
        [
            Paragraph(f"{total_pend}", estilos['kpi_valor']),
            Paragraph(f"{kg_pend:,.0f}", estilos['kpi_valor']),
            Paragraph(f"{total_cerr}", estilos['kpi_valor']),
            Paragraph(f"{kg_prod:,.0f}", estilos['kpi_valor']),
        ],
        [
            Paragraph("PROCESOS PENDIENTES", estilos['kpi_label']),
            Paragraph("KG PENDIENTES", estilos['kpi_label']),
            Paragraph("PROCESOS CERRADOS", estilos['kpi_label']),
            Paragraph("KG PRODUCIDOS", estilos['kpi_label']),
        ]
    ]
    
    col_w = 2.3 * inch
    kpi_table = Table(kpi_data, colWidths=[col_w, col_w, col_w, col_w])
    kpi_table.setStyle(TableStyle([
        # Fondos
        ('BACKGROUND', (0, 0), (0, 1), ROJO_CLARO),
        ('BACKGROUND', (1, 0), (1, 1), NARANJA_CLARO),
        ('BACKGROUND', (2, 0), (2, 1), VERDE_CLARO),
        ('BACKGROUND', (3, 0), (3, 1), AZUL_CLARO),
        # Bordes superiores de color
        ('LINEABOVE', (0, 0), (0, 0), 3, ROJO),
        ('LINEABOVE', (1, 0), (1, 0), 3, NARANJA),
        ('LINEABOVE', (2, 0), (2, 0), 3, VERDE),
        ('LINEABOVE', (3, 0), (3, 0), 3, AZUL_MEDIO),
        # Padding
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        # Bordes
        ('BOX', (0, 0), (0, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (1, 0), (1, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (2, 0), (2, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (3, 0), (3, 1), 1, colors.HexColor('#E0E0E0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(kpi_table)
    elements.append(Spacer(1, 15))
    
    return elements


def _crear_resumen_por_planta(estilos, procesos_pendientes, procesos_cerrados):
    """Crea la sección de resumen por planta."""
    elements = []
    
    elements.append(Paragraph("RESUMEN POR PLANTA", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=10))
    
    # Agrupar por planta
    plantas_pend = {}
    for p in procesos_pendientes:
        planta = _detectar_planta(p)
        if planta not in plantas_pend:
            plantas_pend[planta] = {'procesos': 0, 'kg_prog': 0, 'kg_prod': 0}
        plantas_pend[planta]['procesos'] += 1
        plantas_pend[planta]['kg_prog'] += p.get('product_qty', 0) or 0
        plantas_pend[planta]['kg_prod'] += p.get('qty_produced', 0) or 0
    
    plantas_cerr = {}
    for p in procesos_cerrados:
        planta = _detectar_planta(p)
        if planta not in plantas_cerr:
            plantas_cerr[planta] = {'procesos': 0, 'kg_prod': 0}
        plantas_cerr[planta]['procesos'] += 1
        plantas_cerr[planta]['kg_prod'] += p.get('qty_produced', 0) or 0
    
    todas_plantas = sorted(set(list(plantas_pend.keys()) + list(plantas_cerr.keys())))
    
    if not todas_plantas:
        return elements
    
    header = ['PLANTA', 'PENDIENTES', 'KG PENDIENTES', 'CERRADOS', 'KG PRODUCIDOS']
    data = [header]
    
    for pl in todas_plantas:
        pend = plantas_pend.get(pl, {'procesos': 0, 'kg_prog': 0, 'kg_prod': 0})
        cerr = plantas_cerr.get(pl, {'procesos': 0, 'kg_prod': 0})
        kg_pendiente = pend['kg_prog'] - pend['kg_prod']
        data.append([
            pl,
            str(pend['procesos']),
            f"{kg_pendiente:,.0f} kg",
            str(cerr['procesos']),
            f"{cerr['kg_prod']:,.0f} kg"
        ])
    
    # Fila total
    total_pend = sum(v['procesos'] for v in plantas_pend.values())
    total_kg_pend = sum(v['kg_prog'] - v['kg_prod'] for v in plantas_pend.values())
    total_cerr = sum(v['procesos'] for v in plantas_cerr.values())
    total_kg_prod = sum(v['kg_prod'] for v in plantas_cerr.values())
    data.append([
        'TOTAL',
        str(total_pend),
        f"{total_kg_pend:,.0f} kg",
        str(total_cerr),
        f"{total_kg_prod:,.0f} kg"
    ])
    
    table = Table(data, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch, 2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_OSCURO),
        ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('BACKGROUND', (0, -1), (-1, -1), AZUL_OSCURO),
        ('TEXTCOLOR', (0, -1), (-1, -1), BLANCO),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [BLANCO, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0D0D0')),
        ('BOX', (0, 0), (-1, -1), 1, AZUL_OSCURO),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 15))
    
    return elements


def _crear_evolucion_diaria(estilos, evolucion, totales):
    """Crea la sección de evolución diaria."""
    elements = []
    
    if not evolucion:
        return elements
    
    elements.append(Paragraph("EVOLUCION DIARIA", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=10))
    
    header = ['FECHA', 'CREADOS', 'CERRADOS', 'KG PROGRAMADOS', 'KG PRODUCIDOS', 'BALANCE']
    data = [header]
    
    for e in evolucion:
        fecha_display = e.get('fecha_display', '')
        if not fecha_display:
            try:
                fecha_display = datetime.strptime(e.get('fecha', ''), '%Y-%m-%d').strftime('%d/%m')
            except:
                fecha_display = e.get('fecha', '')
        
        creados = e.get('procesos_creados', 0)
        cerrados_e = e.get('procesos_cerrados', 0)
        balance = creados - cerrados_e
        
        data.append([
            fecha_display,
            str(creados),
            str(cerrados_e),
            f"{e.get('kg_programados', 0):,.0f}",
            f"{e.get('kg_producidos', 0):,.0f}",
            f"+{balance}" if balance > 0 else str(balance)
        ])
    
    # Fila total
    data.append([
        'TOTAL',
        str(totales.get('total_creados', 0)),
        str(totales.get('total_cerrados', 0)),
        f"{totales.get('total_kg_programados', 0):,.0f}",
        f"{totales.get('total_kg_producidos', 0):,.0f}",
        str(totales.get('total_creados', 0) - totales.get('total_cerrados', 0))
    ])
    
    table = Table(data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1.5*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), AZUL_MEDIO),
        ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('TOPPADDING', (0, 0), (-1, 0), 10),
        ('FONTNAME', (0, 1), (-1, -2), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
        ('BACKGROUND', (0, -1), (-1, -1), AZUL_OSCURO),
        ('TEXTCOLOR', (0, -1), (-1, -1), BLANCO),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [BLANCO, AZUL_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0D0D0')),
        ('BOX', (0, 0), (-1, -1), 1, AZUL_MEDIO),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 15))
    
    return elements


def _crear_tabla_pendientes(estilos, procesos_pendientes):
    """Crea la tabla de procesos pendientes por planta."""
    elements = []
    
    if not procesos_pendientes:
        return elements
    
    elements.append(Paragraph("DETALLE DE PROCESOS PENDIENTES", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=ROJO_CLARO, spaceAfter=10))
    
    # Agrupar por planta
    por_planta = {}
    for p in procesos_pendientes:
        planta = _detectar_planta(p)
        if planta not in por_planta:
            por_planta[planta] = []
        por_planta[planta].append(p)
    
    for planta in sorted(por_planta.keys()):
        procs = por_planta[planta]
        
        elements.append(Paragraph(
            f"{planta} - {len(procs)} procesos pendientes",
            estilos['subseccion']
        ))
        
        header = ['OF', 'PRODUCTO', 'SALA', 'KG PROG.', 'KG PROD.', 'PEND.', '% AVANCE']
        data = [header]
        
        procs_sorted = sorted(procs, key=lambda x: (x.get('product_qty', 0) or 0) - (x.get('qty_produced', 0) or 0), reverse=True)
        
        for p in procs_sorted[:25]:
            producto = p.get('product_id', '')
            if isinstance(producto, (list, tuple)) and len(producto) > 1:
                prod_name = str(producto[1])[:30]
            elif isinstance(producto, dict):
                prod_name = str(producto.get('name', 'N/A'))[:30]
            else:
                prod_name = str(producto)[:30]
            
            kg_prog = p.get('product_qty', 0) or 0
            kg_prod = p.get('qty_produced', 0) or 0
            pendiente = kg_prog - kg_prod
            avance = (kg_prod / kg_prog * 100) if kg_prog > 0 else 0
            
            data.append([
                str(p.get('name', ''))[:15],
                Paragraph(prod_name, estilos['normal']),
                str(p.get('x_studio_sala_de_proceso', '-'))[:18],
                f"{kg_prog:,.0f}",
                f"{kg_prod:,.0f}",
                f"{pendiente:,.0f}",
                f"{avance:.0f}%"
            ])
        
        if len(procs) > 25:
            data.append([f"... y {len(procs) - 25} mas", '', '', '', '', '', ''])
        
        table = Table(data, colWidths=[1*inch, 2.2*inch, 1.5*inch, 1*inch, 1*inch, 1*inch, 0.8*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), ROJO),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANCO, ROJO_CLARO]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ('BOX', (0, 0), (-1, -1), 1, ROJO),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
    
    return elements


def _crear_tabla_cerrados(estilos, procesos_cerrados):
    """Crea la tabla de procesos cerrados por planta."""
    elements = []
    
    if not procesos_cerrados:
        return elements
    
    elements.append(Paragraph("PROCESOS CERRADOS EN EL PERIODO", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=VERDE_CLARO, spaceAfter=10))
    
    por_planta = {}
    for p in procesos_cerrados:
        planta = _detectar_planta(p)
        if planta not in por_planta:
            por_planta[planta] = []
        por_planta[planta].append(p)
    
    for planta in sorted(por_planta.keys()):
        procs = por_planta[planta]
        total_kg = sum(p.get('qty_produced', 0) or 0 for p in procs)
        
        elements.append(Paragraph(
            f"{planta} - {len(procs)} cerrados | {total_kg:,.0f} KG producidos",
            estilos['subseccion']
        ))
        
        header = ['OF', 'PRODUCTO', 'SALA', 'KG PRODUCIDOS', 'FECHA CIERRE']
        data = [header]
        
        for p in procs[:25]:
            producto = p.get('product_id', '')
            if isinstance(producto, (list, tuple)) and len(producto) > 1:
                prod_name = str(producto[1])[:30]
            elif isinstance(producto, dict):
                prod_name = str(producto.get('name', 'N/A'))[:30]
            else:
                prod_name = str(producto)[:30]
            
            fecha_cierre = p.get('date_finished', '') or p.get('x_studio_termino_de_proceso', '')
            try:
                if fecha_cierre:
                    fecha_cierre = str(fecha_cierre)[:10]
                    fecha_cierre = datetime.strptime(fecha_cierre, '%Y-%m-%d').strftime('%d/%m/%Y')
            except:
                fecha_cierre = str(fecha_cierre)[:10] if fecha_cierre else '-'
            
            data.append([
                str(p.get('name', ''))[:15],
                Paragraph(prod_name, estilos['normal']),
                str(p.get('x_studio_sala_de_proceso', '-'))[:18],
                f"{p.get('qty_produced', 0) or 0:,.0f}",
                fecha_cierre or '-'
            ])
        
        if len(procs) > 25:
            data.append([f"... y {len(procs) - 25} mas", '', '', '', ''])
        
        table = Table(data, colWidths=[1.2*inch, 2.8*inch, 1.8*inch, 1.3*inch, 1.2*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), VERDE),
            ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANCO, VERDE_CLARO]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ('BOX', (0, 0), (-1, -1), 1, VERDE),
        ]))
        
        elements.append(table)
        elements.append(Spacer(1, 12))
    
    return elements


def _crear_resumen_por_tipo_proceso(estilos, procesos_pendientes):
    """Crea resumen agrupado por tipo de proceso y planta."""
    elements = []
    
    if not procesos_pendientes:
        return elements
    
    elements.append(Paragraph("PENDIENTES POR TIPO DE PROCESO", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=10))
    
    por_tipo = {}
    for p in procesos_pendientes:
        producto = p.get('product_id', '')
        if isinstance(producto, (list, tuple)) and len(producto) > 1:
            prod_name = str(producto[1])
        elif isinstance(producto, dict):
            prod_name = str(producto.get('name', 'N/A'))
        else:
            prod_name = str(producto)
        
        tipo = prod_name.split(']')[0] + ']' if ']' in prod_name else prod_name[:25]
        planta = _detectar_planta(p)
        key = f"{tipo}|{planta}"
        
        if key not in por_tipo:
            por_tipo[key] = {'tipo': tipo, 'planta': planta, 'cantidad': 0, 'kg': 0}
        por_tipo[key]['cantidad'] += 1
        por_tipo[key]['kg'] += (p.get('product_qty', 0) or 0) - (p.get('qty_produced', 0) or 0)
    
    header = ['TIPO PROCESO', 'PLANTA', 'CANTIDAD', 'KG PENDIENTES']
    data = [header]
    
    for item in sorted(por_tipo.values(), key=lambda x: x['kg'], reverse=True)[:20]:
        data.append([
            Paragraph(item['tipo'][:35], estilos['normal']),
            item['planta'],
            str(item['cantidad']),
            f"{item['kg']:,.0f}"
        ])
    
    table = Table(data, colWidths=[3*inch, 1.5*inch, 1.2*inch, 1.5*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), GRIS_OSCURO),
        ('TEXTCOLOR', (0, 0), (-1, 0), BLANCO),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [BLANCO, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0D0D0')),
        ('BOX', (0, 0), (-1, -1), 1, GRIS_OSCURO),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 15))
    
    return elements


def _crear_pie(estilos):
    """Crea el pie del documento."""
    elements = []
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="80%", thickness=1, color=GRIS_MEDIO, spaceAfter=10, hAlign='CENTER'))
    elements.append(Paragraph(
        "Rio Futuro Procesos | Informe de Produccion | Sistema de Dashboards",
        estilos['pie']
    ))
    elements.append(Paragraph(
        "Este informe fue generado automaticamente. Los datos reflejan el estado al momento de la consulta.",
        estilos['pie']
    ))
    return elements


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
    Genera un reporte PDF profesional del monitor de produccion.
    """
    buffer = BytesIO()
    
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.6*inch,
        leftMargin=0.6*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    estilos = _crear_estilos()
    elements = []
    
    # 1. Encabezado con logo
    elements.extend(_crear_encabezado(estilos, fecha_inicio, fecha_fin, planta, sala))
    
    # 2. KPIs principales
    elements.extend(_crear_kpis(estilos, procesos_pendientes, procesos_cerrados, totales))
    
    # 3. Resumen por planta
    elements.extend(_crear_resumen_por_planta(estilos, procesos_pendientes, procesos_cerrados))
    
    # 4. Evolucion diaria
    elements.extend(_crear_evolucion_diaria(estilos, evolucion, totales))
    
    # 5. Resumen por tipo de proceso
    elements.extend(_crear_resumen_por_tipo_proceso(estilos, procesos_pendientes))
    
    # Salto de pagina antes de tablas detalladas
    elements.append(PageBreak())
    
    # 6. Logo pequeño en segunda pagina
    logo_path = _get_logo_path()
    if logo_path:
        try:
            logo = Image(logo_path, width=1.2*inch, height=0.6*inch)
            logo.hAlign = 'RIGHT'
            elements.append(logo)
            elements.append(Spacer(1, 5))
        except:
            pass
    
    # 7. Tabla de pendientes
    elements.extend(_crear_tabla_pendientes(estilos, procesos_pendientes))
    
    # 8. Tabla de cerrados
    elements.extend(_crear_tabla_cerrados(estilos, procesos_cerrados))
    
    # 9. Pie
    elements.extend(_crear_pie(estilos))
    
    # Generar PDF
    doc.build(elements)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    
    return pdf_bytes
