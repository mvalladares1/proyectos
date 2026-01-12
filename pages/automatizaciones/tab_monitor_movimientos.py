"""
Tab: Monitor de Movimientos
Historial de movimientos del día con filtros y referencia rápida.
"""
import streamlit as st
import pandas as pd
from datetime import datetime


def render():
    """Renderiza el tab de Monitor de Movimientos"""
    
    username = st.session_state.get("username")
    password = st.session_state.get("password")
    api_url = st.session_state.get("api_url", "http://localhost:8000")
    
    st.title("📊 Monitor de Movimientos")
    st.markdown("Historial de movimientos realizados hoy")
    
    # Inicializar historial si no existe
    if "mov_historial_dia" not in st.session_state:
        st.session_state.mov_historial_dia = []
    
    historial = st.session_state.mov_historial_dia
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 1: MÉTRICAS DEL DÍA
    # ═══════════════════════════════════════════════════════════════
    
    st.markdown("### 📈 Resumen del Día")
    
    if historial:
        total_movimientos = len(historial)
        total_pallets = sum(h["cantidad"] for h in historial)
        total_kg = sum(h["kg"] for h in historial)
        total_exitosos = sum(h["success"] for h in historial)
        total_fallidos = sum(h["failed"] for h in historial)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Movimientos", total_movimientos)
        col2.metric("Pallets Movidos", total_pallets)
        col3.metric("KG Totales", f"{total_kg:,.0f}")
        col4.metric("Tasa Éxito", f"{(total_exitosos / (total_exitosos + total_fallidos) * 100):.0f}%" if (total_exitosos + total_fallidos) > 0 else "N/A")
    else:
        st.info("📭 No hay movimientos registrados hoy")
        return
    
    st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 2: ÚLTIMO MOVIMIENTO + UNDO
    # ═══════════════════════════════════════════════════════════════
    
    if "mov_ultimo_movimiento" in st.session_state and st.session_state.mov_ultimo_movimiento:
        ultimo = st.session_state.mov_ultimo_movimiento
        
        st.markdown("### ↩️ Último Movimiento")
        
        with st.container(border=True):
            col_info, col_btn = st.columns([3, 1])
            
            with col_info:
                st.markdown(f"""
                **⏰ {ultimo['timestamp']}** → **{ultimo['destino']['name']}**  
                📦 {len(ultimo['pallets'])} pallets • {sum(p['kg'] for p in ultimo['pallets']):,.0f} kg
                """)
            
            with col_btn:
                if st.button("↩️ Deshacer", key="btn_undo", type="secondary", use_container_width=True):
                    st.warning("⚠️ La función de deshacer requiere implementación del API de movimiento inverso")
                    # TODO: Implementar endpoint de undo en el backend
                    # _deshacer_ultimo(username, password, api_url)
        
        st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 3: HISTORIAL COMPLETO
    # ═══════════════════════════════════════════════════════════════
    
    st.markdown("### 📋 Historial de Movimientos")
    
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        destinos_unicos = list(set(h["destino"] for h in historial))
        filtro_destino = st.selectbox(
            "Filtrar por destino",
            ["Todos"] + destinos_unicos,
            key="filtro_destino_monitor"
        )
    
    # Aplicar filtro
    historial_filtrado = historial
    if filtro_destino != "Todos":
        historial_filtrado = [h for h in historial if h["destino"] == filtro_destino]
    
    # Tabla de historial
    if historial_filtrado:
        for i, mov in enumerate(historial_filtrado):
            status_color = "#4CAF50" if mov["failed"] == 0 else "#ff9800"
            status_icon = "✅" if mov["failed"] == 0 else "⚠️"
            
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; 
                        background: rgba(255,255,255,0.05); border-radius: 8px; margin-bottom: 8px;
                        border-left: 3px solid {status_color};">
                <div>
                    <span style="font-size: 1.1rem; font-weight: 600;">{status_icon} {mov['destino']}</span>
                    <span style="color: #aaa; margin-left: 12px;">⏰ {mov['timestamp']}</span>
                </div>
                <div style="text-align: right;">
                    <span style="color: #4FC3F7; font-weight: 600;">{mov['cantidad']} pallets</span>
                    <span style="color: #aaa; margin-left: 8px;">{mov['kg']:,.0f} kg</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Exportar
        with st.expander("📥 Exportar datos"):
            df_historial = pd.DataFrame(historial_filtrado)
            csv = df_historial.to_csv(index=False)
            st.download_button(
                "📥 Descargar CSV",
                csv,
                f"movimientos_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    else:
        st.info("No hay movimientos con los filtros aplicados")
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 4: LIMPIAR HISTORIAL
    # ═══════════════════════════════════════════════════════════════
    
    st.markdown("---")
    
    if st.button("🗑️ Limpiar historial del día", key="btn_clear_historial"):
        st.session_state.mov_historial_dia = []
        st.session_state.mov_ultimo_movimiento = None
        st.toast("Historial limpiado", icon="🗑️")
        st.rerun()
