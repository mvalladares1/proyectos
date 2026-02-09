"""
Servicio para generar reportes PDF del Monitor de Producción Diario.
Diseño profesional consolidado: por planta, sala, tipo de proceso y evolución.
Sin tablas detalladas de cada proceso individual.
"""
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any
import os

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
    Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT


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
    posibles = [
        os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'RFP - LOGO OFICIAL.png'),
        '/app/data/RFP - LOGO OFICIAL.png',
    ]
    for p in posibles:
        if os.path.exists(p):
            return p
    return None


def _detectar_planta(proceso):
    name = str(proceso.get('name', '')).upper()
    sala = str(proceso.get('x_studio_sala_de_proceso', '')).upper()
    origin = str(proceso.get('origin', '')).upper()
    for campo in [name, sala, origin]:
        if 'VLK' in campo or 'VILKUN' in campo:
            return 'VILKUN'
    return 'RIO FUTURO'


def _obtener_sala(proceso):
    sala = proceso.get('x_studio_sala_de_proceso', '') or ''
    return sala.strip() if sala else 'Sin Sala'


def _obtener_tipo_proceso(proceso):
    producto = proceso.get('product_id', '')
    if isinstance(producto, (list, tuple)) and len(producto) > 1:
        prod_name = str(producto[1])
    elif isinstance(producto, dict):
        prod_name = str(producto.get('name', 'N/A'))
    else:
        prod_name = str(producto)
    if ']' in prod_name:
        return prod_name.split(']')[0] + ']'
    return prod_name[:30]


def _crear_estilos():
    styles = getSampleStyleSheet()
    return {
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
        'insight': ParagraphStyle(
            'Insight', parent=styles['Normal'],
            fontSize=9, textColor=AZUL_MEDIO, fontName='Helvetica-Oblique',
            spaceBefore=5, spaceAfter=5, leftIndent=10
        ),
    }


def _tabla_estilo(color_header, filas_data):
    """Genera estilo de tabla estándar."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), color_header),
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
        ('TOPPADDING', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
        ('BACKGROUND', (0, -1), (-1, -1), color_header),
        ('TEXTCOLOR', (0, -1), (-1, -1), BLANCO),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [BLANCO, GRIS_CLARO]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D0D0D0')),
        ('BOX', (0, 0), (-1, -1), 1, color_header),
    ])


# ==================== SECCIONES ====================

def _sec_encabezado(estilos, fecha_inicio, fecha_fin, planta, sala):
    elements = []
    logo_path = _get_logo_path()
    if logo_path:
        try:
            logo = Image(logo_path, width=2.2*inch, height=1.1*inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 10))
        except:
            pass

    elements.append(Paragraph("INFORME SEMANAL DE PRODUCCION", estilos['titulo']))
    elements.append(HRFlowable(width="60%", thickness=2, color=AZUL_OSCURO, spaceAfter=8, spaceBefore=5, hAlign='CENTER'))

    try:
        f_ini = datetime.strptime(fecha_inicio, '%Y-%m-%d').strftime('%d/%m/%Y')
        f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').strftime('%d/%m/%Y')
    except:
        f_ini, f_fin = fecha_inicio, fecha_fin

    filtros = f"Periodo: {f_ini} al {f_fin}"
    if planta and planta != "Todas":
        filtros += f"  |  Planta: {planta}"
    if sala and sala != "Todas":
        filtros += f"  |  Sala: {sala}"

    elements.append(Paragraph(filtros, estilos['subtitulo']))
    elements.append(Paragraph(f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}", estilos['pie']))
    elements.append(Spacer(1, 15))
    return elements


def _sec_kpis(estilos, pend, cerr, totales):
    elements = []
    total_pend = len(pend)
    total_cerr = len(cerr)
    kg_pend = sum(max(0, (p.get('product_qty', 0) or 0) - (p.get('qty_produced', 0) or 0)) for p in pend)
    kg_prod = sum(p.get('qty_produced', 0) or 0 for p in cerr)
    total_all = total_pend + total_cerr
    pct = (total_cerr / total_all * 100) if total_all > 0 else 0

    kpi_data = [
        [
            Paragraph(f"{total_pend}", estilos['kpi_valor']),
            Paragraph(f"{kg_pend:,.0f}", estilos['kpi_valor']),
            Paragraph(f"{total_cerr}", estilos['kpi_valor']),
            Paragraph(f"{kg_prod:,.0f}", estilos['kpi_valor']),
            Paragraph(f"{pct:.0f}%", estilos['kpi_valor']),
        ],
        [
            Paragraph("PROCESOS\nPENDIENTES", estilos['kpi_label']),
            Paragraph("KG\nPENDIENTES", estilos['kpi_label']),
            Paragraph("PROCESOS\nCERRADOS", estilos['kpi_label']),
            Paragraph("KG\nPRODUCIDOS", estilos['kpi_label']),
            Paragraph("AVANCE\nGENERAL", estilos['kpi_label']),
        ]
    ]

    w = 1.85 * inch
    t = Table(kpi_data, colWidths=[w]*5)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 1), ROJO_CLARO),
        ('BACKGROUND', (1, 0), (1, 1), NARANJA_CLARO),
        ('BACKGROUND', (2, 0), (2, 1), VERDE_CLARO),
        ('BACKGROUND', (3, 0), (3, 1), AZUL_CLARO),
        ('BACKGROUND', (4, 0), (4, 1), colors.HexColor('#F3E5F5')),
        ('LINEABOVE', (0, 0), (0, 0), 3, ROJO),
        ('LINEABOVE', (1, 0), (1, 0), 3, NARANJA),
        ('LINEABOVE', (2, 0), (2, 0), 3, VERDE),
        ('LINEABOVE', (3, 0), (3, 0), 3, AZUL_MEDIO),
        ('LINEABOVE', (4, 0), (4, 0), 3, colors.HexColor('#9C27B0')),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (0, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (1, 0), (1, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (2, 0), (2, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (3, 0), (3, 1), 1, colors.HexColor('#E0E0E0')),
        ('BOX', (4, 0), (4, 1), 1, colors.HexColor('#E0E0E0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    elements.append(t)
    elements.append(Spacer(1, 15))
    return elements


def _sec_por_planta(estilos, pend, cerr):
    elements = []
    elements.append(Paragraph("RESUMEN POR PLANTA", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=10))

    plantas = {}
    for p in pend:
        pl = _detectar_planta(p)
        if pl not in plantas:
            plantas[pl] = {'pend': 0, 'kg_pend': 0, 'cerr': 0, 'kg_prod': 0}
        plantas[pl]['pend'] += 1
        plantas[pl]['kg_pend'] += max(0, (p.get('product_qty', 0) or 0) - (p.get('qty_produced', 0) or 0))
    for p in cerr:
        pl = _detectar_planta(p)
        if pl not in plantas:
            plantas[pl] = {'pend': 0, 'kg_pend': 0, 'cerr': 0, 'kg_prod': 0}
        plantas[pl]['cerr'] += 1
        plantas[pl]['kg_prod'] += p.get('qty_produced', 0) or 0

    data = [['PLANTA', 'PENDIENTES', 'KG PENDIENTES', 'CERRADOS', 'KG PRODUCIDOS', '% AVANCE']]
    for pl in sorted(plantas.keys()):
        d = plantas[pl]
        total = d['pend'] + d['cerr']
        avance = (d['cerr'] / total * 100) if total > 0 else 0
        data.append([pl, str(d['pend']), f"{d['kg_pend']:,.0f} kg", str(d['cerr']), f"{d['kg_prod']:,.0f} kg", f"{avance:.0f}%"])

    tp = sum(v['pend'] for v in plantas.values())
    tkp = sum(v['kg_pend'] for v in plantas.values())
    tc = sum(v['cerr'] for v in plantas.values())
    tkc = sum(v['kg_prod'] for v in plantas.values())
    ta = (tc / (tp + tc) * 100) if (tp + tc) > 0 else 0
    data.append(['TOTAL', str(tp), f"{tkp:,.0f} kg", str(tc), f"{tkc:,.0f} kg", f"{ta:.0f}%"])

    t = Table(data, colWidths=[1.8*inch, 1.3*inch, 1.6*inch, 1.3*inch, 1.6*inch, 1.2*inch])
    t.setStyle(_tabla_estilo(AZUL_OSCURO, data))
    elements.append(t)
    elements.append(Spacer(1, 15))
    return elements


def _sec_por_sala(estilos, pend, cerr):
    elements = []
    elements.append(Paragraph("RESUMEN POR SALA DE PROCESO", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=10))

    salas = {}
    for p in pend:
        sala = _obtener_sala(p)
        planta = _detectar_planta(p)
        key = f"{sala}|{planta}"
        if key not in salas:
            salas[key] = {'sala': sala, 'planta': planta, 'pend': 0, 'kg_pend': 0, 'cerr': 0, 'kg_prod': 0}
        salas[key]['pend'] += 1
        salas[key]['kg_pend'] += max(0, (p.get('product_qty', 0) or 0) - (p.get('qty_produced', 0) or 0))
    for p in cerr:
        sala = _obtener_sala(p)
        planta = _detectar_planta(p)
        key = f"{sala}|{planta}"
        if key not in salas:
            salas[key] = {'sala': sala, 'planta': planta, 'pend': 0, 'kg_pend': 0, 'cerr': 0, 'kg_prod': 0}
        salas[key]['cerr'] += 1
        salas[key]['kg_prod'] += p.get('qty_produced', 0) or 0

    if not salas:
        return elements

    data = [['SALA', 'PLANTA', 'PEND.', 'KG PEND.', 'CERR.', 'KG PROD.', 'TOTAL', '% AVANCE']]
    for item in sorted(salas.values(), key=lambda x: x['pend'] + x['cerr'], reverse=True):
        total = item['pend'] + item['cerr']
        avance = (item['cerr'] / total * 100) if total > 0 else 0
        data.append([
            Paragraph(item['sala'][:22], estilos['normal']),
            item['planta'][:10],
            str(item['pend']),
            f"{item['kg_pend']:,.0f}",
            str(item['cerr']),
            f"{item['kg_prod']:,.0f}",
            str(total),
            f"{avance:.0f}%"
        ])

    tp = sum(v['pend'] for v in salas.values())
    tkp = sum(v['kg_pend'] for v in salas.values())
    tc = sum(v['cerr'] for v in salas.values())
    tkc = sum(v['kg_prod'] for v in salas.values())
    tt = tp + tc
    ta = (tc / tt * 100) if tt > 0 else 0
    data.append(['TOTAL', '', str(tp), f"{tkp:,.0f}", str(tc), f"{tkc:,.0f}", str(tt), f"{ta:.0f}%"])

    t = Table(data, colWidths=[2*inch, 1*inch, 0.7*inch, 1.3*inch, 0.7*inch, 1.3*inch, 0.7*inch, 1*inch])
    t.setStyle(_tabla_estilo(AZUL_MEDIO, data))
    elements.append(t)
    elements.append(Spacer(1, 15))
    return elements


def _sec_por_tipo(estilos, pend, cerr):
    elements = []
    elements.append(Paragraph("RESUMEN POR TIPO DE PROCESO", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=10))

    tipos = {}
    for p in pend:
        tipo = _obtener_tipo_proceso(p)
        if tipo not in tipos:
            tipos[tipo] = {'pend': 0, 'kg_pend': 0, 'cerr': 0, 'kg_prod': 0}
        tipos[tipo]['pend'] += 1
        tipos[tipo]['kg_pend'] += max(0, (p.get('product_qty', 0) or 0) - (p.get('qty_produced', 0) or 0))
    for p in cerr:
        tipo = _obtener_tipo_proceso(p)
        if tipo not in tipos:
            tipos[tipo] = {'pend': 0, 'kg_pend': 0, 'cerr': 0, 'kg_prod': 0}
        tipos[tipo]['cerr'] += 1
        tipos[tipo]['kg_prod'] += p.get('qty_produced', 0) or 0

    if not tipos:
        return elements

    data = [['TIPO PROCESO', 'PEND.', 'KG PEND.', 'CERR.', 'KG PROD.', '% AVANCE']]
    for tipo, d in sorted(tipos.items(), key=lambda x: x[1]['pend'] + x[1]['cerr'], reverse=True)[:15]:
        total = d['pend'] + d['cerr']
        avance = (d['cerr'] / total * 100) if total > 0 else 0
        data.append([
            Paragraph(tipo[:35], estilos['normal']),
            str(d['pend']),
            f"{d['kg_pend']:,.0f}",
            str(d['cerr']),
            f"{d['kg_prod']:,.0f}",
            f"{avance:.0f}%"
        ])

    # Sin fila total para evitar error con _tabla_estilo
    t = Table(data, colWidths=[3*inch, 0.9*inch, 1.3*inch, 0.9*inch, 1.3*inch, 1*inch])
    t.setStyle(TableStyle([
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
    elements.append(t)
    elements.append(Spacer(1, 15))
    return elements


def _sec_evolucion(estilos, evolucion, totales):
    elements = []
    if not evolucion:
        return elements

    elements.append(Paragraph("EVOLUCION DIARIA - AVANCE DE PRODUCCION", estilos['seccion']))
    elements.append(HRFlowable(width="100%", thickness=1, color=AZUL_CLARO, spaceAfter=5))
    elements.append(Paragraph(
        "Balance positivo = se cerraron mas procesos de los que se crearon. Negativo = se acumularon.",
        estilos['insight']
    ))
    elements.append(Spacer(1, 5))

    data = [['FECHA', 'CREADOS', 'CERRADOS', 'BALANCE', 'KG PROGRAMADOS', 'KG PRODUCIDOS']]
    acum_cr, acum_ce = 0, 0

    for e in evolucion:
        fd = e.get('fecha_display', '')
        if not fd:
            try:
                fd = datetime.strptime(e.get('fecha', ''), '%Y-%m-%d').strftime('%d/%m')
            except:
                fd = e.get('fecha', '')
        cr = e.get('procesos_creados', 0)
        ce = e.get('procesos_cerrados', 0)
        bal = ce - cr
        acum_cr += cr
        acum_ce += ce
        data.append([
            fd, str(cr), str(ce),
            f"+{bal}" if bal > 0 else str(bal),
            f"{e.get('kg_programados', 0):,.0f}",
            f"{e.get('kg_producidos', 0):,.0f}"
        ])

    bal_total = acum_ce - acum_cr
    data.append([
        'TOTAL', str(acum_cr), str(acum_ce),
        f"+{bal_total}" if bal_total > 0 else str(bal_total),
        f"{totales.get('total_kg_programados', 0):,.0f}",
        f"{totales.get('total_kg_producidos', 0):,.0f}"
    ])

    t = Table(data, colWidths=[1.5*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.5*inch, 1.5*inch])

    style_cmds = [
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
    ]
    # Colorear balance
    for i in range(1, len(data) - 1):
        bv = data[i][3]
        if bv.startswith('+'):
            style_cmds.append(('TEXTCOLOR', (3, i), (3, i), VERDE))
        elif bv.startswith('-'):
            style_cmds.append(('TEXTCOLOR', (3, i), (3, i), ROJO))

    t.setStyle(TableStyle(style_cmds))
    elements.append(t)
    elements.append(Spacer(1, 10))

    if bal_total > 0:
        msg = f"Se cerraron {bal_total} procesos mas de los creados. Buen avance."
    elif bal_total < 0:
        msg = f"Se acumularon {abs(bal_total)} procesos mas de los cerrados. Hay que aumentar ritmo."
    else:
        msg = "Ritmo de cierre igual al de creacion. Produccion estable."
    elements.append(Paragraph(f"Conclusion: {msg}", estilos['insight']))
    elements.append(Spacer(1, 15))
    return elements


def _sec_pie(estilos):
    elements = []
    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="80%", thickness=1, color=GRIS_MEDIO, spaceAfter=10, hAlign='CENTER'))
    elements.append(Paragraph("Rio Futuro Procesos | Informe Semanal de Produccion", estilos['pie']))
    elements.append(Paragraph("Generado automaticamente desde el Sistema de Dashboards.", estilos['pie']))
    return elements


# ==================== GENERADOR PRINCIPAL ====================

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
    Genera PDF consolidado: por planta, sala, tipo de proceso y evolución.
    Sin tablas detalladas de cada proceso individual.
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
    elements.extend(_sec_encabezado(estilos, fecha_inicio, fecha_fin, planta, sala))
    # 2. KPIs principales
    elements.extend(_sec_kpis(estilos, procesos_pendientes, procesos_cerrados, totales))
    # 3. Resumen por planta
    elements.extend(_sec_por_planta(estilos, procesos_pendientes, procesos_cerrados))
    # 4. Resumen por sala
    elements.extend(_sec_por_sala(estilos, procesos_pendientes, procesos_cerrados))
    # 5. Resumen por tipo de proceso
    elements.extend(_sec_por_tipo(estilos, procesos_pendientes, procesos_cerrados))
    # 6. Evolución diaria
    elements.extend(_sec_evolucion(estilos, evolucion, totales))
    # 7. Pie
    elements.extend(_sec_pie(estilos))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
