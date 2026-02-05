"""
Tab: Ajuste de Proformas USD → CLP
Permite buscar facturas en borrador, previsualizar conversión y ajustar moneda.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from .shared import fmt_numero, fmt_dinero, API_URL
import requests


def render(username: str, password: str):
    """
    Renderiza el tab de Ajuste de Proformas.
    """
    
    st.markdown("### 💱 Ajuste de Proformas USD → CLP")
    st.caption("Visualiza y convierte facturas de proveedor de USD a Pesos Chilenos")
    
    # =========================================================================
    # SECCIÓN 1: FILTROS DE BÚSQUEDA
    # =========================================================================
    with st.expander("🔍 Búsqueda de Facturas en Borrador", expanded=True):
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            # Obtener proveedores con borradores
            proveedores = _get_proveedores(username, password)
            proveedor_options = ["Todos"] + [f"{p['nombre']} ({p['rut']})" for p in proveedores]
            proveedor_map = {f"{p['nombre']} ({p['rut']})": p['id'] for p in proveedores}
            
            proveedor_sel = st.selectbox(
                "Proveedor",
                proveedor_options,
                key="ajuste_proforma_proveedor"
            )
        
        with col2:
            fecha_desde = st.date_input(
                "Desde",
                datetime.now() - timedelta(days=30),
                key="ajuste_proforma_fecha_desde",
                format="DD/MM/YYYY"
            )
        
        with col3:
            fecha_hasta = st.date_input(
                "Hasta",
                datetime.now(),
                key="ajuste_proforma_fecha_hasta",
                format="DD/MM/YYYY"
            )
        
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            buscar = st.button("🔍 Buscar Facturas", type="primary", key="btn_buscar_ajuste_proformas")
    
    # =========================================================================
    # SECCIÓN 2: RESULTADOS DE BÚSQUEDA
    # =========================================================================
    if buscar or st.session_state.get("ajuste_proformas_data"):
        if buscar:
            proveedor_id = proveedor_map.get(proveedor_sel) if proveedor_sel != "Todos" else None
            
            with st.spinner("Buscando facturas en borrador..."):
                facturas = _get_facturas_borrador(
                    username, password,
                    proveedor_id=proveedor_id,
                    fecha_desde=fecha_desde.strftime("%Y-%m-%d"),
                    fecha_hasta=fecha_hasta.strftime("%Y-%m-%d")
                )
                st.session_state.ajuste_proformas_data = facturas
        
        facturas = st.session_state.get("ajuste_proformas_data", [])
        
        if not facturas:
            st.info("📭 No se encontraron facturas en borrador en USD para el período seleccionado.")
            return
        
        st.success(f"✅ Se encontraron **{len(facturas)}** facturas en borrador en USD")
        
        # =========================================================================
        # SECCIÓN 2.1: SELECCIÓN MÚLTIPLE PARA ENVÍO MASIVO
        # =========================================================================
        st.markdown("#### 📋 Seleccionar Proformas para Envío")
        
        # Crear opciones para multiselect agrupadas por proveedor
        opciones_envio = []
        for f in facturas:
            email_proveedor = f.get("proveedor_email", "Sin email")
            opciones_envio.append(f"{f['nombre']} | {f['proveedor_nombre'][:30]} | {email_proveedor}")
        
        facturas_seleccionadas = st.multiselect(
            "Seleccionar facturas para envío masivo",
            opciones_envio,
            key="proformas_seleccionadas",
            help="Selecciona una o más proformas para enviar por correo a los proveedores"
        )
        
        # Mostrar resumen de selección
        if facturas_seleccionadas:
            st.info(f"📧 **{len(facturas_seleccionadas)}** proformas seleccionadas para envío")
            
            col_envio1, col_envio2 = st.columns([1, 2])
            with col_envio1:
                if st.button("📤 ENVIAR PROFORMAS POR CORREO", type="primary", key="btn_enviar_masivo"):
                    _enviar_proformas_masivo(facturas, facturas_seleccionadas, username, password)
            
            with col_envio2:
                st.caption("Se enviará un correo a cada proveedor con su proforma en PDF adjunta")
        
        st.markdown("---")
        
        # Tabla resumen de facturas
        st.markdown("#### 📊 Detalle de Facturas")
        
        df_facturas = pd.DataFrame([
            {
                "ID": f["id"],
                "Factura": f["nombre"],
                "Ref": f["ref"] or "-",
                "Proveedor": f["proveedor_nombre"],
                "Fecha": f["fecha_factura"] or f["fecha_creacion"][:10] if f["fecha_creacion"] else "-",
                "Líneas": f["num_lineas"],
                "Total USD": f["total_usd"],
                "Total CLP": f["total_clp"],
                "TC": f["tipo_cambio"]
            }
            for f in facturas
        ])
        
        # Formatear columnas
        df_display = df_facturas.copy()
        df_display["Total USD"] = df_display["Total USD"].apply(lambda x: f"${x:,.2f}")
        df_display["Total CLP"] = df_display["Total CLP"].apply(lambda x: f"${x:,.0f}")
        df_display["TC"] = df_display["TC"].apply(lambda x: f"{x:,.2f}")
        
        # Seleccionar factura
        st.dataframe(
            df_display.drop(columns=["ID"]),
            use_container_width=True,
            hide_index=True
        )
        
        # =========================================================================
        # SECCIÓN 3: SELECCIÓN Y PREVIEW DE FACTURA
        # =========================================================================
        st.markdown("---")
        st.markdown("#### 🔎 Detalle de Factura")
        
        factura_options = [f"{f['nombre']} - {f['proveedor_nombre']}" for f in facturas]
        factura_map = {f"{f['nombre']} - {f['proveedor_nombre']}": f for f in facturas}
        
        col_sel1, col_sel2 = st.columns([3, 1])
        with col_sel1:
            factura_sel = st.selectbox(
                "Seleccionar factura para ver detalle",
                factura_options,
                key="ajuste_proforma_factura_sel"
            )
        
        if factura_sel:
            factura = factura_map.get(factura_sel)
            
            if factura:
                _render_detalle_factura(factura)
                
                # =========================================================================
                # SECCIÓN 4: PREVIEW COMPARATIVO
                # =========================================================================
                st.markdown("---")
                _render_comparativo(factura)
                
                # =========================================================================
                # SECCIÓN 5: PREVIEW DE PROFORMA EN CLP
                # =========================================================================
                st.markdown("---")
                _render_preview_clp(factura, username, password)


def _get_proveedores(username: str, password: str) -> list:
    """Obtiene proveedores con facturas en borrador."""
    try:
        response = requests.get(
            f"{API_URL}/api/v1/proformas/proveedores",
            params={"username": username, "password": password},
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Fallback: llamar directamente al servicio
    try:
        from backend.services.proforma_ajuste_service import get_proveedores_con_borradores
        return get_proveedores_con_borradores(username, password)
    except Exception as e:
        st.error(f"Error obteniendo proveedores: {e}")
        return []


def _get_facturas_borrador(username: str, password: str, **kwargs) -> list:
    """Obtiene facturas en borrador."""
    try:
        params = {"username": username, "password": password, **kwargs}
        response = requests.get(
            f"{API_URL}/api/v1/proformas/borradores",
            params=params,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
    except:
        pass
    
    # Fallback: llamar directamente al servicio
    try:
        from backend.services.proforma_ajuste_service import get_facturas_borrador
        return get_facturas_borrador(username, password, **kwargs)
    except Exception as e:
        st.error(f"Error obteniendo facturas: {e}")
        return []


def _render_detalle_factura(factura: dict):
    """Renderiza el detalle de una factura seleccionada."""
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📄 Factura", factura["nombre"])
        st.caption(f"Ref: {factura['ref'] or 'Sin referencia'}")
    
    with col2:
        st.metric("🏢 Proveedor", factura["proveedor_nombre"][:30])
        st.caption(f"Fecha: {factura['fecha_factura'] or 'Sin fecha'}")
    
    with col3:
        st.metric("💱 Tipo de Cambio", f"{factura['tipo_cambio']:,.2f}")
        st.caption(f"Moneda: {factura['moneda']}")
    
    # Tabla de líneas
    if factura["lineas"]:
        st.markdown("##### 📦 Líneas de Factura")
        
        df_lineas = pd.DataFrame([
            {
                "Descripción": l["nombre"][:60] if l["nombre"] else "-",
                "Cantidad": l["cantidad"],
                "P.Unit USD": l["precio_usd"],
                "Subtotal USD": l["subtotal_usd"],
                "Subtotal CLP": l["subtotal_clp"],
                "TC": l["tc_implicito"]
            }
            for l in factura["lineas"]
        ])
        
        # Formatear
        df_lineas["P.Unit USD"] = df_lineas["P.Unit USD"].apply(lambda x: f"${x:,.2f}")
        df_lineas["Subtotal USD"] = df_lineas["Subtotal USD"].apply(lambda x: f"${x:,.2f}")
        df_lineas["Subtotal CLP"] = df_lineas["Subtotal CLP"].apply(lambda x: f"${x:,.0f}")
        df_lineas["TC"] = df_lineas["TC"].apply(lambda x: f"{x:,.2f}")
        
        st.dataframe(df_lineas, use_container_width=True, hide_index=True)


def _render_comparativo(factura: dict):
    """Renderiza comparativo ANTES/DESPUÉS."""
    
    st.markdown("#### 📊 Comparativo USD → CLP")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("##### 💵 ANTES (USD)")
        st.markdown(f"""
        | Concepto | Monto |
        |----------|-------|
        | Base imponible | **${factura['base_usd']:,.2f}** |
        | IVA 19% | ${factura['iva_usd']:,.2f} |
        | **TOTAL** | **${factura['total_usd']:,.2f}** |
        """)
    
    with col2:
        st.markdown("##### 💰 DESPUÉS (CLP)")
        st.markdown(f"""
        | Concepto | Monto |
        |----------|-------|
        | Base imponible | **${factura['base_clp']:,.0f}** |
        | IVA 19% | ${factura['iva_clp']:,.0f} |
        | **TOTAL** | **${factura['total_clp']:,.0f}** |
        """)
    
    with col3:
        st.markdown("##### ✅ Validación Odoo")
        diff = abs(factura['base_clp'] - factura['base_clp_signed'])
        if diff < 100:
            st.success(f"✅ Cuadra con Odoo")
            st.caption(f"Diferencia: ${diff:,.0f}")
        else:
            st.warning(f"⚠️ Diferencia: ${diff:,.0f}")
        
        st.metric("TC Aplicado", f"{factura['tipo_cambio']:,.4f}")


def _render_preview_clp(factura: dict, username: str, password: str):
    """Renderiza preview de la proforma en CLP."""
    
    st.markdown("#### 📄 Preview: Proforma en CLP")
    
    # Contenedor estilizado con mejor diseño
    st.markdown(f"""
    <div style="border: 2px solid #4CAF50; border-radius: 10px; padding: 20px; background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
            <div>
                <h3 style="margin: 0; color: #2E7D32;">📄 PROFORMA DE PROVEEDOR</h3>
                <p style="color: #666; margin: 5px 0; font-size: 1.1em;"><strong>{factura['nombre']}</strong></p>
            </div>
            <div style="text-align: right; background: #fff; padding: 10px 15px; border-radius: 8px;">
                <p style="margin: 0; font-size: 0.9em;">📅 <strong>Fecha:</strong> {factura['fecha_factura'] or 'Sin fecha'}</p>
                <p style="margin: 5px 0 0 0; font-size: 1.2em; color: #4CAF50;">💰 <strong>CLP</strong></p>
            </div>
        </div>
        <hr style="border: 1px solid #ccc; margin: 15px 0;">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
            <p style="margin: 5px 0;">🏢 <strong>Proveedor:</strong> {factura['proveedor_nombre']}</p>
            <p style="margin: 5px 0;">🔖 <strong>Referencia:</strong> {factura['ref'] or '-'}</p>
            <p style="margin: 5px 0;">📋 <strong>OCs Origen:</strong> {factura['origin'] or '-'}</p>
            <p style="margin: 5px 0;">💱 <strong>TC Aplicado:</strong> {factura['tipo_cambio']:,.2f}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabla de líneas en CLP
    if factura["lineas"]:
        df_preview = pd.DataFrame([
            {
                "Descripción": l["nombre"][:50] if l["nombre"] else "-",
                "Cantidad": f"{l['cantidad']:,.2f}",
                "Subtotal CLP": f"${l['subtotal_clp']:,.0f}"
            }
            for l in factura["lineas"]
        ])
        
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    # Totales
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        st.markdown("**Base imponible:**")
        st.markdown("**IVA 19%:**")
        st.markdown("**TOTAL:**")
    with col3:
        st.markdown(f"**${factura['base_clp']:,.0f}**")
        st.markdown(f"${factura['iva_clp']:,.0f}")
        st.markdown(f"**${factura['total_clp']:,.0f}**")
    
    # Botones de acción
    st.markdown("---")
    st.markdown("#### 🚀 Acciones")
    
    col_action1, col_action2, col_action3 = st.columns([1.5, 1, 1.5])
    
    with col_action1:
        # Botón para enviar esta proforma individual
        if st.button("📤 Enviar esta Proforma", key=f"enviar_individual_{factura['id']}"):
            _enviar_proforma_individual(factura, username, password)
    
    with col_action2:
        # Exportar a Excel
        if st.button("📥 Exportar Excel", key=f"export_excel_{factura['id']}"):
            _exportar_excel(factura)
    
    with col_action3:
        st.link_button(
            "🔗 Ver en Odoo",
            f"https://riofuturo.server98c6e.oerpondemand.net/odoo/account.move/{factura['id']}",
            use_container_width=True
        )
    
    # Botón deshabilitado temporalmente
    with st.expander("⚙️ Opciones Avanzadas (Deshabilitado)", expanded=False):
        st.warning("⚠️ La función de cambiar moneda en Odoo está temporalmente deshabilitada")
        st.button(
            "✅ APLICAR CAMBIO A CLP EN ODOO", 
            key=f"aplicar_cambio_{factura['id']}", 
            disabled=True,
            help="Esta función está temporalmente deshabilitada"
        )


def _aplicar_cambio_odoo(factura: dict, username: str, password: str):
    """Aplica el cambio de moneda USD → CLP en Odoo."""
    
    with st.spinner("🔄 Aplicando cambio en Odoo..."):
        try:
            # Intentar vía API
            response = requests.post(
                f"{API_URL}/api/v1/proformas/cambiar_moneda/{factura['id']}",
                params={
                    "username": username,
                    "password": password,
                    "moneda_destino": "CLP"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
            else:
                # Fallback: llamar directamente al servicio
                from backend.services.proforma_ajuste_service import aplicar_conversion_clp
                result = aplicar_conversion_clp(username, password, factura['id'], factura['lineas'])
            
            if result.get("success"):
                st.success(f"""
                ✅ **¡Cambio aplicado exitosamente!**
                
                - Factura: **{factura['nombre']}**
                - Líneas actualizadas: **{result.get('lineas_actualizadas', 0)}**
                - Nueva moneda: **CLP**
                
                👉 Ahora puedes ir a Odoo para generar el PDF.
                """)
                st.balloons()
                
                # Limpiar cache para que se refresque la lista
                if "ajuste_proformas_data" in st.session_state:
                    del st.session_state.ajuste_proformas_data
            else:
                st.error(f"❌ Error al aplicar cambio: {result.get('error', 'Error desconocido')}")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


def _exportar_excel(factura: dict):
    """Exporta la proforma a Excel."""
    import io
    
    # Crear DataFrame
    df_lineas = pd.DataFrame([
        {
            "Descripción": l["nombre"],
            "Cantidad": l["cantidad"],
            "Precio USD": l["precio_usd"],
            "Subtotal USD": l["subtotal_usd"],
            "Subtotal CLP": l["subtotal_clp"],
            "Tipo Cambio": l["tc_implicito"]
        }
        for l in factura["lineas"]
    ])
    
    # Agregar fila de totales
    df_totales = pd.DataFrame([
        {
            "Descripción": "BASE IMPONIBLE",
            "Cantidad": "",
            "Precio USD": "",
            "Subtotal USD": factura["base_usd"],
            "Subtotal CLP": factura["base_clp"],
            "Tipo Cambio": factura["tipo_cambio"]
        },
        {
            "Descripción": "IVA 19%",
            "Cantidad": "",
            "Precio USD": "",
            "Subtotal USD": factura["iva_usd"],
            "Subtotal CLP": factura["iva_clp"],
            "Tipo Cambio": ""
        },
        {
            "Descripción": "TOTAL",
            "Cantidad": "",
            "Precio USD": "",
            "Subtotal USD": factura["total_usd"],
            "Subtotal CLP": factura["total_clp"],
            "Tipo Cambio": ""
        }
    ])
    
    df_export = pd.concat([df_lineas, df_totales], ignore_index=True)
    
    # Crear buffer Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_export.to_excel(writer, sheet_name='Proforma CLP', index=False)
    
    buffer.seek(0)
    
    st.download_button(
        label="⬇️ Descargar Excel",
        data=buffer,
        file_name=f"proforma_{factura['nombre']}_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_{factura['id']}"
    )


def _generar_pdf_proforma(factura: dict) -> bytes:
    """Genera un PDF de la proforma usando reportlab."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    import io
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    normal_style = styles['Normal']
    
    elements = []
    
    # Título
    elements.append(Paragraph("PROFORMA DE PROVEEDOR", title_style))
    elements.append(Spacer(1, 12))
    
    # Información del documento
    info_data = [
        ["Factura:", factura['nombre'], "Fecha:", factura.get('fecha_factura', '-')],
        ["Proveedor:", factura['proveedor_nombre'][:40], "Moneda:", "CLP"],
        ["Referencia:", factura.get('ref', '-') or '-', "TC:", f"{factura['tipo_cambio']:,.2f}"],
    ]
    
    info_table = Table(info_data, colWidths=[1.2*inch, 2.5*inch, 1*inch, 1.5*inch])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tabla de líneas
    table_data = [["Descripción", "Cantidad", "Subtotal CLP"]]
    
    for linea in factura['lineas']:
        desc = linea['nombre'][:50] if linea['nombre'] else "-"
        cant = f"{linea['cantidad']:,.2f}"
        subtotal = f"${linea['subtotal_clp']:,.0f}"
        table_data.append([desc, cant, subtotal])
    
    # Totales
    table_data.append(["", "", ""])
    table_data.append(["", "Base Imponible:", f"${factura['base_clp']:,.0f}"])
    table_data.append(["", "IVA 19%:", f"${factura['iva_clp']:,.0f}"])
    table_data.append(["", "TOTAL:", f"${factura['total_clp']:,.0f}"])
    
    main_table = Table(table_data, colWidths=[4*inch, 1.3*inch, 1.5*inch])
    main_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, len(factura['lineas'])), 0.5, colors.grey),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        # Estilo para totales
        ('FONTNAME', (1, -3), (1, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, -1), (2, -1), 'Helvetica-Bold'),
        ('LINEABOVE', (1, -3), (-1, -3), 1, colors.black),
    ]))
    elements.append(main_table)
    
    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()


def _enviar_proforma_individual(factura: dict, username: str, password: str):
    """Envía una proforma individual por correo."""
    
    email_destino = factura.get("proveedor_email", "")
    
    if not email_destino:
        st.error(f"❌ El proveedor {factura['proveedor_nombre']} no tiene email configurado en Odoo")
        return
    
    with st.spinner(f"📤 Enviando proforma a {email_destino}..."):
        try:
            # Generar PDF
            pdf_bytes = _generar_pdf_proforma(factura)
            
            # Enviar correo via servicio
            from backend.services.proforma_ajuste_service import enviar_proforma_email
            
            resultado = enviar_proforma_email(
                username=username,
                password=password,
                factura_id=factura['id'],
                email_destino=email_destino,
                pdf_bytes=pdf_bytes,
                nombre_factura=factura['nombre'],
                proveedor_nombre=factura['proveedor_nombre']
            )
            
            if resultado.get("success"):
                st.success(f"✅ Proforma enviada exitosamente a **{email_destino}**")
            else:
                st.error(f"❌ Error al enviar: {resultado.get('error', 'Error desconocido')}")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


def _enviar_proformas_masivo(facturas: list, seleccionadas: list, username: str, password: str):
    """Envía múltiples proformas por correo."""
    
    # Mapear seleccionadas a facturas
    facturas_a_enviar = []
    for sel in seleccionadas:
        nombre_factura = sel.split(" | ")[0]
        for f in facturas:
            if f['nombre'] == nombre_factura:
                facturas_a_enviar.append(f)
                break
    
    if not facturas_a_enviar:
        st.error("No se encontraron facturas para enviar")
        return
    
    # Verificar emails
    sin_email = [f for f in facturas_a_enviar if not f.get("proveedor_email")]
    con_email = [f for f in facturas_a_enviar if f.get("proveedor_email")]
    
    if sin_email:
        st.warning(f"⚠️ {len(sin_email)} proveedores sin email configurado:")
        for f in sin_email:
            st.caption(f"  - {f['nombre']} - {f['proveedor_nombre']}")
    
    if not con_email:
        st.error("❌ Ninguna factura tiene proveedor con email configurado")
        return
    
    # Progreso
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    enviados = 0
    errores = []
    
    for i, factura in enumerate(con_email):
        status_text.text(f"📤 Enviando {i+1}/{len(con_email)}: {factura['nombre']}...")
        progress_bar.progress((i + 1) / len(con_email))
        
        try:
            # Generar PDF
            pdf_bytes = _generar_pdf_proforma(factura)
            
            # Enviar
            from backend.services.proforma_ajuste_service import enviar_proforma_email
            
            resultado = enviar_proforma_email(
                username=username,
                password=password,
                factura_id=factura['id'],
                email_destino=factura['proveedor_email'],
                pdf_bytes=pdf_bytes,
                nombre_factura=factura['nombre'],
                proveedor_nombre=factura['proveedor_nombre']
            )
            
            if resultado.get("success"):
                enviados += 1
            else:
                errores.append(f"{factura['nombre']}: {resultado.get('error', 'Error')}")
                
        except Exception as e:
            errores.append(f"{factura['nombre']}: {str(e)}")
    
    progress_bar.empty()
    status_text.empty()
    
    # Resumen
    if enviados > 0:
        st.success(f"✅ **{enviados}** proformas enviadas exitosamente")
        st.balloons()
    
    if errores:
        st.error(f"❌ **{len(errores)}** proformas con error:")
        for err in errores:
            st.caption(f"  - {err}")
