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
        # Excluir productor ADMINISTRADOR
        productor = (r.get('productor') or '').strip()
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
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
    Agrupa recepciones por tipo_fruta (del producto) y luego por manejo.
    Retorna estructura jerárquica para mostrar en tablas.
    """
    # Estructura: {tipo_fruta: {manejo: {kg, costo, iqf_vals, block_vals}}}
    agrup = {}
    
    for r in recepciones:
        # Excluir productor ADMINISTRADOR
        productor = (r.get('productor') or '').strip()
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
        # Tipo de fruta del QC (para asociar IQF/Block)
        tipo_fruta_qc = (r.get('tipo_fruta') or '').strip()
        
        # IQF/Block son a nivel de recepción
        iqf_val = r.get('total_iqf', 0) or 0
        block_val = r.get('total_block', 0) or 0
        
        # Rastrear manejos por cada tipo de fruta
        manejos_por_tipo = {}
        
        # Recorrer productos para obtener tipo y manejo del producto
        for p in r.get('productos', []) or []:
            cat = _normalize_categoria(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue  # Excluir bandejas
            
            kg = p.get('Kg Hechos', 0) or 0
            if kg <= 0:
                continue  # Ignorar productos con 0 kg
            
            # Usar TipoFruta del producto, con fallback al tipo_fruta del QC
            tipo = (p.get('TipoFruta') or tipo_fruta_qc or '').strip()
            if not tipo:
                continue
            
            manejo = (p.get('Manejo') or '').strip()
            if not manejo:
                manejo = 'Sin Manejo'
            
            # Rastrear manejos por tipo
            if tipo not in manejos_por_tipo:
                manejos_por_tipo[tipo] = set()
            manejos_por_tipo[tipo].add(manejo)
            
            if tipo not in agrup:
                agrup[tipo] = {}
            
            if manejo not in agrup[tipo]:
                agrup[tipo][manejo] = {
                    'kg': 0.0,
                    'costo': 0.0,
                    'iqf_vals': [],
                    'block_vals': []
                }
            
            costo = p.get('Costo Total', 0) or 0
            agrup[tipo][manejo]['kg'] += kg
            agrup[tipo][manejo]['costo'] += costo
        
        # Agregar IQF/Block SOLO al tipo de fruta del QC
        # (no a todos los productos, ya que IQF/Block son mediciones del tipo_fruta del QC)
        if tipo_fruta_qc and tipo_fruta_qc in manejos_por_tipo:
            for manejo in manejos_por_tipo[tipo_fruta_qc]:
                if tipo_fruta_qc in agrup and manejo in agrup[tipo_fruta_qc]:
                    agrup[tipo_fruta_qc][manejo]['iqf_vals'].append(iqf_val)
                    agrup[tipo_fruta_qc][manejo]['block_vals'].append(block_val)

    
    # Convertir a lista jerárquica
    out = []
    for tipo, manejos in agrup.items():
        tipo_kg = sum(m['kg'] for m in manejos.values())
        
        # Omitir tipos de fruta sin kg
        if tipo_kg <= 0:
            continue
            
        tipo_costo = sum(m['costo'] for m in manejos.values())
        
        manejo_list = []
        for manejo, v in sorted(manejos.items()):
            kg = v['kg']
            # Omitir manejos sin kg
            if kg <= 0:
                continue
                
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
        
        # Omitir tipos sin manejos válidos
        if not manejo_list:
            continue
        
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
        
        # Excluir productor ADMINISTRADOR
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
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
                                  include_pie: bool = True,
                                  solo_hechas: bool = True) -> bytes:
    """Genera un PDF con el resumen por fruta para el rango dado.
    Opciones para incluir la semana previa y acumulado parcial del mes.
    Args:
        solo_hechas: Si True, solo incluye recepciones en estado 'done'. Si False, incluye todas.
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

    recepciones_all = get_recepciones_mp(username, password, fetch_start.isoformat(), f_fin.isoformat(), solo_hechas=solo_hechas)

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
    
    # Obtener precios proyectados del servicio de abastecimiento
    precios_proyectados = {}
    try:
        from backend.services.abastecimiento_service import get_precios_por_especie
        precios_data = get_precios_por_especie(planta=None, especie=None)
        for item in precios_data:
            especie = item.get('especie', '')
            precio = item.get('precio_proyectado', 0)
            precios_proyectados[especie] = precio
    except Exception as e:
        print(f"Error obteniendo precios proyectados para PDF: {e}")
    
    tbl_data = [["Tipo Fruta / Manejo", "Kg", "Costo Total", "$/Kg", "$/Kg Proy", "Desv", "% IQF", "% Block"]]
    tipo_fruta_rows = []  # Para trackear filas de tipo fruta (para estilo)
    
    # Función para calcular y formatear desviación
    def calc_desv(costo_kg, precio_proy):
        if precio_proy > 0 and costo_kg > 0:
            desv = ((costo_kg - precio_proy) / precio_proy) * 100
            if desv <= 0:
                return f"✓{abs(desv):.1f}%"  # Favorable
            elif desv <= 3:
                return f"+{desv:.1f}%"  # Verde (1-3%)
            elif desv <= 8:
                return f"⚠+{desv:.1f}%"  # Amarillo (3-8%)
            else:
                return f"‼+{desv:.1f}%"  # Rojo (>8%)
        return "-"
    
    row_idx = 1  # Empezamos en 1 (después del header)
    for tipo_data in main_agg_manejo:
        tipo_fruta = tipo_data['tipo_fruta']
        tipo_kg = tipo_data['kg_total']
        tipo_costo = tipo_data['costo_total']
        tipo_costo_prom_val = tipo_costo / tipo_kg if tipo_kg > 0 else 0
        tipo_costo_prom = fmt_dinero(tipo_costo_prom_val, 2) if tipo_kg > 0 else "-"
        
        # Precio proyectado para este tipo de fruta
        precio_proy_tipo = precios_proyectados.get(tipo_fruta, 0)
        precio_proy_str = fmt_dinero(precio_proy_tipo, 0) if precio_proy_tipo > 0 else "-"
        desv_tipo = calc_desv(tipo_costo_prom_val, precio_proy_tipo)
        
        # Fila de Tipo Fruta (totalizador)
        tbl_data.append([
            tipo_fruta,
            fmt_numero(tipo_kg, 2),
            fmt_dinero(tipo_costo),
            tipo_costo_prom,
            precio_proy_str,
            desv_tipo,
            "-",
            "-"
        ])
        tipo_fruta_rows.append(row_idx)
        row_idx += 1
        
        # Filas de Manejo (indentadas)
        for m in tipo_data['manejos']:
            manejo_name = m['manejo']
            costo_prom_val = m['costo_prom'] if m['costo_prom'] is not None else 0
            costo_prom = fmt_dinero(costo_prom_val, 2) if costo_prom_val > 0 else "-"
            
            # Precio proyectado para la combinación tipo + manejo
            manejo_norm = 'Orgánico' if 'org' in manejo_name.lower() else 'Convencional'
            especie_manejo = f"{tipo_fruta} {manejo_norm}"
            precio_proy_manejo = precios_proyectados.get(especie_manejo, precios_proyectados.get(tipo_fruta, 0))
            precio_proy_manejo_str = fmt_dinero(precio_proy_manejo, 0) if precio_proy_manejo > 0 else "-"
            desv_manejo = calc_desv(costo_prom_val, precio_proy_manejo)
            
            tbl_data.append([
                f"   → {manejo_name}",  # Indentado
                fmt_numero(m['kg'], 2),
                fmt_dinero(m['costo']),
                costo_prom,
                precio_proy_manejo_str,
                desv_manejo,
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
    elements.append(Spacer(1, 6))
    
    # Leyenda de desviación de precios
    leyenda_desv = Paragraph(
        "<b>Leyenda Desv:</b> ✓ Favorable (pagando menos) · +X% = 1-3% ok · ⚠ = 3-8% atención · ‼ = >8% crítico",
        styles['Normal']
    )
    elements.append(leyenda_desv)
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
    titulo_detalle = Paragraph("Detalle por Tipo de Fruta", styles['Heading2'])
    
    fruta_agg = _aggregate_by_fruta_productor_manejo(recepciones_main)
    
    # Crear estilo para celdas con texto largo que necesita wrap
    from reportlab.lib.styles import ParagraphStyle
    cell_style = ParagraphStyle('CellStyle', fontName='Helvetica', fontSize=8, leading=10)
    cell_style_bold = ParagraphStyle('CellStyleBold', fontName='Helvetica-Bold', fontSize=8, leading=10)
    cell_style_italic = ParagraphStyle('CellStyleItalic', fontName='Helvetica-Oblique', fontSize=8, leading=10)
    # Estilo para header con texto blanco
    header_style = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.whitesmoke)
    
    # Crear tabla jerárquica - usar Paragraph para la primera columna
    detail_tbl = [[Paragraph("Tipo Fruta / Productor / Manejo", header_style), "Kg", "Costo Total", "Costo Prom/Kg"]]
    fruta_rows = []  # Filas de tipo fruta para estilo
    productor_rows = []  # Filas de productores para estilo
    row_idx = 1
    
    for fruta_data in fruta_agg:
        # Fila de Tipo Fruta (totalizador principal)
        costo_prom_str = fmt_dinero(fruta_data['costo_prom'], 2) if fruta_data['costo_prom'] is not None else "-"
        detail_tbl.append([
            Paragraph(f"<b>{fruta_data['tipo_fruta']}</b>", cell_style_bold),
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
                Paragraph(f"<i>→ {prod_data['productor']}</i>", cell_style_italic),
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
                    Paragraph(f"&nbsp;&nbsp;&nbsp;↳ {manejo_data['manejo']}", cell_style),
                    fmt_numero(manejo_data['kg'], 2),
                    fmt_dinero(manejo_data['costo']),
                    costo_prom_manejo
                ])
                row_idx += 1
    
    # Fila de TOTAL GENERAL
    total_kg_detail = sum(f['kg'] for f in fruta_agg)
    total_costo_detail = sum(f['costo'] for f in fruta_agg)
    total_costo_prom_detail = fmt_dinero(total_costo_detail / total_kg_detail, 2) if total_kg_detail > 0 else "-"
    detail_tbl.append([Paragraph("<b>TOTAL GENERAL</b>", cell_style_bold), fmt_numero(total_kg_detail, 2), fmt_dinero(total_costo_detail), total_costo_prom_detail])
    
    # Anchos de columna: Nombre amplio (para productores largos con wrap), Kg, Costo Total, Costo Prom
    col_widths = [280, 60, 90, 80]
    detail_table = Table(detail_tbl, hAlign='LEFT', repeatRows=1, colWidths=col_widths)
    
    # Estilo base
    detail_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        # Fila total general
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#d0d0d0')),
    ]
    
    # Estilo para filas de Tipo Fruta (fondo gris)
    for row_num in fruta_rows:
        detail_style.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#e8e8e8')))
    
    # Estilo para filas de Productor (fondo más claro)
    for row_num in productor_rows:
        detail_style.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor('#f5f5f5')))
    
    detail_table.setStyle(TableStyle(detail_style))
    
    # Agregar título y tabla juntos
    elements.append(titulo_detalle)
    elements.append(Spacer(1, 6))
    elements.append(detail_table)
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


def generate_bandejas_report_pdf(
    kpis: Dict[str, Any],
    df_gestion: List[Dict[str, Any]],
    df_productores: List[Dict[str, Any]],
    filtros: Optional[Dict[str, str]] = None,
    logo_path: Optional[str] = None
) -> bytes:
    """
    Genera un PDF con el informe de Bandejas.
    
    Args:
        kpis: Diccionario con KPIs consolidados (despachadas, recepcionadas, en_productores, stock_total, limpias, sucias)
        df_gestion: Lista de dicts con datos de gestión de bandejas
        df_productores: Lista de dicts con datos por productor
        filtros: Diccionario opcional con los filtros aplicados (año, mes, temporada)
        logo_path: Ruta opcional al logo
    
    Returns:
        bytes: Contenido del PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=30, rightMargin=30, topMargin=60, bottomMargin=40)
    styles = getSampleStyleSheet()
    elements = []
    
    generated_str = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    PAGE_WIDTH, PAGE_HEIGHT = A4
    
    # Título
    filtro_str = ""
    if filtros:
        if filtros.get('temporada'):
            filtro_str = f" - {filtros['temporada']}"
        elif filtros.get('año') and filtros.get('mes'):
            filtro_str = f" - {filtros['mes']}/{filtros['año']}"
        elif filtros.get('año'):
            filtro_str = f" - Año {filtros['año']}"
    
    title = f"Informe de Bandejas{filtro_str}"
    elements.append(Paragraph(title, styles['Title']))
    elements.append(Spacer(1, 12))
    
    # --- KPIs Consolidados ---
    elements.append(Paragraph("KPIs Consolidados", styles['Heading2']))
    elements.append(Spacer(1, 6))
    
    kpi_data = [
        ["📤 Despachadas", "📥 Recepcionadas", "🏠 En Productores"],
        [fmt_numero(kpis.get('despachadas', 0)), fmt_numero(kpis.get('recepcionadas', 0)), fmt_numero(kpis.get('en_productores', 0))],
        ["📦 Stock Total", "✨ Limpias", "🧹 Sucias"],
        [fmt_numero(kpis.get('stock_total', 0)), fmt_numero(kpis.get('limpias', 0)), fmt_numero(kpis.get('sucias', 0))]
    ]
    
    kpi_table = Table(kpi_data, hAlign='LEFT', colWidths=[170, 170, 170])
    kpi_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BACKGROUND', (0, 2), (-1, 2), colors.HexColor('#333333')),
        ('TEXTCOLOR', (0, 2), (-1, 2), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(kpi_table)
    elements.append(Spacer(1, 20))
    
    # --- Tabla Gestión Bandejas ---
    if df_gestion:
        elements.append(Paragraph("Gestión de Bandejas", styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        gestion_header = ["Nombre", "Sucias", "Limpias", "Proyectados", "Diferencia"]
        gestion_data = [gestion_header]
        
        for row in df_gestion:
            gestion_data.append([
                row.get('Nombre', ''),
                fmt_numero(row.get('Bandejas Sucias', 0)),
                fmt_numero(row.get('Bandejas Limpias', 0)),
                fmt_numero(row.get('Proyectados', 0)),
                fmt_numero(row.get('Diferencia', 0))
            ])
        
        gestion_table = Table(gestion_data, hAlign='LEFT', repeatRows=1, colWidths=[180, 80, 80, 80, 80])
        gestion_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ]
        
        # Highlight TOTAL row if present
        for i, row in enumerate(df_gestion):
            if row.get('Nombre') == 'TOTAL':
                gestion_style.append(('BACKGROUND', (0, i+1), (-1, i+1), colors.HexColor('#ffc107')))
                gestion_style.append(('FONTNAME', (0, i+1), (-1, i+1), 'Helvetica-Bold'))
        
        gestion_table.setStyle(TableStyle(gestion_style))
        elements.append(gestion_table)
        elements.append(Spacer(1, 20))
    
    # --- Tabla Por Productor ---
    if df_productores:
        elements.append(Paragraph("Detalle por Productor", styles['Heading2']))
        elements.append(Spacer(1, 6))
        
        # Estilo para celdas con texto largo que necesita wrap
        from reportlab.lib.styles import ParagraphStyle
        cell_style = ParagraphStyle('CellStyle', fontName='Helvetica', fontSize=7, leading=9)
        header_style = ParagraphStyle('HeaderStyle', fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.whitesmoke)
        
        prod_header = [
            Paragraph("Productor", header_style), 
            Paragraph("Recepcionadas", header_style), 
            Paragraph("Despachadas", header_style), 
            Paragraph("En Productor", header_style)
        ]
        prod_data = [prod_header]
        
        for row in df_productores:
            # Usar Paragraph para el nombre del productor (permite wrap)
            nombre = row.get('Productor', '')
            prod_data.append([
                Paragraph(nombre, cell_style),
                fmt_numero(row.get('Recepcionadas', 0)),
                fmt_numero(row.get('Despachadas', 0)),
                fmt_numero(row.get('Bandejas en Productor', 0))
            ])
        
        # Anchos: Productor más ancho (280), números más compactos (75 cada uno)
        prod_table = Table(prod_data, hAlign='LEFT', repeatRows=1, colWidths=[280, 75, 75, 75])
        prod_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#333333')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]))
        elements.append(prod_table)
    
    # Header/footer
    def _draw_page(canvas, doc):
        canvas.saveState()
        header_y = PAGE_HEIGHT - 40
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
        canvas.setFont('Helvetica', 8)
        canvas.drawString(doc.leftMargin, 20, f"Generado: {generated_str}")
        canvas.drawRightString(PAGE_WIDTH - doc.rightMargin, 20, f"Página {doc.page}")
        canvas.restoreState()
    
    doc.build(elements, onFirstPage=_draw_page, onLaterPages=_draw_page)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
