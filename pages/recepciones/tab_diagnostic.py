"""
Tab temporal: Verificador de IDs de Picking Types
"""
import streamlit as st
from shared.odoo_client import OdooClient

def render(username: str, password: str):
    st.subheader("🔍 Verificador de IDs de Picking Types")
    st.caption("Herramienta de diagnóstico para encontrar el ID correcto de San José")
    
    if st.button("🔄 Buscar Picking Types en Odoo", type="primary"):
        with st.spinner("Consultando Odoo..."):
            try:
                client = OdooClient(username=username, password=password)
                
                # Buscar todos los picking types de recepciones MP
                pts = client.search_read(
                    "stock.picking.type",
                    [("name", "ilike", "Recepciones MP")],
                    ["id", "name", "warehouse_id"]
                )
                
                if not pts:
                    st.error("❌ No se encontraron Picking Types con 'Recepciones MP'")
                else:
                    st.success(f"✅ Se encontraron {len(pts)} Picking Types")
                    
                    # Mostrar en una tabla
                    import pandas as pd
                    
                    data = []
                    for pt in pts:
                        warehouse = pt.get('warehouse_id', [None, 'N/A'])
                        warehouse_name = warehouse[1] if isinstance(warehouse, (list, tuple)) else warehouse
                        
                        # Identificar cuál podría ser San José
                        es_san_jose = 'SAN JOSE' in pt['name'].upper() or 'SANJOSE' in pt['name'].upper()
                        
                        data.append({
                            "ID": pt['id'],
                            "Nombre": pt['name'],
                            "Warehouse": warehouse_name,
                            "¿Es San José?": "✅ SÍ" if es_san_jose else ""
                        })
                    
                    df = pd.DataFrame(data)
                    
                    st.dataframe(
                        df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "ID": st.column_config.NumberColumn("ID", format="%d"),
                            "Nombre": st.column_config.TextColumn("Nombre del Picking Type"),
                            "Warehouse": st.column_config.TextColumn("Almacén"),
                            "¿Es San José?": st.column_config.TextColumn("¿Es San José?")
                        }
                    )
                    
                    # Buscar específicamente San José
                    san_jose = [p for p in pts if 'SAN JOSE' in p['name'].upper() or 'SANJOSE' in p['name'].upper()]
                    
                    if san_jose:
                        st.success("🎯 ENCONTRADO SAN JOSÉ:")
                        for sj in san_jose:
                            st.info(f"**ID: {sj['id']}** | Nombre: {sj['name']}")
                            
                            # Verificar si es diferente a 218
                            if sj['id'] != 218:
                                st.warning(f"⚠️ El ID actual es **{sj['id']}**, pero el código está usando **218**")
                                st.code(f"""
# Necesitas actualizar estos archivos con el ID correcto: {sj['id']}

# En: backend/services/recepcion_service.py
ORIGEN_PICKING_MAP = {{
    "RFP": 1,
    "VILKUN": 217,
    "SAN JOSE": {sj['id']}  # <-- Cambiar 218 por {sj['id']}
}}
                                """, language="python")
                            else:
                                st.success("✅ El ID 218 es correcto!")
                    else:
                        st.warning("⚠️ No se encontró ningún Picking Type con 'San Jose' en el nombre")
                        st.info("👆 Revisa la tabla de arriba y busca manualmente cuál corresponde a San José")
                    
            except Exception as e:
                st.error(f"❌ Error al conectar con Odoo: {e}")
    
    with st.expander("ℹ️ ¿Para qué sirve esto?"):
        st.markdown("""
        Este tab te ayuda a verificar el **ID correcto** del Picking Type de San José en Odoo.
        
        **¿Por qué es importante?**
        - El backend usa IDs numéricos para identificar cada planta (RFP=1, VILKUN=217)
        - Si el ID de San José no es 218, el sistema no encontrará datos
        - Esta herramienta te muestra el ID real y te da el código para corregirlo
        
        **Instrucciones:**
        1. Click en "Buscar Picking Types en Odoo"
        2. Busca en la tabla la fila que dice "San Jose" o similar
        3. Anota el ID que aparece
        4. Si es diferente a 218, usa el código que aparece para actualizarlo
        """)
