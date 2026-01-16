"""
Tab: Estado de Resultados Consolidado
Tabla expandible con formato similar a Flujo de Caja.
Usa los filtros de la sidebar (Año, Mes, Centro de Costos).
"""
import streamlit as st
from datetime import datetime
from streamlit.components.v1 import html as st_html

from .eerr_table import EERR_CSS, render_eerr_table
from .eerr_table.constants import MESES_NOMBRES, ESTRUCTURA_EERR
from . import shared


@st.fragment
def render(username: str, password: str, estructura: dict, datos_mensuales: dict, 
           meses_lista: list, ppto_mensual: dict):
    """
    Renderiza el tab de Estado de Resultados Consolidado.
    
    Args:
        username: Usuario para API
        password: Password para API
        estructura: Estructura del EERR con categorías y subcategorías
        datos_mensuales: Datos mensuales del EERR
        meses_lista: Lista de meses a mostrar (formato YYYY-MM)
        ppto_mensual: Datos del presupuesto mensual
    """
    st.subheader("📊 Estado de Resultados")
    st.caption("Vista consolidada mensual con detalle expandible")
    
    # Mostrar período seleccionado
    if meses_lista:
        mes_inicio = meses_lista[0]
        mes_fin = meses_lista[-1]
        st.info(f"📅 Período: **{mes_inicio}** a **{mes_fin}** ({len(meses_lista)} meses)")
    
    st.markdown("---")
    
    # === RENDERIZAR TABLA ===
    if estructura:
        tabla_html = render_eerr_table(
            estructura=estructura,
            datos_mensuales=datos_mensuales,
            meses_lista=meses_lista,
            ppto_mensual=ppto_mensual
        )
        
        # JavaScript para expansión
        js_code = """
        <script>
            function toggleEerrRow(rowId) {
                const icon = document.querySelector(`[data-row-id="${rowId}"] .expand-icon`);
                const childRows = document.querySelectorAll(`.child-of-${rowId}`);
                
                if (icon) {
                    icon.classList.toggle('expanded');
                }
                
                childRows.forEach(row => {
                    row.classList.toggle('hidden-row');
                });
            }
        </script>
        """
        
        # Combinar todo en un solo HTML
        full_html = f"{EERR_CSS}\n{tabla_html}\n{js_code}"
        
        # Calcular altura basada en filas visibles
        num_visible_rows = len(ESTRUCTURA_EERR)
        table_height = min(max(num_visible_rows * 50 + 80, 450), 850)
        
        st_html(full_html, height=table_height, scrolling=True)
    else:
        st.warning("⚠️ No hay datos disponibles para el período seleccionado.")
        st.caption("Utiliza los filtros de la barra lateral para cambiar el período.")
