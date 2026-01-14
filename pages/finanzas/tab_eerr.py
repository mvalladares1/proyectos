"""
Tab: Estado de Resultados Consolidado
Tabla expandible con formato similar a Flujo de Caja.
Combina vistas de Agrupado, Mensualizado, Detalle y YTD en una sola tabla.
"""
import streamlit as st
from datetime import datetime

from .eerr_table import EERR_CSS, EERR_JS, render_eerr_table
from .eerr_table.constants import MESES_NOMBRES, ESTRUCTURA_EERR
from . import shared


@st.fragment
def render(username: str, password: str):
    """
    Renderiza el tab de Estado de Resultados Consolidado.
    """
    st.subheader("📊 Estado de Resultados")
    st.caption("Vista consolidada mensual con detalle expandible")
    
    # === FILTROS ===
    col_fecha1, col_fecha2, col_btn = st.columns([2, 2, 1])
    
    with col_fecha1:
        fecha_inicio = st.date_input(
            "Desde",
            value=datetime(datetime.now().year, 1, 1),
            key="eerr_fecha_inicio"
        )
    
    with col_fecha2:
        fecha_fin = st.date_input(
            "Hasta",
            value=datetime.now(),
            key="eerr_fecha_fin"
        )
    
    with col_btn:
        st.write("")  # Spacer
        btn_generar = st.button("🔄 Generar", type="primary", use_container_width=True, key="eerr_btn")
    
    # Generar lista de meses entre fechas
    meses_lista = []
    current = datetime(fecha_inicio.year, fecha_inicio.month, 1)
    end = datetime(fecha_fin.year, fecha_fin.month, 1)
    while current <= end:
        meses_lista.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = datetime(current.year + 1, 1, 1)
        else:
            current = datetime(current.year, current.month + 1, 1)
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    cache_key = f"eerr_consolidado_{fecha_inicio}_{fecha_fin}"
    
    if btn_generar:
        if cache_key in st.session_state:
            del st.session_state[cache_key]
        st.session_state["eerr_should_load"] = True
    
    if st.session_state.get("eerr_should_load") or cache_key in st.session_state:
        
        if cache_key not in st.session_state:
            with st.spinner("📊 Cargando Estado de Resultados..."):
                # Usar la función existente de shared
                data = shared.fetch_estado_resultado(
                    fecha_ini=fecha_inicio.strftime("%Y-%m-%d"),
                    fecha_f=fecha_fin.strftime("%Y-%m-%d"),
                    centro=None,  # Sin filtro de centro
                    _username=username,
                    _password=password
                )
                
                if data and "error" not in data:
                    st.session_state[cache_key] = data
                    st.session_state["eerr_should_load"] = False
                    st.toast("✅ Datos cargados", icon="✅")
                else:
                    error_msg = data.get("error", "Error desconocido") if data else "Sin respuesta"
                    st.error(f"Error: {error_msg}")
                    return
        
        data = st.session_state.get(cache_key, {})
        
        if "error" in data:
            st.error(f"Error: {data['error']}")
            return
        
        # Extraer datos del response
        estructura = data.get("estructura", {})
        datos_mensuales = data.get("datos_mensuales", {})
        ppto_mensual = data.get("ppto_mensual", {})
        
        # === CONTROLES DE EXPANSIÓN ===
        col_expand, col_collapse, col_export = st.columns([1, 1, 2])
        
        with col_expand:
            expand_all = st.button("➕ Expandir", use_container_width=True, key="eerr_expand")
        
        with col_collapse:
            collapse_all = st.button("➖ Colapsar", use_container_width=True, key="eerr_collapse")
        
        with col_export:
            # Export button placeholder
            pass
        
        # === RENDERIZAR TABLA CON JS FUNCIONAL ===
        if estructura:
            from streamlit.components.v1 import html as st_html
            
            tabla_html = render_eerr_table(
                estructura=estructura,
                datos_mensuales=datos_mensuales,
                meses_lista=meses_lista,
                ppto_mensual=ppto_mensual
            )
            
            # Acción de expansión/colapso a ejecutar
            js_action = ""
            if expand_all:
                js_action = "setTimeout(() => toggleAllEerr(true), 100);"
            elif collapse_all:
                js_action = "setTimeout(() => toggleAllEerr(false), 100);"
            
            # Combinar CSS + JS + Tabla en un solo componente HTML
            full_html = f"""
            {EERR_CSS}
            {tabla_html}
            <script>
                // Toggle expansión de filas
                function toggleEerrRow(rowId) {{
                    const icon = document.querySelector(`[data-row-id="${{rowId}}"] .expand-icon`);
                    const childRows = document.querySelectorAll(`.child-of-${{rowId}}`);
                    
                    if (icon) {{
                        icon.classList.toggle('expanded');
                    }}
                    
                    childRows.forEach(row => {{
                        row.classList.toggle('hidden-row');
                    }});
                }}
                
                // Expandir/Colapsar todos
                function toggleAllEerr(expand) {{
                    const icons = document.querySelectorAll('.expand-icon');
                    const hiddenRows = document.querySelectorAll('.eerr-table tr[class*="child-of-"]');
                    
                    icons.forEach(icon => {{
                        if (expand) {{
                            icon.classList.add('expanded');
                        }} else {{
                            icon.classList.remove('expanded');
                        }}
                    }});
                    
                    hiddenRows.forEach(row => {{
                        if (expand) {{
                            row.classList.remove('hidden-row');
                        }} else {{
                            row.classList.add('hidden-row');
                        }}
                    }});
                }}
                
                {js_action}
            </script>
            """
            
            # Calcular altura basada en filas
            num_rows = len(ESTRUCTURA_EERR) + sum(1 for c in estructura.values() if isinstance(c, dict))
            table_height = min(max(num_rows * 45 + 100, 500), 900)
            
            st_html(full_html, height=table_height, scrolling=True)
        else:
            st.warning("⚠️ No hay datos disponibles para el período seleccionado.")
            
            # Debug info
            with st.expander("🔍 Información de Debug"):
                st.write("Meses consultados:", meses_lista)
                st.write("Datos recibidos:", list(data.keys()) if data else "Ninguno")
    else:
        st.info("👆 Selecciona el rango de fechas y haz clic en **Generar** para ver el Estado de Resultados")

