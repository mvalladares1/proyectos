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
            "Seleccionar facturas para envío masivo (pueden ser de diferentes proveedores)",
            opciones_envio,
            key="proformas_seleccionadas",
            help="Selecciona una o más proformas para analizar y enviar por correo a los proveedores"
        )
        
        # =========================================================================
        # ANÁLISIS DE PROFORMAS SELECCIONADAS
        # =========================================================================
        if facturas_seleccionadas:
            st.markdown("---")
            st.markdown("#### 📊 Análisis de Proformas Seleccionadas")
            
            # Mapear seleccionadas a facturas
            facturas_sel = []
            for sel in facturas_seleccionadas:
                nombre_factura = sel.split(" | ")[0]
                for f in facturas:
                    if f['nombre'] == nombre_factura:
                        facturas_sel.append(f)
                        break
            
            # Métricas generales
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            
            total_usd = sum(f['total_usd'] for f in facturas_sel)
            total_clp = sum(f['total_clp'] for f in facturas_sel)
            num_proveedores = len(set(f['proveedor_id'] for f in facturas_sel))
            con_email = len([f for f in facturas_sel if f.get('proveedor_email')])
            
            with col_m1:
                st.metric("📄 Proformas", len(facturas_sel))
            with col_m2:
                st.metric("🏢 Proveedores", num_proveedores)
            with col_m3:
                st.metric("💵 Total USD", f"${total_usd:,.2f}")
            with col_m4:
                st.metric("💰 Total CLP", f"${total_clp:,.0f}")
            
            # Agrupar por proveedor
            st.markdown("##### 📦 Detalle por Proveedor")
            
            proveedores_agrupados = {}
            for f in facturas_sel:
                prov_id = f['proveedor_id']
                if prov_id not in proveedores_agrupados:
                    proveedores_agrupados[prov_id] = {
                        'nombre': f['proveedor_nombre'],
                        'email': f.get('proveedor_email', 'Sin email'),
                        'facturas': [],
                        'total_usd': 0,
                        'total_clp': 0
                    }
                proveedores_agrupados[prov_id]['facturas'].append(f['nombre'])
                proveedores_agrupados[prov_id]['total_usd'] += f['total_usd']
                proveedores_agrupados[prov_id]['total_clp'] += f['total_clp']
            
            # Tabla de análisis por proveedor
            df_analisis = pd.DataFrame([
                {
                    'Proveedor': p['nombre'][:40],
                    'Email': p['email'] if p['email'] else '❌ Sin email',
                    'N° Facturas': len(p['facturas']),
                    'Total USD': p['total_usd'],
                    'Total CLP': p['total_clp'],
                    'Facturas': ', '.join(p['facturas'][:3]) + ('...' if len(p['facturas']) > 3 else '')
                }
                for p in proveedores_agrupados.values()
            ])
            
            # Formatear
            df_analisis['Total USD'] = df_analisis['Total USD'].apply(lambda x: f"${x:,.2f}")
            df_analisis['Total CLP'] = df_analisis['Total CLP'].apply(lambda x: f"${x:,.0f}")
            
            st.dataframe(df_analisis, use_container_width=True, hide_index=True)
            
            # Advertencias
            sin_email = [f for f in facturas_sel if not f.get("proveedor_email")]
            if sin_email:
                st.warning(f"⚠️ **{len(sin_email)} proformas** de proveedores sin email configurado no se enviarán:")
                for f in sin_email[:5]:
                    st.caption(f"  - {f['nombre']} - {f['proveedor_nombre']}")
                if len(sin_email) > 5:
                    st.caption(f"  ... y {len(sin_email) - 5} más")
            
            # Botón de envío
            st.markdown("---")
            col_envio1, col_envio2 = st.columns([1, 2])
            
            with col_envio1:
                if st.button("📤 ENVIAR PROFORMAS SELECCIONADAS", type="primary", key="btn_enviar_masivo"):
                    _enviar_proformas_masivo(facturas, facturas_seleccionadas, username, password)
            
            with col_envio2:
                if con_email > 0:
                    st.info(f"✉️ Se enviarán **{con_email}** proformas a **{num_proveedores}** proveedores")
                else:
                    st.error("❌ Ninguna proforma tiene proveedor con email configurado")
        
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


def _enviar_proformas_masivo(facturas_todas: list, facturas_seleccionadas: list, username: str, password: str):
    """Envía múltiples proformas de forma masiva."""
    
    # Mapear seleccionadas a facturas completas
    facturas_enviar = []
    for sel in facturas_seleccionadas:
        nombre_factura = sel.split(" | ")[0]
        for f in facturas_todas:
            if f['nombre'] == nombre_factura and f.get('proveedor_email'):
                facturas_enviar.append(f)
                break
    
    if not facturas_enviar:
        st.error("❌ No hay proformas válidas para enviar (todos los proveedores sin email)")
        return
    
    st.markdown("---")
    st.markdown("### 📤 Enviando Proformas...")
    
    progress_bar = st.progress(0)
    status_container = st.container()
    
    total = len(facturas_enviar)
    enviadas = 0
    errores = []
    
    for idx, factura in enumerate(facturas_enviar):
        progress = (idx + 1) / total
        progress_bar.progress(progress)
        
        with status_container:
            st.info(f"📧 Enviando {idx + 1}/{total}: {factura['nombre']} → {factura['proveedor_email']}")
        
        try:
            # Generar PDF
            pdf_bytes = _generar_pdf_proforma(factura)
            
            # Enviar email
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
                enviadas += 1
                with status_container:
                    st.success(f"✅ {factura['nombre']} enviada correctamente")
            else:
                errores.append(f"{factura['nombre']}: {resultado.get('error', 'Error desconocido')}")
                with status_container:
                    st.error(f"❌ Error enviando {factura['nombre']}")
        
        except Exception as e:
            errores.append(f"{factura['nombre']}: {str(e)}")
            with status_container:
                st.error(f"❌ Error enviando {factura['nombre']}: {str(e)}")
    
    progress_bar.progress(1.0)
    
    # Resumen final
    st.markdown("---")
    st.markdown("### 📊 Resumen de Envío")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("✅ Enviadas", enviadas)
    with col2:
        st.metric("❌ Errores", len(errores))
    with col3:
        st.metric("📊 Total", total)
    
    if errores:
        st.error("**Errores encontrados:**")
        for error in errores:
            st.caption(f"  • {error}")
    else:
        st.success("🎉 ¡Todas las proformas fueron enviadas correctamente!")
        st.balloons()


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
    
    # Tabla de líneas con información completa (igual que el PDF)
    if factura["lineas"]:
        st.markdown("##### 📦 Líneas de Factura")
        
        # Obtener fechas de OCs
        from shared.odoo_client import OdooClient
        client = OdooClient(username=st.session_state.get('username'), password=st.session_state.get('password'))
        
        lineas_completas = []
        for l in factura["lineas"]:
            desc = l["nombre"][:60] if l["nombre"] else "-"
            
            # Extraer fecha de OC
            fecha_oc = "-"
            if ":" in desc:
                oc_nombre = desc.split(":")[0].strip()
                try:
                    ocs = client.search_read(
                        "purchase.order",
                        [("name", "=", oc_nombre)],
                        ["date_order"],
                        limit=1
                    )
                    if ocs and ocs[0].get("date_order"):
                        fecha_oc = ocs[0]["date_order"][:10]  # YYYY-MM-DD
                except:
                    pass
            
            # Calcular precio unitario CLP
            p_unit_clp = l["subtotal_clp"] / l["cantidad"] if l["cantidad"] else 0
            
            lineas_completas.append({
                "Descripción": desc,
                "Fecha OC": fecha_oc,
                "Cant. KG": l["cantidad"],
                "P. Unitario USD": l["precio_usd"],
                "Tipo Cambio": l["tc_implicito"],
                "P. Unitario CLP": p_unit_clp,
                "Subtotal USD": l["subtotal_usd"],
                "Subtotal CLP": l["subtotal_clp"]
            })
        
        df_lineas = pd.DataFrame(lineas_completas)
        
        # Formatear con formato chileno
        df_lineas["Cant. KG"] = df_lineas["Cant. KG"].apply(lambda x: f"{x:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        df_lineas["P. Unitario USD"] = df_lineas["P. Unitario USD"].apply(lambda x: f"${x:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        df_lineas["Tipo Cambio"] = df_lineas["Tipo Cambio"].apply(lambda x: f"{x:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        df_lineas["P. Unitario CLP"] = df_lineas["P. Unitario CLP"].apply(lambda x: f"${x:,.0f}".replace(',', '.'))
        df_lineas["Subtotal USD"] = df_lineas["Subtotal USD"].apply(lambda x: f"${x:,.2f}".replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.'))
        df_lineas["Subtotal CLP"] = df_lineas["Subtotal CLP"].apply(lambda x: f"${x:,.0f}".replace(',', '.'))
        
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
    
    # Contenedor estilizado con mejor contraste
    st.markdown(f"""
    <div style="border: 3px solid #1B4F72; border-radius: 12px; padding: 25px; background: #ffffff; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; padding-bottom: 15px; border-bottom: 2px solid #E8F4F8;">
            <div>
                <h3 style="margin: 0; color: #1B4F72; font-size: 1.5em;">📄 PROFORMA DE PROVEEDOR</h3>
                <p style="color: #333; margin: 8px 0 0 0; font-size: 1.2em;"><strong>{factura['nombre']}</strong></p>
            </div>
            <div style="text-align: right; background: #E8F4F8; padding: 15px 20px; border-radius: 8px; border-left: 4px solid #2E86AB;">
                <p style="margin: 0; font-size: 0.95em; color: #333;">📅 <strong>Fecha:</strong> {factura['fecha_factura'] or 'Sin fecha'}</p>
                <p style="margin: 8px 0 0 0; font-size: 1.3em; color: #1B4F72; font-weight: bold;">💰 CLP</p>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; background: #f8f9fa; padding: 15px; border-radius: 8px;">
            <p style="margin: 8px 0; color: #333; font-size: 0.95em;">🏢 <strong style="color: #1B4F72;">Proveedor:</strong> {factura['proveedor_nombre']}</p>
            <p style="margin: 8px 0; color: #333; font-size: 0.95em;">🔖 <strong style="color: #1B4F72;">Referencia:</strong> {factura['ref'] or '-'}</p>
            <p style="margin: 8px 0; color: #333; font-size: 0.95em;">📋 <strong style="color: #1B4F72;">OCs Origen:</strong> {factura['origin'] or '-'}</p>
            <p style="margin: 8px 0; color: #333; font-size: 0.95em;">💱 <strong style="color: #1B4F72;">TC Aplicado:</strong> {factura['tipo_cambio']:,.2f}</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Tabla de líneas con detalle completo
    if factura["lineas"]:
        st.markdown("##### 📦 Detalle de Líneas")
        
        df_preview = pd.DataFrame([
            {
                "Descripción": l["nombre"][:40] if l["nombre"] else "-",
                "Cant.": l["cantidad"],
                "P.Unit USD": l["precio_usd"],
                "TC": l["tc_implicito"],
                "P.Unit CLP": l["subtotal_clp"] / l["cantidad"] if l["cantidad"] else 0,
                "Subtotal USD": l["subtotal_usd"],
                "Subtotal CLP": l["subtotal_clp"],
            }
            for l in factura["lineas"]
        ])
        
        # Formatear columnas
        df_preview["Cant."] = df_preview["Cant."].apply(lambda x: f"{x:,.2f}")
        df_preview["P.Unit USD"] = df_preview["P.Unit USD"].apply(lambda x: f"${x:,.2f}")
        df_preview["TC"] = df_preview["TC"].apply(lambda x: f"{x:,.2f}")
        df_preview["P.Unit CLP"] = df_preview["P.Unit CLP"].apply(lambda x: f"${x:,.0f}")
        df_preview["Subtotal USD"] = df_preview["Subtotal USD"].apply(lambda x: f"${x:,.2f}")
        df_preview["Subtotal CLP"] = df_preview["Subtotal CLP"].apply(lambda x: f"${x:,.0f}")
        
        st.dataframe(df_preview, use_container_width=True, hide_index=True)
    
    # Totales mejorados
    st.markdown("---")
    col_tot1, col_tot2, col_tot3 = st.columns([2, 1, 1])
    
    with col_tot1:
        st.markdown("")
    
    with col_tot2:
        st.markdown("##### 💵 USD")
        st.markdown(f"Base: **${factura['base_usd']:,.2f}**")
        st.markdown(f"IVA 19%: ${factura['iva_usd']:,.2f}")
        st.markdown(f"**TOTAL: ${factura['total_usd']:,.2f}**")
    
    with col_tot3:
        st.markdown("##### 💰 CLP")
        st.markdown(f"Base: **${factura['base_clp']:,.0f}**")
        st.markdown(f"IVA 19%: ${factura['iva_clp']:,.0f}")
        st.markdown(f"**TOTAL: ${factura['total_clp']:,.0f}**")
    
    # Botones de acción
    st.markdown("---")
    st.markdown("#### 🚀 Acciones")
    
    col_action1, col_action2, col_action3, col_action4 = st.columns(4)
    
    with col_action1:
        # Botón para descargar PDF
        pdf_bytes = _generar_pdf_proforma(factura)
        st.download_button(
            label="📄 Descargar PDF",
            data=pdf_bytes,
            file_name=f"Proforma_{factura['nombre']}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            key=f"download_pdf_{factura['id']}"
        )
    
    with col_action2:
        # Botón para enviar esta proforma individual
        if st.button("📤 Enviar por Email", key=f"enviar_individual_{factura['id']}"):
            _enviar_proforma_individual(factura, username, password)
    
    with col_action3:
        # Exportar a Excel
        if st.button("📥 Exportar Excel", key=f"export_excel_{factura['id']}"):
            _exportar_excel(factura)
    
    with col_action4:
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
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    import io
    import os
    
    # Función para formato chileno (puntos como separador de miles, coma para decimales)
    def fmt_cl(num, decimales=2):
        """Formatea número a formato chileno."""
        if decimales == 0:
            formatted = f"{num:,.0f}"
        else:
            formatted = f"{num:,.{decimales}f}"
        # Intercambiar comas y puntos
        formatted = formatted.replace(',', 'TEMP').replace('.', ',').replace('TEMP', '.')
        return formatted
    
    buffer = io.BytesIO()
    # Usar landscape para tener más espacio horizontal
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                          topMargin=0.5*inch, bottomMargin=0.7*inch,
                          leftMargin=0.6*inch, rightMargin=0.6*inch)
    
    styles = getSampleStyleSheet()
    # Colores: azul corporativo de Rio Futuro
    color_azul = colors.HexColor('#1B4F72')  # Azul oscuro del logo
    color_azul_claro = colors.HexColor('#2E86AB')  # Azul medio
    
    title_style = ParagraphStyle('CustomTitle', 
                                parent=styles['Heading1'], 
                                fontSize=18, 
                                alignment=TA_CENTER,
                                textColor=color_azul,
                                spaceAfter=20)
    
    elements = []
    
    # Título centrado (el logo se sobrepone después)
    elements.append(Paragraph("PROFORMA DE PROVEEDOR", title_style))
    elements.append(Spacer(1, 12))
    
    # Fecha de envío (hoy)
    from datetime import datetime
    fecha_envio = datetime.now().strftime("%d-%m-%Y")
    
    # Información del documento en 2 columnas
    info_data = [
        ["Factura:", factura['nombre'], "", "Fecha Envío:", fecha_envio],
        ["Proveedor:", factura['proveedor_nombre'][:50], "", "Moneda:", "USD / CLP"],
        ["Referencia:", factura.get('ref', '-') or '-', "", "", ""],
    ]
    
    info_table = Table(info_data, colWidths=[1*inch, 3*inch, 0.5*inch, 1.2*inch, 1.3*inch])
    info_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (3, 0), (3, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Tabla de líneas con fecha de OC
    table_data = [["Descripción", "Fecha OC", "Cant.\nKG", "P. Unitario\nUSD", "Tipo\nCambio", "P. Unitario\nCLP", "Subtotal\nUSD", "Subtotal\nCLP"]]
    
    # Necesitamos obtener las fechas de las OCs
    from shared.odoo_client import OdooClient
    client = OdooClient(username=st.session_state.get('username'), password=st.session_state.get('password'))
    
    for linea in factura['lineas']:
        desc = linea['nombre'][:35] if linea['nombre'] else "-"
        cant = linea['cantidad']
        p_unit_usd = linea['precio_usd']
        tc_linea = linea['tc_implicito']
        p_unit_clp = linea['subtotal_clp'] / cant if cant else 0
        subtotal_usd = linea['subtotal_usd']
        subtotal_clp = linea['subtotal_clp']
        
        # Extraer fecha de OC
        fecha_oc = "-"
        if ":" in desc:
            oc_nombre = desc.split(":")[0].strip()
            try:
                ocs = client.search_read(
                    "purchase.order",
                    [("name", "=", oc_nombre)],
                    ["date_order"],
                    limit=1
                )
                if ocs and ocs[0].get("date_order"):
                    fecha_oc = ocs[0]["date_order"][:10]  # YYYY-MM-DD
            except:
                pass
        
        table_data.append([
            desc,
            fecha_oc,
            fmt_cl(cant, 2),
            f"${fmt_cl(p_unit_usd, 2)}",
            fmt_cl(tc_linea, 2),
            f"${fmt_cl(p_unit_clp, 0)}",
            f"${fmt_cl(subtotal_usd, 2)}",
            f"${fmt_cl(subtotal_clp, 0)}"
        ])
    
    # Línea en blanco antes de totales
    table_data.append(["", "", "", "", "", "", "", ""])
    
    # Totales - 3 filas
    table_data.append([
        "", "", "", "", "", "Base Imponible:",
        f"${fmt_cl(factura['base_usd'], 2)}",
        f"${fmt_cl(factura['base_clp'], 0)}"
    ])
    table_data.append([
        "", "", "", "", "", "IVA 19%:",
        f"${fmt_cl(factura['iva_usd'], 2)}",
        f"${fmt_cl(factura['iva_clp'], 0)}"
    ])
    table_data.append([
        "", "", "", "", "", "TOTAL:",
        f"${fmt_cl(factura['total_usd'], 2)}",
        f"${fmt_cl(factura['total_clp'], 0)} *"
    ])
    
    # Anchos de columna ajustados para landscape con fecha OC - más anchos para ver nombres completos
    main_table = Table(table_data, colWidths=[2.0*inch, 0.8*inch, 0.65*inch, 0.8*inch, 0.6*inch, 0.9*inch, 0.9*inch, 1.05*inch])
    main_table.setStyle(TableStyle([
        # Header - azul corporativo con texto más grande y visible
        ('BACKGROUND', (0, 0), (-1, 0), color_azul),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),  # Header más grande
        ('FONTSIZE', (0, 1), (-1, -1), 7),  # Datos más pequeños
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        
        # Grid para líneas de productos
        ('GRID', (0, 0), (-1, len(factura['lineas'])), 0.5, colors.grey),
        ('LINEBELOW', (0, len(factura['lineas'])), (-1, len(factura['lineas'])), 1, colors.black),
        
        # Padding
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        
        # Totales - negritas con fondo azul claro
        ('FONTNAME', (5, -3), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (5, -1), (-1, -1), 9),
        ('LINEABOVE', (5, -3), (-1, -3), 1.5, colors.black),
        ('BACKGROUND', (5, -3), (-1, -1), colors.HexColor('#E8F4F8')),
    ]))
    elements.append(main_table)
    
    # Nota importante sobre el monto a facturar
    elements.append(Spacer(1, 10))
    nota_style = ParagraphStyle('Nota',
                               parent=styles['Normal'],
                               fontSize=8,
                               textColor=color_azul,
                               alignment=TA_LEFT,
                               leftIndent=0.6*inch)
    elements.append(Paragraph(
        "<b>* Este es el monto total en CLP que se debe facturar</b>",
        nota_style
    ))
    
    # Footer
    from datetime import datetime
    anio_actual = datetime.now().year
    
    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle('Footer', 
                                 parent=styles['Normal'],
                                 fontSize=7,
                                 textColor=color_azul,
                                 alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Rio Futuro Procesos SPA | Año {anio_actual}",
        footer_style
    ))
    
    doc.build(elements)
    buffer.seek(0)
    
    # Dibujar logo superpuesto en la esquina superior izquierda
    from reportlab.pdfgen import canvas as pdf_canvas
    from PyPDF2 import PdfReader, PdfWriter
    
    logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "RFP - LOGO OFICIAL.png")
    
    if os.path.exists(logo_path):
        # Leer el PDF generado
        pdf_reader = PdfReader(buffer)
        pdf_writer = PdfWriter()
        
        # Crear un canvas temporal para el logo
        overlay_buffer = io.BytesIO()
        c = pdf_canvas.Canvas(overlay_buffer, pagesize=landscape(letter))
        
        # Dibujar logo en esquina superior izquierda (muy esquinado)
        page_width, page_height = landscape(letter)
        logo_width = 4.2 * inch  # Aún más grande
        logo_height = 1.4 * inch
        x_pos = 0.02 * inch  # Muy a la izquierda - casi en el borde
        y_pos = page_height - 0.15 * inch - logo_height  # Muy arriba - casi en el borde
        
        c.drawImage(logo_path, x_pos, y_pos, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')
        c.save()
        
        # Sobreponer logo en cada página
        overlay_buffer.seek(0)
        overlay_pdf = PdfReader(overlay_buffer)
        overlay_page = overlay_pdf.pages[0]
        
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            page.merge_page(overlay_page)
            pdf_writer.add_page(page)
        
        # Guardar el PDF final con logo
        final_buffer = io.BytesIO()
        pdf_writer.write(final_buffer)
        final_buffer.seek(0)
        return final_buffer.getvalue()
    
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
