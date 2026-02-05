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
                key="proforma_proveedor"
            )
        
        with col2:
            fecha_desde = st.date_input(
                "Desde",
                datetime.now() - timedelta(days=30),
                key="proforma_fecha_desde",
                format="DD/MM/YYYY"
            )
        
        with col3:
            fecha_hasta = st.date_input(
                "Hasta",
                datetime.now(),
                key="proforma_fecha_hasta",
                format="DD/MM/YYYY"
            )
        
        col_btn1, col_btn2 = st.columns([1, 3])
        with col_btn1:
            buscar = st.button("🔍 Buscar Facturas", type="primary", key="btn_buscar_proformas")
    
    # =========================================================================
    # SECCIÓN 2: RESULTADOS DE BÚSQUEDA
    # =========================================================================
    if buscar or st.session_state.get("proformas_data"):
        if buscar:
            proveedor_id = proveedor_map.get(proveedor_sel) if proveedor_sel != "Todos" else None
            
            with st.spinner("Buscando facturas en borrador..."):
                facturas = _get_facturas_borrador(
                    username, password,
                    proveedor_id=proveedor_id,
                    fecha_desde=fecha_desde.strftime("%Y-%m-%d"),
                    fecha_hasta=fecha_hasta.strftime("%Y-%m-%d")
                )
                st.session_state.proformas_data = facturas
        
        facturas = st.session_state.get("proformas_data", [])
        
        if not facturas:
            st.info("📭 No se encontraron facturas en borrador en USD para el período seleccionado.")
            return
        
        st.success(f"✅ Se encontraron **{len(facturas)}** facturas en borrador en USD")
        
        # Tabla resumen de facturas
        st.markdown("#### 📋 Facturas Encontradas")
        
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
                key="proforma_factura_sel"
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
                _render_preview_clp(factura)


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


def _render_preview_clp(factura: dict):
    """Renderiza preview de la proforma en CLP."""
    
    st.markdown("#### 📄 Preview: Proforma en CLP")
    
    # Contenedor estilizado
    with st.container():
        st.markdown(f"""
        <div style="border: 2px solid #ddd; border-radius: 10px; padding: 20px; background-color: #fafafa;">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <div>
                    <h4 style="margin: 0;">PROFORMA DE PROVEEDOR</h4>
                    <p style="color: #666; margin: 5px 0;">Factura: {factura['nombre']}</p>
                </div>
                <div style="text-align: right;">
                    <p style="margin: 0;"><strong>Fecha:</strong> {factura['fecha_factura'] or 'Sin fecha'}</p>
                    <p style="margin: 0;"><strong>Moneda:</strong> CLP</p>
                </div>
            </div>
            <hr style="border: 1px solid #ddd;">
            <p><strong>Proveedor:</strong> {factura['proveedor_nombre']}</p>
            <p><strong>Referencia:</strong> {factura['ref'] or '-'}</p>
            <p><strong>OCs Origen:</strong> {factura['origin'] or '-'}</p>
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
    
    # Botón de exportar (futuro)
    st.markdown("---")
    col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 2])
    
    with col_exp1:
        # Exportar a Excel
        if st.button("📥 Exportar Excel", key=f"export_excel_{factura['id']}"):
            _exportar_excel(factura)
    
    with col_exp2:
        # Generar PDF (placeholder)
        st.button("📄 Generar PDF", key=f"export_pdf_{factura['id']}", disabled=True)


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
