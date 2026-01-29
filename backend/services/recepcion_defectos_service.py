"""
Servicio para generar reporte Excel de recepciones con detalles de defectos.
Basado en el script generar_reporte_recepciones_excel.py
"""
from shared.odoo_client import OdooClient
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from io import BytesIO
from typing import List, Optional


def generar_reporte_defectos_excel(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
    origenes: Optional[List[str]] = None,
    solo_hechas: bool = True
) -> bytes:
    """
    Genera un reporte Excel detallado de recepciones con información de defectos.
    
    Args:
        username: Usuario de Odoo
        password: Password de Odoo
        fecha_inicio: Fecha inicio en formato YYYY-MM-DD
        fecha_fin: Fecha fin en formato YYYY-MM-DD
        origenes: Lista de orígenes ['RFP', 'VILKUN', 'SAN JOSE']. Si None, incluye todos.
        solo_hechas: Si True, solo recepciones en estado 'done'
        
    Returns:
        bytes del archivo Excel generado
    """
    
    # Conectar a Odoo
    odoo = OdooClient(username=username, password=password)
    
    # Analizar campos disponibles
    campos_picking = odoo.execute('stock.picking', 'fields_get', [], {'attributes': ['string', 'type']})
    campos_template = odoo.execute('product.template', 'fields_get', [], {'attributes': ['string', 'type']})
    campos_quality = odoo.execute('quality.check', 'fields_get', [], {'attributes': ['string', 'type']})
    
    # Determinar campos a usar
    campo_guia = _determinar_campo(campos_picking, [
        'x_studio_gua_de_despacho', 'x_studio_gua_despacho', 'x_studio_guia_despacho'
    ])
    
    campo_categoria_prod = _determinar_campo(campos_picking, [
        'x_studio_categora_de_producto', 'x_studio_categoria_de_producto'
    ])
    
    campos_template_usar = {
        'variedad': _determinar_campo(campos_template, ['x_studio_categora_variedad', 'x_studio_variedad']),
        'manejo': _determinar_campo(campos_template, ['x_studio_categora_tipo_de_manejo', 'x_studio_manejo_del_producto']),
        'categoria': 'categ_id',  # Campo estándar de Odoo para categoría de producto
    }
    
    campos_quality_usar = {
        'tipo_fruta_qc': _determinar_campo(campos_quality, ['x_studio_tipo_de_fruta']),
        'pallet': _determinar_campo(campos_quality, ['x_studio_n_de_palet_o_paquete', 'x_studio_n_palet']),
        'clasificacion': _determinar_campo(campos_quality, ['x_studio_calific_final', 'x_studio_calificacin_final']),
        'total_defectos': _determinar_campo(campos_quality, ['x_studio_total_def_calidad', 'x_studio_total_de_defectos_']),
        'temperatura': _determinar_campo(campos_quality, ['x_studio_temperatura']),
        'hongos': _determinar_campo(campos_quality, ['x_studio_hongos']),
        'inmadura': _determinar_campo(campos_quality, ['x_studio_inmadura']),
        'sobremadura': _determinar_campo(campos_quality, ['x_studio_sobremadura', 'x_studio_sobre_madura']),
        'deshidratado': _determinar_campo(campos_quality, ['x_studio_deshidratado']),
        'crumble': _determinar_campo(campos_quality, ['x_studio_crumble']),
        'dano_mecanico': _determinar_campo(campos_quality, ['x_studio_dao_mecanico', 'x_studio_dano_mecanico']),
        'dano_insecto': _determinar_campo(campos_quality, ['x_studio_presencia_de_insectos', 'x_studio_totdaoinsecto', 'x_studio_dao_insecto']),
        'deformes': _determinar_campo(campos_quality, ['x_studio_frutos_deformes', 'x_studio_deformes']),
        'fruta_verde': _determinar_campo(campos_quality, ['x_studio_fruta_verde']),
        'herida_partida': _determinar_campo(campos_quality, ['x_studio_heridapartidamolida', 'x_studio_heridapartiduramolida']),
        'materias_extranas': _determinar_campo(campos_quality, ['x_studio_materias_extraas', 'x_studio_materias_extranas']),
    }
    
    # Mapeo de picking types
    ORIGEN_PICKING_MAP = {
        "RFP": 1,
        "VILKUN": 217,
        "SAN JOSE": 164
    }
    
    # Si no se especifican orígenes, usar todos
    if not origenes:
        origenes = list(ORIGEN_PICKING_MAP.keys())
    
    # Obtener recepciones
    todas_recepciones = []
    for origen in origenes:
        if origen not in ORIGEN_PICKING_MAP:
            continue
            
        picking_type_id = ORIGEN_PICKING_MAP[origen]
        
        domain = [
            ('picking_type_id', '=', picking_type_id),
            ('scheduled_date', '>=', fecha_inicio),
            ('scheduled_date', '<=', fecha_fin),
        ]
        
        if solo_hechas:
            domain.append(('state', '=', 'done'))
        
        if campo_categoria_prod:
            domain.append((campo_categoria_prod, '=', 'MP'))
        
        campos_leer = ['id', 'name', 'scheduled_date', 'partner_id']
        if campo_guia:
            campos_leer.append(campo_guia)
        
        recepciones = odoo.search_read('stock.picking', domain, campos_leer, limit=5000)
        
        for rec in recepciones:
            rec['origen'] = origen
        
        todas_recepciones.extend(recepciones)
    
    if not todas_recepciones:
        # Generar Excel vacío
        return _generar_excel_vacio()
    
    # Obtener movimientos
    picking_ids = [r['id'] for r in todas_recepciones]
    movimientos = odoo.search_read(
        'stock.move',
        [('picking_id', 'in', picking_ids), ('state', '=', 'done')],
        ['id', 'product_id', 'quantity_done', 'picking_id'],
        limit=50000
    )
    
    # Obtener productos y templates
    product_ids = list(set([m['product_id'][0] for m in movimientos if m.get('product_id')]))
    productos = odoo.search_read(
        'product.product',
        [('id', 'in', product_ids)],
        ['id', 'name', 'product_tmpl_id'],
        limit=10000
    )
    productos_map = {p['id']: p for p in productos}
    
    template_ids = list(set([p['product_tmpl_id'][0] for p in productos if p.get('product_tmpl_id')]))
    template_campos_leer = ['id']
    for campo in campos_template_usar.values():
        if campo:
            template_campos_leer.append(campo)
    
    templates = odoo.search_read(
        'product.template',
        [('id', 'in', template_ids)],
        template_campos_leer,
        limit=10000
    )
    templates_map = {t['id']: t for t in templates}
    
    # Obtener quality checks
    quality_campos_leer = ['id', 'picking_id', 'create_date']
    for campo in campos_quality_usar.values():
        if campo:
            quality_campos_leer.append(campo)
    
    quality_checks = odoo.search_read(
        'quality.check',
        [('picking_id', 'in', picking_ids)],
        quality_campos_leer,
        limit=50000
    )
    
    # Organizar quality checks por picking
    quality_by_picking = {}
    for qc in quality_checks:
        picking_id = qc.get('picking_id')
        if picking_id:
            picking_id = picking_id[0] if isinstance(picking_id, (list, tuple)) else picking_id
            if picking_id not in quality_by_picking:
                quality_by_picking[picking_id] = []
            quality_by_picking[picking_id].append(qc)
    
    # Construir datos para Excel
    datos_excel = []
    
    for recepcion in todas_recepciones:
        picking_id = recepcion['id']
        albaran = recepcion.get('name', '')
        fecha = recepcion.get('scheduled_date', '')
        if fecha:
            fecha = datetime.strptime(fecha, '%Y-%m-%d %H:%M:%S').strftime('%d/%m/%Y')
        
        proveedor = recepcion.get('partner_id')
        proveedor = proveedor[1] if isinstance(proveedor, (list, tuple)) else str(proveedor) if proveedor else ''
        
        guia_despacho = recepcion.get(campo_guia, '') if campo_guia else ''
        origen = recepcion.get('origen', '')
        
        movs_recepcion = [m for m in movimientos if m.get('picking_id') and m['picking_id'][0] == picking_id]
        qcs_recepcion = quality_by_picking.get(picking_id, [])
        
        # Si NO hay quality checks, saltar esta recepción (es IQF/BLOCK sin control de calidad)
        if not qcs_recepcion:
            continue
            
        # Para cada quality check (pallet)
        for qc in qcs_recepcion:
            n_pallet = _get_field(qc, campos_quality_usar.get('pallet'))
            calificacion = _get_field(qc, campos_quality_usar.get('clasificacion'))
            temperatura = _get_field(qc, campos_quality_usar.get('temperatura'), 0)
            total_defectos_gramos = _get_field(qc, campos_quality_usar.get('total_defectos'), 0)
            tipo_fruta_from_qc = _get_field(qc, campos_quality_usar.get('tipo_fruta_qc'))
            
            # Defectos en gramos
            hongos = _get_field(qc, campos_quality_usar.get('hongos'), 0)
            inmadura = _get_field(qc, campos_quality_usar.get('inmadura'), 0)
            sobremadura = _get_field(qc, campos_quality_usar.get('sobremadura'), 0)
            deshidratado = _get_field(qc, campos_quality_usar.get('deshidratado'), 0)
            crumble = _get_field(qc, campos_quality_usar.get('crumble'), 0)
            dano_mecanico = _get_field(qc, campos_quality_usar.get('dano_mecanico'), 0)
            dano_insecto = _get_field(qc, campos_quality_usar.get('dano_insecto'), 0)
            deformes = _get_field(qc, campos_quality_usar.get('deformes'), 0)
            fruta_verde = _get_field(qc, campos_quality_usar.get('fruta_verde'), 0)
            herida_partida = _get_field(qc, campos_quality_usar.get('herida_partida'), 0)
            materias_extranas = _get_field(qc, campos_quality_usar.get('materias_extranas'), 0)
            
            # Calcular % defectos si tenemos gramos de muestra
            # Típicamente es de 500g o 1000g de muestra
            total_defectos_pct = 0
            if total_defectos_gramos > 0:
                # Asumimos muestra de 1000g para calcular porcentaje
                total_defectos_pct = round((total_defectos_gramos / 1000) * 100, 2)
            
            # Para cada producto
            for mov in movs_recepcion:
                qty = mov.get('quantity_done', 0) or 0
                if qty == 0:
                    continue
                
                prod_id = mov.get('product_id')
                if not prod_id:
                    continue
                prod_id = prod_id[0] if isinstance(prod_id, (list, tuple)) else prod_id
                
                prod_info = productos_map.get(prod_id, {})
                producto_nombre = prod_info.get('name', '')
                
                tmpl_id = prod_info.get('product_tmpl_id')
                tmpl_id = tmpl_id[0] if isinstance(tmpl_id, (list, tuple)) else tmpl_id
                tmpl_info = templates_map.get(tmpl_id, {})
                
                # FILTRO: Excluir productos de categoría BANDEJAS
                categoria = tmpl_info.get('categ_id', '')
                categoria_nombre = categoria[1] if isinstance(categoria, (list, tuple)) and len(categoria) > 1 else ''
                if 'BANDEJA' in categoria_nombre.upper():
                    continue
                
                variedad = _extract_many2one(tmpl_info.get(campos_template_usar.get('variedad'), ''))
                manejo = _extract_many2one(tmpl_info.get(campos_template_usar.get('manejo'), ''))
                
                # Tipo de fruta: priorizar desde quality.check
                tipo_fruta = tipo_fruta_from_qc or ''
                
                datos_excel.append({
                    'Fecha': fecha,
                    'Proveedor': proveedor,
                    'Guía Despacho': guia_despacho,
                    'Origen': origen,
                    'Albarán': albaran,
                    'Producto': producto_nombre,
                    'Variedad': variedad,
                    'Tipo Fruta': tipo_fruta,
                    'Manejo': manejo,
                    'Kg': qty,
                    'N° Pallet': n_pallet,
                    'Calificación': calificacion,
                    'Temperatura °C': temperatura,
                    '% Defectos': total_defectos_pct,
                    'Hongos (g)': hongos,
                    'Inmadura (g)': inmadura,
                    'Sobremadura (g)': sobremadura,
                    'Deshidratado (g)': deshidratado,
                    'Crumble (g)': crumble,
                    'Daño Mecánico (g)': dano_mecanico,
                    'Daño Insecto (g)': dano_insecto,
                    'Deformes (g)': deformes,
                    'Fruta Verde (g)': fruta_verde,
                    'Herida/Partida (g)': herida_partida,
                    'Materias Extrañas (g)': materias_extranas,
                })
    
    # Generar Excel
    df = pd.DataFrame(datos_excel)
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Recepciones Defectos"
    
    # Estilos
    header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    
    # Encabezados
    headers = df.columns.tolist()
    for col_num, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_num)
        cell.value = header
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border
    
    # Datos
    for row_num, row_data in enumerate(df.values, 2):
        for col_num, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_num, column=col_num)
            cell.value = value
            cell.border = thin_border
            
            if col_num > 10:  # Columnas numéricas
                cell.alignment = Alignment(horizontal="right")
            else:
                cell.alignment = Alignment(horizontal="left")
    
    # Ajustar anchos
    for col_num, header in enumerate(headers, 1):
        column_letter = ws.cell(row=1, column=col_num).column_letter
        
        if 'Fecha' in header:
            ws.column_dimensions[column_letter].width = 12
        elif 'Proveedor' in header or 'Producto' in header:
            ws.column_dimensions[column_letter].width = 30
        elif '(g)' in header or '°C' in header or '%' in header:
            ws.column_dimensions[column_letter].width = 12
        else:
            ws.column_dimensions[column_letter].width = 15
    
    ws.freeze_panes = "A2"
    
    # Guardar a bytes
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    return buffer.getvalue()


def _determinar_campo(campos_dict, opciones):
    """Determina qué campo usar de una lista de opciones."""
    for opcion in opciones:
        if opcion in campos_dict:
            return opcion
    return None


def _get_field(data_dict, field_name, default=''):
    """Obtiene un campo del diccionario de forma segura."""
    if not field_name:
        return default
    value = data_dict.get(field_name, default)
    return value if value else default


def _extract_many2one(value):
    """Extrae el valor de un campo many2one."""
    if isinstance(value, (list, tuple)) and len(value) > 1:
        return value[1]
    elif value:
        return str(value)
    return ''


def _generar_excel_vacio():
    """Genera un Excel vacío cuando no hay datos."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Sin Datos"
    ws['A1'] = "No se encontraron recepciones con los filtros especificados"
    
    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
