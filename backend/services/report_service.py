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


# --- Funciones de formateo chileno ---
def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, (date, datetime)):
            return fecha_str.strftime("%d/%m/%Y")
        if isinstance(fecha_str, str):
            if " " in fecha_str:
                fecha_str = fecha_str.split(" ")[0]
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except:
        pass
    return str(fecha_str)

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

def fmt_dinero(valor, decimales=0):
    """Formatea valor monetario con símbolo $"""
    return f"${fmt_numero(valor, decimales)}"


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


def _aggregate_by_fruta_manejo(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa recepciones por tipo_fruta y luego por manejo (Orgánico/Convencional).
    Retorna estructura jerárquica para mostrar en tablas.
    """
    # Estructura: {tipo_fruta: {manejo: {kg, costo, iqf_vals, block_vals}}}
    agrup = {}
    
    for r in recepciones:
        tipo = (r.get('tipo_fruta') or '').strip()
        if not tipo:
            continue
        
        if tipo not in agrup:
            agrup[tipo] = {}
        
        # IQF/Block son a nivel de recepción
        iqf_val = r.get('total_iqf', 0) or 0
        block_val = r.get('total_block', 0) or 0
        
        # Primero identificar todos los manejos presentes en esta recepción
        manejos_en_recepcion = set()
        
        # Recorrer productos para obtener manejo y sumar kg/costo
        for p in r.get('productos', []) or []:
            cat = _normalize_categoria(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue  # Excluir bandejas
            
            manejo = (p.get('Manejo') or '').strip()
            if not manejo:
                manejo = 'Sin Manejo'
            
            manejos_en_recepcion.add(manejo)
            
            if manejo not in agrup[tipo]:
                agrup[tipo][manejo] = {
                    'kg': 0.0,
                    'costo': 0.0,
                    'iqf_vals': [],
                    'block_vals': []
                }
            
            kg = p.get('Kg Hechos', 0) or 0
            costo = p.get('Costo Total', 0) or 0
            agrup[tipo][manejo]['kg'] += kg
            agrup[tipo][manejo]['costo'] += costo
        
        # Agregar valores IQF/Block a TODOS los manejos presentes en esta recepción
        # (ya que IQF/Block es medición de la recepción, aplica a todos los productos)
        for manejo in manejos_en_recepcion:
            if manejo in agrup[tipo]:
                agrup[tipo][manejo]['iqf_vals'].append(iqf_val)
                agrup[tipo][manejo]['block_vals'].append(block_val)
    
    # Convertir a lista jerárquica
    out = []
    for tipo, manejos in agrup.items():
        tipo_kg = sum(m['kg'] for m in manejos.values())
        tipo_costo = sum(m['costo'] for m in manejos.values())
        
        manejo_list = []
        for manejo, v in sorted(manejos.items()):
            kg = v['kg']
            costo = v['costo']
            costo_prom = (costo / kg) if kg > 0 else None
            prom_iqf = (sum(v['iqf_vals']) / len(v['iqf_vals'])) if v['iqf_vals'] else 0
            prom_block = (sum(v['block_vals']) / len(v['block_vals'])) if v['block_vals'] else 0
            
            manejo_list.append({
                'manejo': manejo,
                'kg': kg,
                'costo': costo,
                'costo_prom': costo_prom,
                'prom_iqf': prom_iqf,
                'prom_block': prom_block
            })
        
        # Ordenar manejos por kg descendente
        manejo_list.sort(key=lambda x: x['kg'], reverse=True)
        
        out.append({
            'tipo_fruta': tipo,
            'kg_total': tipo_kg,
            'costo_total': tipo_costo,
            'manejos': manejo_list
        })
    
    # Ordenar tipos por kg descendente
    out.sort(key=lambda x: x['kg_total'], reverse=True)
    return out


def _aggregate_by_fruta_productor_manejo(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa recepciones por Tipo de Fruta → Productor → Manejo.
    Para cada nivel calcula: Kg, Costo Total, Costo Promedio/Kg.
    """
    # Estructura: {tipo_fruta: {productor: {manejo: {kg, costo}}}}
    agrup = {}
    
    for r in recepciones:
        tipo = (r.get('tipo_fruta') or '').strip()
        if not tipo:
            continue  # Skip recepciones sin tipo de fruta
        
        productor = (r.get('productor') or '').strip()
        if not productor:
            productor = 'Sin Productor'
        
        if tipo not in agrup:
            agrup[tipo] = {}
        
        if productor not in agrup[tipo]:
            agrup[tipo][productor] = {}
        
        # Recorrer productos para obtener manejo y sumar kg/costo
        for p in r.get('productos', []) or []:
            cat = _normalize_categoria(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue  # Excluir bandejas
            
            manejo = (p.get('Manejo') or '').strip()
            if not manejo:
                manejo = 'Sin Manejo'
            
            if manejo not in agrup[tipo][productor]:
                agrup[tipo][productor][manejo] = {'kg': 0.0, 'costo': 0.0}
            
            kg = p.get('Kg Hechos', 0) or 0
            costo = p.get('Costo Total', 0) or 0
            agrup[tipo][productor][manejo]['kg'] += kg
            agrup[tipo][productor][manejo]['costo'] += costo
    
    # Convertir a lista jerárquica
    out = []
    for tipo, productores in agrup.items():
        tipo_kg = 0.0
        tipo_costo = 0.0
        
        productores_list = []
        for productor, manejos in productores.items():
            prod_kg = sum(m['kg'] for m in manejos.values())
            prod_costo = sum(m['costo'] for m in manejos.values())
            prod_costo_prom = (prod_costo / prod_kg) if prod_kg > 0 else None
            
            tipo_kg += prod_kg
            tipo_costo += prod_costo
            
            manejos_list = []
            for manejo, v in sorted(manejos.items()):
                kg = v['kg']
                costo = v['costo']
                costo_prom = (costo / kg) if kg > 0 else None
                manejos_list.append({
                    'manejo': manejo,
                    'kg': kg,
                    'costo': costo,
                    'costo_prom': costo_prom
                })
            
            # Ordenar manejos por kg descendente
            manejos_list.sort(key=lambda x: x['kg'], reverse=True)
            
            productores_list.append({
                'productor': productor,
                'kg': prod_kg,
                'costo': prod_costo,
                'costo_prom': prod_costo_prom,
                'manejos': manejos_list
            })
        
        # Ordenar productores por kg descendente
        productores_list.sort(key=lambda x: x['kg'], reverse=True)
        
        tipo_costo_prom = (tipo_costo / tipo_kg) if tipo_kg > 0 else None
        
        out.append({
            'tipo_fruta': tipo,
            'kg': tipo_kg,
            'costo': tipo_costo,
            'costo_prom': tipo_costo_prom,
            'productores': productores_list
        })
    
    # Ordenar tipos de fruta por kg descendente
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
    generated_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    title = f"Informe de Recepciones MP: {fmt_fecha(fecha_inicio)} a {fmt_fecha(fecha_fin)}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 4))
    # Agregar semana y temporada (fecha de generación va al footer)
    elements.append(Paragraph(f"<b>{semana_str}</b> | <b>{temporada_str}</b>", styles['Normal']))
    elements.append(Spacer(1, 12))

    # Header/footer drawing
    PAGE_WIDTH, PAGE_HEIGHT = A4

    def _draw_first_page(canvas, doc):
        """Primera página: solo footer con info, el título ya está en el contenido."""
        canvas.saveState()
        # Logo en la esquina superior izquierda (si existe)
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
        # Footer: fecha generación a la izquierda, página a la derecha
        canvas.setFont('Helvetica', 8)
        canvas.drawString(doc.leftMargin, 20, f"Generado: {generated_str}")
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 20, f"Página {doc.page}")
        canvas.restoreState()

    def _draw_later_pages(canvas, doc):
        """Páginas posteriores: header compacto + footer."""
        canvas.saveState()
        header_y = PAGE_HEIGHT - 40
        # Logo (si existe)
        if logo_path and os.path.exists(logo_path):
            try:
                img = ImageReader(logo_path)
                iw, ih = img.getSize()
                max_h = 30
                scale = max_h / float(ih)
                draw_w = iw * scale
                canvas.drawImage(img, doc.leftMargin, header_y - max_h + 6, width=draw_w, height=max_h, preserveAspectRatio=True)
            except Exception:
                pass
        # Título compacto al centro
        canvas.setFont('Helvetica-Bold', 9)
        canvas.drawCentredString(PAGE_WIDTH / 2.0, header_y - 6, f"Recepciones MP: {fmt_fecha(fecha_inicio)} a {fmt_fecha(fecha_fin)}")
        # Rango a la derecha
        canvas.setFont('Helvetica', 8)
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, header_y - 6, f"Página {doc.page}")
        # Footer
        canvas.setFont('Helvetica', 8)
        canvas.drawString(doc.leftMargin, 20, f"{semana_str} | {temporada_str}")
        canvas.restoreState()

    # Tabla principal por fruta
    elements.append(Paragraph("Resumen por Tipo de Fruta", styles['Heading2']))
    # KPIs generales
    elements.append(Paragraph(f"Total Kg Recepcionados (fruta): {fmt_numero(total_kg, 2)}", styles['Normal']))
    elements.append(Paragraph(f"Bandejas recepcionadas (unidades): {fmt_numero(total_bandejas, 0)}", styles['Normal']))
    elements.append(Paragraph(f"Costo Total MP: {fmt_dinero(total_costo)}", styles['Normal']))
    elements.append(Spacer(1, 8))
    
    # Desglose de envases por tipo
    envases_por_tipo = _aggregate_envases(recepciones_main)
    if envases_por_tipo:
        elements.append(Paragraph("Detalle Envases Recepcionados por Tipo", styles['Heading3']))
        envases_tbl = [["Tipo de Envase", "Cantidad (unidades)"]]
        total_envases = 0
        for nombre, cantidad in sorted(envases_por_tipo.items(), key=lambda x: x[1], reverse=True):
            envases_tbl.append([nombre, fmt_numero(cantidad, 0)])
            total_envases += cantidad
        # Fila de totales
        envases_tbl.append(["TOTAL", fmt_numero(total_envases, 0)])
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

    # Tabla principal con jerarquía Tipo Fruta → Manejo
    main_agg_manejo = _aggregate_by_fruta_manejo(recepciones_main)
    
    tbl_data = [["Tipo Fruta / Manejo", "Kg", "Costo Total", "Costo Promedio/kg", "% IQF", "% Block"]]
    tipo_fruta_rows = []  # Para trackear filas de tipo fruta (para estilo)
    
    row_idx = 1  # Empezamos en 1 (después del header)
    for tipo_data in main_agg_manejo:
        tipo_fruta = tipo_data['tipo_fruta']
        tipo_kg = tipo_data['kg_total']
        tipo_costo = tipo_data['costo_total']
        tipo_costo_prom = fmt_dinero(tipo_costo / tipo_kg, 2) if tipo_kg > 0 else "-"
        
        # Fila de Tipo Fruta (totalizador)
        tbl_data.append([
            tipo_fruta,
            fmt_numero(tipo_kg, 2),
            fmt_dinero(tipo_costo),
            tipo_costo_prom,
            "-",
            "-"
        ])
        tipo_fruta_rows.append(row_idx)
        row_idx += 1
        
        # Filas de Manejo (indentadas)
        for m in tipo_data['manejos']:
            manejo_name = m['manejo']
            costo_prom = fmt_dinero(m['costo_prom'], 2) if m['costo_prom'] is not None else "-"
            tbl_data.append([
                f"   → {manejo_name}",  # Indentado
                fmt_numero(m['kg'], 2),
                fmt_dinero(m['costo']),
                costo_prom,
                f"{fmt_numero(m['prom_iqf'], 2)}%",
                f"{fmt_numero(m['prom_block'], 2)}%"
            ])
            row_idx += 1
    
    # Fila de totales generales
    tbl_data.append([
        'TOTAL GENERAL',
        fmt_numero(total_kg, 2),
        fmt_dinero(total_costo),
        '-',
        '-',
        '-'
    ])
    
    t = Table(tbl_data, hAlign='LEFT', repeatRows=1)
    
    # Estilo base
    style_commands = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Fila total general
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0')),
    ]
    
    # Estilo para filas de Tipo Fruta (negrita, fondo gris claro)
    for row_num in tipo_fruta_rows:
        style_commands.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        style_commands.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#f0f0f0')))
    
    t.setStyle(TableStyle(style_commands))
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

    # Detalle por Tipo Fruta → Productor → Manejo
    elements.append(Paragraph("Detalle por Tipo de Fruta", styles['Heading2']))
    
    fruta_agg = _aggregate_by_fruta_productor_manejo(recepciones_main)
    
    # Crear tabla jerárquica
    detail_tbl = [["Tipo Fruta / Productor / Manejo", "Kg", "Costo Total", "Costo Prom/Kg"]]
    fruta_rows = []  # Filas de tipo fruta para estilo
    productor_rows = []  # Filas de productores para estilo
    row_idx = 1
    
    for fruta_data in fruta_agg:
        # Fila de Tipo Fruta (totalizador principal)
        costo_prom_str = fmt_dinero(fruta_data['costo_prom'], 2) if fruta_data['costo_prom'] is not None else "-"
        detail_tbl.append([
            fruta_data['tipo_fruta'],
            fmt_numero(fruta_data['kg'], 2),
            fmt_dinero(fruta_data['costo']),
            costo_prom_str
        ])
        fruta_rows.append(row_idx)
        row_idx += 1
        
        # Filas de Productor (indentadas)
        for prod_data in fruta_data['productores']:
            costo_prom_prod = fmt_dinero(prod_data['costo_prom'], 2) if prod_data['costo_prom'] is not None else "-"
            detail_tbl.append([
                f"   → {prod_data['productor']}",
                fmt_numero(prod_data['kg'], 2),
                fmt_dinero(prod_data['costo']),
                costo_prom_prod
            ])
            productor_rows.append(row_idx)
            row_idx += 1
            
            # Filas de Manejo (doble indentación)
            for manejo_data in prod_data['manejos']:
                costo_prom_manejo = fmt_dinero(manejo_data['costo_prom'], 2) if manejo_data['costo_prom'] is not None else "-"
                detail_tbl.append([
                    f"      ↳ {manejo_data['manejo']}",
                    fmt_numero(manejo_data['kg'], 2),
                    fmt_dinero(manejo_data['costo']),
                    costo_prom_manejo
                ])
                row_idx += 1
    
    # Fila de TOTAL GENERAL
    total_kg_detail = sum(f['kg'] for f in fruta_agg)
    total_costo_detail = sum(f['costo'] for f in fruta_agg)
    total_costo_prom_detail = fmt_dinero(total_costo_detail / total_kg_detail, 2) if total_kg_detail > 0 else "-"
    detail_tbl.append(["TOTAL GENERAL", fmt_numero(total_kg_detail, 2), fmt_dinero(total_costo_detail), total_costo_prom_detail])
    
    # Anchos de columna: Nombre amplio, Kg, Costo Total, Costo Prom
    col_widths = [240, 70, 90, 80]
    detail_table = Table(detail_tbl, hAlign='LEFT', repeatRows=1, colWidths=col_widths)
    
    # Estilo base
    detail_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Fila total general
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d0d0d0')),
    ]
    
    # Estilo para filas de Tipo Fruta (negrita, fondo gris)
    for row_num in fruta_rows:
        detail_style.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        detail_style.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#e8e8e8')))
    
    # Estilo para filas de Productor (itálica, fondo más claro)
    for row_num in productor_rows:
        detail_style.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Oblique'))
        detail_style.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#f5f5f5')))
    
    detail_table.setStyle(TableStyle(detail_style))
    elements.append(KeepTogether([detail_table]))
    elements.append(Spacer(1, 12))

    # Semana anterior
    if prev_agg is not None:
        p_tbl = [["Tipo Fruta", "Kg", "Costo Total", "Costo Promedio/kg"]]
        prev_total_kg = 0
        prev_total_costo = 0
        for r in prev_agg:
            costo_prom = fmt_dinero(r['costo_prom'], 2) if r['costo_prom'] is not None else "-"
            p_tbl.append([r['tipo_fruta'], fmt_numero(r['kg'], 2), fmt_dinero(r['costo']), costo_prom])
            prev_total_kg += r['kg']
            prev_total_costo += r['costo']
        # Fila de totales
        p_tbl.append(["TOTAL", fmt_numero(prev_total_kg, 2), fmt_dinero(prev_total_costo), "-"])
        pt2 = Table(p_tbl, hAlign='LEFT', repeatRows=1)
        pt2.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0'))
        ]))
        # Mantener título y tabla juntos
        elements.append(Spacer(1, 12))
        elements.append(KeepTogether([
            Paragraph("Resumen - Semana Anterior", styles['Heading2']),
            Spacer(1, 6),
            pt2
        ]))

    # Acumulado parcial mes
    if month_agg is not None:
        m_tbl = [["Tipo Fruta", "Kg", "Costo Total", "Costo Promedio/kg"]]
        month_total_kg = 0
        month_total_costo = 0
        for r in month_agg:
            costo_prom = fmt_dinero(r['costo_prom'], 2) if r['costo_prom'] is not None else "-"
            m_tbl.append([r['tipo_fruta'], fmt_numero(r['kg'], 2), fmt_dinero(r['costo']), costo_prom])
            month_total_kg += r['kg']
            month_total_costo += r['costo']
        # Fila de totales
        m_tbl.append(["TOTAL", fmt_numero(month_total_kg, 2), fmt_dinero(month_total_costo), "-"])
        mt = Table(m_tbl, hAlign='LEFT', repeatRows=1)
        mt.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f2f2f2')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#e0e0e0'))
        ]))
        # Mantener título y tabla juntos
        elements.append(Spacer(1, 12))
        elements.append(KeepTogether([
            Paragraph("Acumulado Parcial del Mes", styles['Heading2']),
            Spacer(1, 6),
            mt
        ]))

    # Build document with header/footer callbacks
    doc.build(elements, onFirstPage=_draw_first_page, onLaterPages=_draw_later_pages)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
