"""
Tab: Revertir Consumo
Herramienta para revertir el consumo de órdenes de fabricación de desmontaje.
Recupera MP a paquetes originales y elimina subproductos.
"""
import streamlit as st
import requests
from typing import Dict

from .shared import API_URL


@st.fragment
def render(username: str, password: str):
    """Renderiza el contenido del tab Revertir Consumo."""
    st.header("🔄 Revertir Consumo de ODF")
    
    st.info(
        "💡 **¿Cuándo usar esta herramienta?**\n\n"
        "Cuando hiciste un **desmontaje/deconstrucción** para recuperar MP pero:\n"
        "- Los componentes (MP) quedaron sin paquete asignado\n"
        "- Los subproductos (congelado) no deberían existir\n\n"
        "Esta herramienta:\n"
        "✅ Reasigna la MP a sus paquetes originales\n"
        "✅ Elimina los subproductos (pone cantidades en 0)"
    )
    
    st.divider()
    
    # Input de ODF
    st.subheader("1️⃣ Orden de Fabricación a Revertir")
    
    odf_name = st.text_input(
        "Código de la ODF",
        placeholder="VLK/CongTE109",
        help="Nombre completo de la orden de fabricación de desmontaje"
    ).strip().upper()
    
    if not odf_name:
        st.warning("⚠️ Ingresa el código de la ODF para continuar")
        return
    
    st.divider()
    
    # Botón de reversión
    st.subheader("2️⃣ Ejecutar Reversión")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.warning(
            "⚠️ **Atención:** Esta acción:\n"
            "- Creará transferencias internas para recuperar MP\n"
            "- Pondrá en 0 las cantidades de subproductos\n"
            "- No se puede deshacer automáticamente"
        )
    
    with col2:
        ejecutar = st.button(
            "🔄 REVERTIR",
            type="primary",
            use_container_width=True,
            disabled=not odf_name
        )
    
    if ejecutar:
        _ejecutar_reversion(username, password, odf_name)


def _ejecutar_reversion(username: str, password: str, odf_name: str):
    """Ejecuta la reversión del consumo de la ODF."""
    
    with st.spinner(f"Revirtiendo consumo de {odf_name}..."):
        try:
            response = requests.post(
                f"{API_URL}/api/v1/automatizaciones/revertir-consumo-odf",
                json={"odf_name": odf_name},
                params={
                    "username": username,
                    "password": password
                },
                timeout=120  # 2 minutos
            )
            
            if response.status_code == 200:
                resultado = response.json()
                
                if resultado.get("success"):
                    st.success(f"### {resultado.get('message', '✅ Reversión completada')}")
                    
                    # Mostrar detalles en tabs
                    tab1, tab2, tab3 = st.tabs(["📦 Componentes", "🧊 Subproductos", "📋 Transferencias"])
                    
                    with tab1:
                        _mostrar_componentes(resultado.get("componentes_revertidos", []))
                    
                    with tab2:
                        _mostrar_subproductos(resultado.get("subproductos_eliminados", []))
                    
                    with tab3:
                        _mostrar_transferencias(resultado.get("transferencias_creadas", []))
                    
                    # Mostrar errores si hay
                    if resultado.get("errores"):
                        st.warning(f"⚠️ Se encontraron {len(resultado['errores'])} advertencias:")
                        for error in resultado["errores"]:
                            st.caption(f"• {error}")
                else:
                    st.error(f"❌ {resultado.get('message', 'Error en la reversión')}")
                    
                    if resultado.get("errores"):
                        st.error("**Errores:**")
                        for error in resultado["errores"]:
                            st.caption(f"• {error}")
            else:
                error_detail = response.json().get("detail", "Error desconocido")
                st.error(f"❌ Error en la API: {error_detail}")
                
        except requests.Timeout:
            st.error("❌ Timeout: La operación tardó demasiado. Verifica en Odoo si se completó.")
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")


def _mostrar_componentes(componentes: list):
    """Muestra tabla de componentes recuperados."""
    if not componentes:
        st.info("No se recuperaron componentes")
        return
    
    st.write(f"**Total recuperados:** {len(componentes)}")
    
    # Crear tabla
    data = []
    for comp in componentes:
        data.append({
            "Producto": comp.get("producto", "N/A"),
            "Lote": comp.get("lote", "N/A"),
            "Paquete": comp.get("paquete", "N/A"),
            "Cantidad (Kg)": f"{comp.get('cantidad', 0):.2f}",
            "Transferencia": comp.get("transferencia", "N/A")
        })
    
    st.dataframe(data, use_container_width=True, hide_index=True)


def _mostrar_subproductos(subproductos: list):
    """Muestra tabla de subproductos eliminados."""
    if not subproductos:
        st.info("No se eliminaron subproductos")
        return
    
    st.write(f"**Total eliminados:** {len(subproductos)}")
    
    # Crear tabla
    data = []
    for sub in subproductos:
        data.append({
            "Producto": sub.get("producto", "N/A"),
            "Cantidad Original (Kg)": f"{sub.get('cantidad_original', 0):.2f}",
            "Nueva Cantidad (Kg)": f"{sub.get('nueva_cantidad', 0):.2f}"
        })
    
    st.dataframe(data, use_container_width=True, hide_index=True)


def _mostrar_transferencias(transferencias: list):
    """Muestra lista de transferencias creadas."""
    if not transferencias:
        st.info("No se crearon transferencias")
        return
    
    st.write(f"**Total creadas:** {len(transferencias)}")
    
    for i, trans in enumerate(transferencias, 1):
        st.caption(f"{i}. {trans}")
