"""
Tab de Proforma Consolidada de Fletes
Genera documento consolidado por transportista con detalle de OCs, kms, kilos, costos
"""

import streamlit as st
import pandas as pd
import xmlrpc.client
from datetime import datetime, timedelta
import io
from typing import Dict, List, Optional
import requests
import json


URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'
API_LOGISTICA_RUTAS = 'https://riofuturoprocesos.com/api/logistica/rutas'
API_LOGISTICA_COSTES = 'https://riofuturoprocesos.com/api/logistica/db/coste-rutas'


def get_odoo_connection(username, password):
    """Conexión a Odoo"""
    try:
        common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
        uid = common.authenticate(DB, username, password, {})
        models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
        return models, uid
    except Exception as e:
        st.error(f"Error de conexión a Odoo: {e}")
        return None, None


@st.cache_data(ttl=300)
def obtener_rutas_logistica():
    """Obtener rutas del sistema de logística"""
    try:
        response = requests.get(API_LOGISTICA_RUTAS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            # Manejar si es lista o dict con 'data'
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'data' in data:
                return data['data']
            return []
        return []
    except Exception as e:
        st.warning(f"No se pudo conectar al sistema de logística: {e}")
        return []


def buscar_ruta_en_logistica(oc_name: str, rutas_logistica: List[Dict]) -> Optional[Dict]:
    """Buscar ruta en sistema de logística por nombre de OC"""
    for ruta in rutas_logistica:
        if ruta.get('purchase_order_name') == oc_name:
            return ruta
    return None


@st.cache_data(ttl=60)
def obtener_ocs_transportes(_models, _uid, username, password, fecha_desde, fecha_hasta):
    """Obtener OCs de TRANSPORTES en el rango de fechas"""
    try:
        # Construir dominio de búsqueda
        domain = [
            ('x_studio_categora_de_producto', '=', 'SERVICIOS'),
            ('x_studio_selection_field_yUNPd', 'ilike', 'TRANSPORTES'),
            ('state', 'in', ['draft', 'sent', 'to approve', 'purchase', 'done']),  # Todos los estados
            ('date_order', '>=', fecha_desde),
            ('date_order', '<=', fecha_hasta)
        ]
        
        ocs = _models.execute_kw(
            DB, _uid, password,
            'purchase.order', 'search_read',
            [domain],
            {'fields': ['id', 'name', 'partner_id', 'date_order', 'amount_untaxed', 'state'], 
             'order': 'date_order desc'}
        )
        
        # Obtener líneas y costo calculado para cada OC
        for oc in ocs:
            lineas = _models.execute_kw(
                DB, _uid, password,
                'purchase.order.line', 'search_read',
                [[('order_id', '=', oc['id'])]],
                {'fields': ['product_id', 'name', 'product_qty', 'price_subtotal']}
            )
            
            oc['costo_lineas'] = sum(linea.get('price_subtotal', 0) for linea in lineas)
            oc['num_viajes'] = sum(linea.get('product_qty', 0) for linea in lineas)
        
        return ocs
    except Exception as e:
        st.error(f"Error obteniendo OCs: {e}")
        return []


def generar_pdf_proforma(datos_consolidados: Dict, fecha_desde: str, fecha_hasta: str) -> bytes:
    """Genera archivo PDF con la proforma consolidada por transportista"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    
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
    
    for idx, (transportista, data) in enumerate(datos_consolidados.items()):
        # Si no es el primero, agregar salto de página
        if idx > 0:
            story.append(PageBreak())
        
        # Header principal
        story.append(Paragraph("PROFORMA CONSOLIDADA DE FLETES", title_style))
        story.append(Paragraph(f"Período: {fecha_desde} al {fecha_hasta}", subtitle_style))
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
                oc_data['ruta'][:25] if oc_data['ruta'] else 'Sin ruta',  # Truncar si es muy largo
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


def generar_excel_proforma(datos_consolidados: Dict, fecha_desde: str, fecha_hasta: str) -> bytes:
    """Genera archivo Excel con la proforma consolidada por transportista"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
    
    wb = Workbook()
    
    for transportista, data in datos_consolidados.items():
        # Crear hoja por transportista
        ws = wb.create_sheet(title=transportista[:30])  # Max 31 chars
        
        # Header
        ws['A1'] = 'PROFORMA CONSOLIDADA DE FLETES'
        ws['A1'].font = Font(bold=True, size=14)
        ws.merge_cells('A1:H1')
        ws['A1'].alignment = Alignment(horizontal='center')
        
        ws['A2'] = f'Transportista: {transportista}'
        ws['A2'].font = Font(bold=True, size=12)
        ws.merge_cells('A2:H2')
        
        ws['A3'] = f'Período: {fecha_desde} - {fecha_hasta}'
        ws.merge_cells('A3:H3')
        
        ws['A4'] = f'Generado: {datetime.now().strftime("%d/%m/%Y %H:%M")}'
        ws.merge_cells('A4:H4')
        
        # Headers de tabla
        headers = ['OC', 'Fecha', 'Ruta', 'Kms', 'Kilos', 'Costo', '$/km', 'Tipo Camión']
        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=6, column=col)
            cell.value = header
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color='D3D3D3', end_color='D3D3D3', fill_type='solid')
            cell.alignment = Alignment(horizontal='center')
        
        # Datos
        row = 7
        for oc_data in data['ocs']:
            ws.cell(row=row, column=1, value=oc_data['oc_name'])
            ws.cell(row=row, column=2, value=oc_data['fecha'])
            ws.cell(row=row, column=3, value=oc_data['ruta'] or 'Sin ruta')
            ws.cell(row=row, column=4, value=oc_data['kms'] or 0)
            ws.cell(row=row, column=5, value=oc_data['kilos'] or 0)
            ws.cell(row=row, column=6, value=oc_data['costo'])
            ws.cell(row=row, column=7, value=oc_data['costo_por_km'] or 0)
            ws.cell(row=row, column=8, value=oc_data['tipo_camion'] or 'N/A')
            row += 1
        
        # Totales
        row += 1
        ws.cell(row=row, column=1, value='TOTALES')
        ws.cell(row=row, column=1).font = Font(bold=True)
        ws.cell(row=row, column=4, value=data['totales']['kms'])
        ws.cell(row=row, column=4).font = Font(bold=True)
        ws.cell(row=row, column=5, value=data['totales']['kilos'])
        ws.cell(row=row, column=5).font = Font(bold=True)
        ws.cell(row=row, column=6, value=data['totales']['costo'])
        ws.cell(row=row, column=6).font = Font(bold=True)
        
        # Promedio $/km
        if data['totales']['kms'] > 0:
            promedio_km = data['totales']['costo'] / data['totales']['kms']
            ws.cell(row=row, column=7, value=promedio_km)
            ws.cell(row=row, column=7).font = Font(bold=True)
        
        # Ajustar anchos
        ws.column_dimensions['A'].width = 12
        ws.column_dimensions['B'].width = 12
        ws.column_dimensions['C'].width = 30
        ws.column_dimensions['D'].width = 10
        ws.column_dimensions['E'].width = 10
        ws.column_dimensions['F'].width = 15
        ws.column_dimensions['G'].width = 12
        ws.column_dimensions['H'].width = 20
    
    # Eliminar hoja por defecto
    if 'Sheet' in wb.sheetnames:
        wb.remove(wb['Sheet'])
    
    # Guardar en bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output.getvalue()


def render(username: str, password: str):
    """Renderiza el tab de Proforma Consolidada"""
    st.markdown("## 📄 Proforma Consolidada de Fletes")
    st.markdown("Genere documentos consolidados por transportista con el detalle de movimientos del período")
    
    models, uid = get_odoo_connection(username, password)
    if not models or not uid:
        return
    
    # Filtros
    col1, col2 = st.columns(2)
    
    with col1:
        fecha_desde = st.date_input(
            "Fecha Desde",
            value=datetime.now().replace(day=1),
            key="proforma_fecha_desde"
        )
    
    with col2:
        fecha_hasta = st.date_input(
            "Fecha Hasta",
            value=datetime.now(),
            key="proforma_fecha_hasta"
        )
    
    # Convertir a string
    fecha_desde_str = fecha_desde.strftime('%Y-%m-%d')
    fecha_hasta_str = fecha_hasta.strftime('%Y-%m-%d')
    
    # Obtener datos
    with st.spinner("Cargando OCs de transportes..."):
        ocs = obtener_ocs_transportes(models, uid, username, password, fecha_desde_str, fecha_hasta_str)
        rutas_logistica = obtener_rutas_logistica()
    
    if not ocs:
        st.info("No hay OCs de TRANSPORTES confirmadas en el período seleccionado")
        return
    
    st.success(f"✅ {len(ocs)} OCs encontradas")
    
    # Obtener lista de transportistas únicos
    transportistas_unicos = sorted(list(set([
        oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
        for oc in ocs
    ])))
    
    # Filtro de transportistas
    st.markdown("### 🚚 Filtrar por Transportista")
    transportistas_seleccionados = st.multiselect(
        "Seleccione los transportistas a incluir (deje vacío para todos)",
        options=transportistas_unicos,
        default=None,
        key="filtro_transportistas"
    )
    
    # Filtrar OCs si hay transportistas seleccionados
    if transportistas_seleccionados:
        ocs = [oc for oc in ocs if (
            oc.get('partner_id') and 
            isinstance(oc['partner_id'], (list, tuple)) and 
            oc['partner_id'][1] in transportistas_seleccionados
        )]
        st.info(f"📋 Mostrando {len(ocs)} OCs de {len(transportistas_seleccionados)} transportista(s) seleccionado(s)")
    
    if not ocs:
        st.warning("No hay OCs para los transportistas seleccionados")
        return
    
    # Enriquecer con datos de logística
    datos_tabla = []
    for oc in ocs:
        transportista = oc['partner_id'][1] if oc.get('partner_id') and isinstance(oc['partner_id'], (list, tuple)) else 'N/A'
        
        ruta_info = buscar_ruta_en_logistica(oc['name'], rutas_logistica)
        
        kms = ruta_info.get('total_distance_km', 0) if ruta_info else 0
        kilos = ruta_info.get('total_qnt', 0) if ruta_info else 0  # Campo correcto de la API
        costo = oc['costo_lineas']
        costo_por_km = (costo / kms) if kms > 0 else 0
        
        # Obtener nombre de ruta
        ruta_nombre = 'Sin ruta'
        tipo_camion = 'N/A'
        if ruta_info:
            routes_field = ruta_info.get('routes', False)
            if routes_field and isinstance(routes_field, str) and routes_field.startswith('['):
                try:
                    routes_data = json.loads(routes_field)
                    if isinstance(routes_data, list) and len(routes_data) > 0:
                        route_info = routes_data[0]
                        ruta_nombre = route_info.get('route_name', 'Sin nombre')
                        cost_type = route_info.get('cost_type', '')
                        if cost_type == 'truck_8':
                            tipo_camion = '🚛 Camión 8 Ton'
                        elif cost_type == 'truck_12_14':
                            tipo_camion = '🚚 Camión 12-14 Ton'
                        elif cost_type == 'short_rampla':
                            tipo_camion = '🚐 Rampla Corta'
                        elif cost_type == 'rampla':
                            tipo_camion = '🚛 Rampla'
                except:
                    pass
        
        datos_tabla.append({
            'Sel': False,
            'OC': oc['name'],
            'Fecha': oc['date_order'][:10] if oc.get('date_order') else 'N/A',
            'Transportista': transportista,
            'Ruta': ruta_nombre,
            'Kms': kms,
            'Kilos': kilos,
            'Costo': costo,
            '$/km': costo_por_km,
            'Tipo Camión': tipo_camion,
            '_oc_id': oc['id']
        })
    
    df = pd.DataFrame(datos_tabla)
    
    # Tabla editable
    st.markdown("### 📋 Seleccione las OCs a incluir en la proforma")
    
    edited_df = st.data_editor(
        df,
        column_config={
            'Sel': st.column_config.CheckboxColumn('Sel', default=False),
            'OC': st.column_config.TextColumn('OC', width='small'),
            'Fecha': st.column_config.TextColumn('Fecha', width='small'),
            'Transportista': st.column_config.TextColumn('Transportista', width='medium'),
            'Ruta': st.column_config.TextColumn('Ruta', width='medium'),
            'Kms': st.column_config.NumberColumn('Kms', format='%.0f'),
            'Kilos': st.column_config.NumberColumn('Kilos', format='%.2f'),
            'Costo': st.column_config.NumberColumn('Costo', format='$%.0f'),
            '$/km': st.column_config.NumberColumn('$/km', format='$%.0f'),
            'Tipo Camión': st.column_config.TextColumn('Tipo Camión', width='medium'),
            '_oc_id': None  # Ocultar
        },
        disabled=['OC', 'Fecha', 'Transportista', 'Ruta', 'Kms', 'Kilos', 'Costo', '$/km', 'Tipo Camión'],
        hide_index=True,
        key='editor_proforma',
        use_container_width=True
    )
    
    # Resumen de seleccionados
    seleccionados = edited_df[edited_df['Sel'] == True]
    n_sel = len(seleccionados)
    
    if n_sel > 0:
        st.markdown(f"### ✅ {n_sel} OCs seleccionadas")
        
        # Agrupar por transportista
        transportistas = seleccionados.groupby('Transportista').agg({
            'Kms': 'sum',
            'Kilos': 'sum',
            'Costo': 'sum',
            'OC': 'count'
        }).reset_index()
        transportistas.rename(columns={'OC': 'Cant OCs'}, inplace=True)
        
        st.dataframe(
            transportistas,
            column_config={
                'Transportista': st.column_config.TextColumn('Transportista'),
                'Cant OCs': st.column_config.NumberColumn('OCs', format='%d'),
                'Kms': st.column_config.NumberColumn('Kms Totales', format='%.0f'),
                'Kilos': st.column_config.NumberColumn('Kilos Totales', format='%.2f'),
                'Costo': st.column_config.NumberColumn('Costo Total', format='$%.0f')
            },
            hide_index=True,
            use_container_width=True
        )
        
        # Botón para generar proforma
        col_pdf, col_excel = st.columns(2)
        
        with col_pdf:
            if st.button("📄 Generar Proforma PDF", type="primary", use_container_width=True):
                with st.spinner("Generando PDF..."):
                    # Agrupar datos por transportista
                    datos_consolidados = {}
                    
                    for _, row in seleccionados.iterrows():
                        transp = row['Transportista']
                        
                        if transp not in datos_consolidados:
                            datos_consolidados[transp] = {
                                'ocs': [],
                                'totales': {'kms': 0, 'kilos': 0, 'costo': 0}
                            }
                        
                        datos_consolidados[transp]['ocs'].append({
                            'oc_name': row['OC'],
                            'fecha': row['Fecha'],
                            'ruta': row['Ruta'],
                            'kms': row['Kms'],
                            'kilos': row['Kilos'],
                            'costo': row['Costo'],
                            'costo_por_km': row['$/km'],
                            'tipo_camion': row['Tipo Camión']
                        })
                        
                        datos_consolidados[transp]['totales']['kms'] += row['Kms']
                        datos_consolidados[transp]['totales']['kilos'] += row['Kilos']
                        datos_consolidados[transp]['totales']['costo'] += row['Costo']
                    
                    # Generar PDF
                    pdf_bytes = generar_pdf_proforma(datos_consolidados, fecha_desde_str, fecha_hasta_str)
                    
                    # Botón de descarga
                    st.download_button(
                        label="⬇️ Descargar Proforma PDF",
                        data=pdf_bytes,
                        file_name=f"proforma_fletes_{fecha_desde_str}_{fecha_hasta_str}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True
                    )
                    
                    st.success("✅ PDF generado exitosamente")
        
        with col_excel:
            if st.button("📊 Generar Proforma Excel", use_container_width=True):
                with st.spinner("Generando Excel..."):
                    # Agrupar datos por transportista
                    datos_consolidados = {}
                    
                    for _, row in seleccionados.iterrows():
                        transp = row['Transportista']
                        
                        if transp not in datos_consolidados:
                            datos_consolidados[transp] = {
                                'ocs': [],
                                'totales': {'kms': 0, 'kilos': 0, 'costo': 0}
                            }
                        
                        datos_consolidados[transp]['ocs'].append({
                            'oc_name': row['OC'],
                            'fecha': row['Fecha'],
                            'ruta': row['Ruta'],
                            'kms': row['Kms'],
                            'kilos': row['Kilos'],
                            'costo': row['Costo'],
                            'costo_por_km': row['$/km'],
                            'tipo_camion': row['Tipo Camión']
                        })
                        
                        datos_consolidados[transp]['totales']['kms'] += row['Kms']
                        datos_consolidados[transp]['totales']['kilos'] += row['Kilos']
                        datos_consolidados[transp]['totales']['costo'] += row['Costo']
                    
                    # Generar Excel
                    excel_bytes = generar_excel_proforma(datos_consolidados, fecha_desde_str, fecha_hasta_str)
                    
                    # Botón de descarga
                    st.download_button(
                        label="⬇️ Descargar Proforma Excel",
                        data=excel_bytes,
                        file_name=f"proforma_fletes_{fecha_desde_str}_{fecha_hasta_str}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.success("✅ Excel generado exitosamente")
    else:
        st.info("👆 Seleccione las OCs que desea incluir en la proforma")
