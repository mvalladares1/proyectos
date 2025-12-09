from typing import List, Dict, Any, Optional
from io import BytesIO
from datetime import datetime, date, timedelta
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.utils import ImageReader
import matplotlib.pyplot as plt

# Máximo de días a traer en una sola llamada a Odoo (para evitar rangos excesivos)
MAX_DAYS_FETCH = 90

from backend.services.recepcion_service import get_recepciones_mp


def _normalize_categoria(cat: str) -> str:
    if not cat:
        return ''
    c = cat.strip().upper()
    if 'BANDEJ' in c:
        return 'BANDEJAS'
    return c


def _aggregate_envases(recepciones: List[Dict[str, Any]]) -> Dict[str, float]:
    """Agrupa envases (bandejas) por nombre de producto para desglose detallado."""
    envases = {}
    for r in recepciones:
        for p in r.get('productos', []) or []:
            categoria = _normalize_categoria(p.get('Categoria', ''))
            if categoria == 'BANDEJAS':
                nombre = p.get('Producto', 'Sin nombre')
                envases[nombre] = envases.get(nombre, 0) + (p.get('Kg Hechos', 0) or 0)
    return envases


def _aggregate_by_fruta(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa recepciones por tipo_fruta y calcula métricas por fruta."""
    agrup = {}
    for r in recepciones:
        tipo = (r.get('tipo_fruta') or '').strip()
        if not tipo:
            continue
        if tipo not in agrup:
            agrup[tipo] = {
                'kg': 0.0,
                'costo': 0.0,
                'iqf_vals': [],
                'block_vals': [],
                'n_recepciones': 0,
                'productores': {}
            }
        entry = agrup[tipo]
        entry['n_recepciones'] += 1
        # recorrer productos para sumar kg y costo excluyendo bandejas
        for p in r.get('productos', []) or []:
            cat = _normalize_categoria(p.get('Categoria', ''))
            kg = p.get('Kg Hechos', 0) or 0
            costo = p.get('Costo Total', 0) or 0
            if cat == 'BANDEJAS':
                # skip bandejas from kg/costo of fruit
                continue
            entry['kg'] += kg
            entry['costo'] += costo
        # quality averages
        entry['iqf_vals'].append(r.get('total_iqf', 0) or 0)
        entry['block_vals'].append(r.get('total_block', 0) or 0)
        # productores
        prod = r.get('productor') or ''
        if prod:
            entry['productores'][prod] = entry['productores'].get(prod, 0) + (r.get('kg_recepcionados') or 0)

    # convertir a lista con cálculos
    out = []
    for tipo, v in agrup.items():
        kg = v['kg']
        costo = v['costo']
        costo_prom = (costo / kg) if kg > 0 else None
        prom_iqf = (sum(v['iqf_vals']) / len(v['iqf_vals'])) if v['iqf_vals'] else 0
        prom_block = (sum(v['block_vals']) / len(v['block_vals'])) if v['block_vals'] else 0
        top_productores = sorted(v['productores'].items(), key=lambda x: x[1], reverse=True)[:5]
        out.append({
            'tipo_fruta': tipo,
            'kg': kg,
            'costo': costo,
            'costo_prom': costo_prom,
            'prom_iqf': prom_iqf,
            'prom_block': prom_block,
            'n_recepciones': v['n_recepciones'],
            'top_productores': top_productores
        })
    # orden por Kg descendente
    out.sort(key=lambda x: x['kg'], reverse=True)
    return out


def generate_recepcion_report_pdf(username: str, password: str, fecha_inicio: str, fecha_fin: str,
                                  include_prev_week: bool = False, include_month_accum: bool = False,
                                  logo_path: Optional[str] = None,
                                  include_pie: bool = True) -> bytes:
    """Genera un PDF con el resumen por fruta para el rango dado.
    Opciones para incluir la semana previa y acumulado parcial del mes.
    """
    # Parse dates
    f_inicio = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
    f_fin = datetime.strptime(fecha_fin, '%Y-%m-%d').date()

    # calcular semana anterior range
    delta = (f_fin - f_inicio) + timedelta(days=1)
    prev_end = f_inicio - timedelta(days=1)
    prev_start = prev_end - (delta - timedelta(days=1))

    # calcular mes start
    month_start = date(f_fin.year, f_fin.month, 1)

    # determino el rango a traer desde Odoo: el mínimo entre month_start y prev_start
    fetch_start = min(month_start, prev_start)

    # Limitar el número de días a traer para evitar consultas muy grandes
    total_days = (f_fin - fetch_start).days + 1
    if total_days > MAX_DAYS_FETCH:
        raise Exception(f"Rango demasiado grande: {total_days} días. Límite permitido = {MAX_DAYS_FETCH} días. Por favor reduzca el rango o use un reporte asíncrono.")

    recepciones_all = get_recepciones_mp(username, password, fetch_start.isoformat(), f_fin.isoformat())

    # normalizar categorias
    for r in recepciones_all:
        for p in r.get('productos', []) or []:
            p['Categoria'] = _normalize_categoria(p.get('Categoria', ''))

    # helper to filter by date range (using date portion of r['fecha'])
    def _in_range(r, start_date: date, end_date: date) -> bool:
        try:
            rd = datetime.fromisoformat(r.get('fecha')).date()
        except Exception:
            try:
                rd = datetime.strptime(r.get('fecha', '')[:10], '%Y-%m-%d').date()
            except Exception:
                return False
        return start_date <= rd <= end_date

    # filtrar recepciones para el rango principal
    recepciones_main = [r for r in recepciones_all if _in_range(r, f_inicio, f_fin)]
    main_agg = _aggregate_by_fruta(recepciones_main)

    # Calcular totales y KPIs globales para mostrar arriba
    total_kg = sum(r['kg'] for r in main_agg)
    total_costo = sum(r['costo'] for r in main_agg)
    # calcular bandejas (unidades) sumando la cantidad reportada para productos categorizados como BANDEJAS
    # Nota: en los movimientos la cantidad queda en 'Kg Hechos' pero para bandejas representa unidades.
    total_bandejas = 0.0
    for r in recepciones_main:
        for p in r.get('productos', []) or []:
            if (p.get('Categoria') or '').upper() == 'BANDEJAS':
                total_bandejas += p.get('Kg Hechos', 0) or 0

    prev_agg = None
    if include_prev_week:
        recepciones_prev = [r for r in recepciones_all if _in_range(r, prev_start, prev_end)]
        prev_agg = _aggregate_by_fruta(recepciones_prev)

    month_agg = None
    if include_month_accum:
        recepciones_month = [r for r in recepciones_all if _in_range(r, month_start, f_fin)]
        month_agg = _aggregate_by_fruta(recepciones_month)

    # Generar PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []

    # Calcular semana ISO y temporada basada en las fechas
    semana_inicio = f_inicio.isocalendar()[1]
    semana_fin = f_fin.isocalendar()[1]
    if semana_inicio == semana_fin:
        semana_str = f"Semana {semana_inicio}"
    else:
        semana_str = f"Semanas {semana_inicio}-{semana_fin}"
    
    # Temporada: Oct año N - Sep año N+1
    # Si estamos en Oct-Dic, temporada es año_actual-año_siguiente
    # Si estamos en Ene-Sep, temporada es año_anterior-año_actual
    if f_fin.month >= 10:
        temp_año_ini = f_fin.year
    else:
        temp_año_ini = f_fin.year - 1
    temporada_str = f"Temporada {temp_año_ini}-{temp_año_ini + 1}"

    title = f"Informe de Recepciones MP: {fecha_inicio} a {fecha_fin}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 4))
    # Agregar semana y temporada
    elements.append(Paragraph(f"<b>{semana_str}</b> | <b>{temporada_str}</b>", styles['Normal']))
    elements.append(Spacer(1, 4))
    meta = f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    elements.append(Paragraph(meta, styles['Normal']))
    elements.append(Spacer(1, 12))

    # Header/footer drawing
    PAGE_WIDTH, PAGE_HEIGHT = A4

    def _draw_header_footer(canvas, doc):
        canvas.saveState()
        # Header: optional logo + title + date range
        header_y = PAGE_HEIGHT - 40
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                max_h = 36
                scale = max_h / float(ih)
                draw_w = iw * scale
                canvas.drawImage(img, doc.leftMargin, header_y - max_h + 6, width=draw_w, height=max_h, preserveAspectRatio=True)
            except Exception:
                pass
        # Title at center
        canvas.setFont('Helvetica-Bold', 10)
        canvas.drawCentredString(PAGE_WIDTH / 2.0, header_y - 6, title)
        # Date range at right
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, header_y - 6, f"Rango: {fecha_inicio} - {fecha_fin}")

        # Footer: page number
        canvas.setFont('Helvetica', 8)
        page_text = f"Página {doc.page}"
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 20, page_text)
        canvas.restoreState()

    # Tabla principal por fruta
    elements.append(Paragraph("Resumen por Tipo de Fruta", styles['Heading2']))
    # KPIs generales
    elements.append(Paragraph(f"Total Kg Recepcionados (fruta): {total_kg:,.2f}", styles['Normal']))
    elements.append(Paragraph(f"Bandejas recepcionadas (unidades): {total_bandejas:,.0f}", styles['Normal']))
    elements.append(Paragraph(f"Costo Total MP: ${total_costo:,.0f}", styles['Normal']))
    elements.append(Spacer(1, 6))
    
    # Nota sobre cálculo de costo promedio
    elements.append(Paragraph(
        "<i>Nota: Costo Promedio/kg = Costo Total ÷ Kg Recepcionados (excluyendo bandejas)</i>",
        styles['Normal']
    ))
    elements.append(Spacer(1, 8))
    
    # Desglose de envases por tipo
    envases_por_tipo = _aggregate_envases(recepciones_main)
    if envases_por_tipo:
        elements.append(Paragraph("Detalle Envases Recepcionados por Tipo", styles['Heading3']))
        envases_tbl = [["Tipo de Envase", "Cantidad (unidades)"]]
        total_envases = 0
        for nombre, cantidad in sorted(envases_por_tipo.items(), key=lambda x: x[1], reverse=True):
            envases_tbl.append([nombre, f"{cantidad:,.0f}"])
            total_envases += cantidad
        # Fila de totales
        envases_tbl.append(["TOTAL", f"{total_envases:,.0f}"])
        env_t = Table(envases_tbl, hAlign='LEFT', repeatRows=1)
        env_t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#666666')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Total row bold
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),  # Total row grey
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(KeepTogether([env_t]))
        elements.append(Spacer(1, 12))

    tbl_data = [["Tipo Fruta", "Kg", "Costo Total", "Costo Promedio/kg", "% IQF", "% Block", "# Recepciones"]]
    for r in main_agg:
        costo_prom = f"${r['costo_prom']:,.2f}" if r['costo_prom'] is not None else "-"
        tbl_data.append([
            r['tipo_fruta'],
            f"{r['kg']:,.2f}",
            f"${r['costo']:,.0f}",
            costo_prom,
            f"{r['prom_iqf']:.2f}%",
            f"{r['prom_block']:.2f}%",
            str(r['n_recepciones'])
        ])
    # Fila de totales
    tbl_data.append([
        'TOTAL',
        f"{total_kg:,.2f}",
        f"${total_costo:,.0f}",
        '-',
        '-',
        '-',
        ''
    ])
    # repeatRows=1 para repetir el encabezado en páginas siguientes; envolver en KeepTogether
    t = Table(tbl_data, hAlign='LEFT', repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(KeepTogether([t]))
    elements.append(Spacer(1, 12))

    # Gráfico: Kg por Tipo de Fruta (matplotlib)
    try:
        labels = [r['tipo_fruta'] for r in main_agg]
        values = [r['kg'] for r in main_agg]
        if labels and values:
            # Bar chart
            fig, ax = plt.subplots(figsize=(6, 3))
            ax.bar(labels, values, color='#2b8cbe')
            ax.set_ylabel('Kg')
            ax.set_title('Kg Recepcionados por Tipo de Fruta')
            ax.tick_params(axis='x', rotation=45)
            plt.tight_layout()
            img_buf = BytesIO()
            fig.savefig(img_buf, format='png', dpi=150)
            plt.close(fig)
            img_buf.seek(0)
            img = Image(ImageReader(img_buf), width=450, height=200)
            elements.append(img)
            elements.append(Spacer(1, 8))

            # Pie chart showing % Kg per fruit
            if include_pie and sum(values) > 0:
                try:
                    fig2, ax2 = plt.subplots(figsize=(4, 3))
                    ax2.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 8})
                    ax2.axis('equal')
                    ax2.set_title('% Kg por Tipo de Fruta', fontsize=9)
                    plt.tight_layout()
                    pie_buf = BytesIO()
                    fig2.savefig(pie_buf, format='png', dpi=150)
                    plt.close(fig2)
                    pie_buf.seek(0)
                    pie_img = Image(ImageReader(pie_buf), width=220, height=160)
                    elements.append(pie_img)
                    elements.append(Spacer(1, 12))
                except Exception:
                    pass
    except Exception:
        # si falla el gráfico, continuar sin él
        pass

    # Top productores por fruta
    elements.append(Paragraph("Top Productores por Kg (por Tipo de Fruta)", styles['Heading2']))
    for r in main_agg:
        elements.append(Paragraph(r['tipo_fruta'], styles['Heading3']))
        pdata = [["Productor", "Kg"]]
        total_especie = 0
        for prod, kg in r['top_productores']:
            pdata.append([prod, f"{kg:,.2f}"])
            total_especie += kg
        # Fila de total por especie
        pdata.append(["TOTAL", f"{total_especie:,.2f}"])
        pt = Table(pdata, hAlign='LEFT', repeatRows=1)
        pt.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),  # Total row bold
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(KeepTogether([pt]))
        elements.append(Spacer(1, 6))

    # Semana anterior
    if prev_agg is not None:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Resumen - Semana Anterior", styles['Heading2']))
        p_tbl = [["Tipo Fruta", "Kg", "Costo Total", "Costo Promedio/kg"]]
        prev_total_kg = 0
        prev_total_costo = 0
        for r in prev_agg:
            costo_prom = f"${r['costo_prom']:,.2f}" if r['costo_prom'] is not None else "-"
            p_tbl.append([r['tipo_fruta'], f"{r['kg']:,.2f}", f"${r['costo']:,.0f}", costo_prom])
            prev_total_kg += r['kg']
            prev_total_costo += r['costo']
        # Fila de totales
        p_tbl.append(["TOTAL", f"{prev_total_kg:,.2f}", f"${prev_total_costo:,.0f}", "-"])
        pt2 = Table(p_tbl, hAlign='LEFT', repeatRows=1)
        pt2.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0'))
        ]))
        elements.append(KeepTogether([pt2]))

    # Acumulado parcial mes
    if month_agg is not None:
        elements.append(Spacer(1, 12))
        elements.append(Paragraph("Acumulado Parcial del Mes", styles['Heading2']))
        m_tbl = [["Tipo Fruta", "Kg", "Costo Total", "Costo Promedio/kg"]]
        month_total_kg = 0
        month_total_costo = 0
        for r in month_agg:
            costo_prom = f"${r['costo_prom']:,.2f}" if r['costo_prom'] is not None else "-"
            m_tbl.append([r['tipo_fruta'], f"{r['kg']:,.2f}", f"${r['costo']:,.0f}", costo_prom])
            month_total_kg += r['kg']
            month_total_costo += r['costo']
        # Fila de totales
        m_tbl.append(["TOTAL", f"{month_total_kg:,.2f}", f"${month_total_costo:,.0f}", "-"])
        mt = Table(m_tbl, hAlign='LEFT', repeatRows=1)
        mt.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0'))
        ]))
        elements.append(KeepTogether([mt]))

    # Build document with header/footer callbacks
    doc.build(elements, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
