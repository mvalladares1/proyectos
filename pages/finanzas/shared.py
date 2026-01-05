"""
Módulo compartido para Finanzas.
Contiene funciones de utilidad, formateo, llamadas a API y configuraciones.
"""
import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ESTADO_RESULTADO_URL = f"{API_URL}/api/v1/estado-resultado"
PRESUPUESTO_URL = f"{API_URL}/api/v1/presupuesto"
FLUJO_CAJA_URL = f"{API_URL}/api/v1/flujo-caja"


# ===================== FORMATEO =====================

def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal (formato chileno)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)


def fmt_dinero(valor, decimales=0):
    """Formatea valor monetario con símbolo $"""
    return f"${fmt_numero(valor, decimales)}"


def fmt_flujo(valor):
    """Formatea monto de flujo de caja con signo."""
    if valor >= 0:
        return f"${valor:,.0f}"
    else:
        return f"-${abs(valor):,.0f}"


def fmt_monto(valor):
    """Formatea monto para Estado de Resultados."""
    if valor >= 0:
        return f"${valor:,.0f}"
    else:
        return f"-${abs(valor):,.0f}"


def fmt_pct(valor):
    """Formatea porcentaje."""
    if valor is None or str(valor) == "inf" or (isinstance(valor, float) and pd.isna(valor)):
        return "-"
    return f"{valor:.1f}%"


# ===================== SESSION STATE =====================

def init_session_state():
    """Inicializa variables de session_state para el módulo Finanzas."""
    defaults = {
        'finanzas_eerr_datos': None,
        'finanzas_eerr_ppto': None,
        'finanzas_flujo_data': None,
        'finanzas_flujo_clicked': False,
        'finanzas_mostrar_editor': False,
        'finanzas_cuenta_a_editar': None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


# ===================== API CALLS =====================

@st.cache_data(ttl=300, show_spinner=False)
def fetch_centros_costo(_username, _password):
    """Obtiene lista de centros de costo disponibles."""
    try:
        resp = requests.get(
            f"{ESTADO_RESULTADO_URL}/centros-costo",
            params={"username": _username, "password": _password},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except:
        return []


@st.cache_data(ttl=300, show_spinner="Cargando datos desde Odoo...")
def fetch_estado_resultado(fecha_ini, fecha_f, centro, _username, _password):
    """Obtiene el estado de resultado desde Odoo."""
    try:
        params = {
            "fecha_inicio": fecha_ini,
            "username": _username,
            "password": _password
        }
        if fecha_f:
            params["fecha_fin"] = fecha_f
        if centro:
            params["centro_costo"] = centro
        resp = requests.get(f"{ESTADO_RESULTADO_URL}/", params=params, timeout=120)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


@st.cache_data(ttl=300, show_spinner="Cargando presupuesto...")
def fetch_presupuesto(año, centro=None):
    """Obtiene datos de presupuesto."""
    try:
        params = {"año": año}
        if centro:
            params["centro_costo"] = centro
        resp = requests.get(f"{PRESUPUESTO_URL}/", params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}


def fetch_flujo_caja(fecha_inicio, fecha_fin, _username, _password):
    """Obtiene flujo de caja (sin caché para datos frescos al regenerar)."""
    try:
        resp = requests.get(
            f"{FLUJO_CAJA_URL}/",
            params={
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "username": _username,
                "password": _password
            },
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return {"error": f"Error {resp.status_code}: {resp.text}"}
    except Exception as e:
        return {"error": str(e)}


def guardar_mapeo_cuenta(codigo, categoria, nombre, username, password, impacto=None):
    """Guarda el mapeo de una cuenta a una categoría IAS 7."""
    try:
        final_categoria = categoria if categoria != "UNCLASSIFIED" else None
        resp = requests.post(
            f"{FLUJO_CAJA_URL}/mapeo-cuenta",
            params={
                "codigo": codigo,
                "categoria": final_categoria,
                "nombre": nombre,
                "username": username,
                "password": password,
                "impacto_estimado": impacto
            },
            timeout=10
        )
        if resp.status_code == 200:
            return True, None
        else:
            try:
                detail = resp.json().get('detail', resp.text[:100])
            except:
                detail = resp.text[:100]
            return False, f"Error {resp.status_code}: {detail}"
    except Exception as e:
        return False, f"Error conexión: {e}"


# ===================== IAS 7 HELPERS =====================

def build_ias7_categories_dropdown():
    """
    Retorna las categorías IAS 7 para el dropdown del editor de mapeo.
    Formato: {"label": "value"}
    """
    return {
        "--- Seleccionar ---": "",
        "❌ Dejar Sin Clasificar (Limpiar)": "UNCLASSIFIED",
        "🟢 1.1.1 - Cobros procedentes de las ventas de bienes y prestación de servicios": "1.1.1",
        "🟢 1.2.1 - Pagos a proveedores por el suministro de bienes y servicios": "1.2.1",
        "🟢 1.2.2 - Pagos a y por cuenta de los empleados": "1.2.2",
        "🟢 1.2.3 - Intereses pagados": "1.2.3",
        "🟢 1.2.4 - Intereses recibidos": "1.2.4",
        "🟢 1.2.5 - Impuestos a las ganancias reembolsados (pagados)": "1.2.5",
        "🟢 1.2.6 - Otras entradas (salidas) de efectivo": "1.2.6",
        "🔵 2.1 - Flujos para obtener control de subsidiarias": "2.1",
        "🔵 2.2 - Compra de participaciones no controladoras": "2.2",
        "🔵 2.3 - Compras de propiedades, planta y equipo": "2.3",
        "🔵 2.4 - Compras de activos intangibles": "2.4",
        "🔵 2.5 - Dividendos recibidos": "2.5",
        "🟣 3.0.1 - Importes procedentes de préstamos de largo plazo": "3.0.1",
        "🟣 3.0.2 - Importes procedentes de préstamos de corto plazo": "3.0.2",
        "🟣 3.1.1 - Préstamos de entidades relacionadas": "3.1.1",
        "🟣 3.1.2 - Pagos de préstamos": "3.1.2",
        "🟣 3.1.3 - Pagos de préstamos a entidades relacionadas": "3.1.3",
        "🟣 3.1.4 - Pagos de pasivos por arrendamientos financieros": "3.1.4",
        "🟣 3.1.5 - Dividendos pagados": "3.1.5",
        "🟣 3.2.3 - Otros flujos de financiamiento": "3.2.3",
        "⚪ 4.2 - Efectos variación tasa de cambio": "4.2",
        "⚪ NEUTRAL - Transferencias internas (no impacta flujo)": "NEUTRAL"
    }


def sugerir_categoria(nombre_cuenta: str, monto: float) -> tuple:
    """
    Sugiere una categoría IAS 7 basada en el nombre de la cuenta y el monto.
    Retorna (codigo_sugerido, razon) o (None, None) si no hay sugerencia.
    """
    if not nombre_cuenta:
        return (None, None)
    
    nombre_lower = nombre_cuenta.lower()
    
    # NEUTRAL: Cuentas transitorias/internas
    if any(kw in nombre_lower for kw in ['transitoria', 'intercuenta', 'puente', 'traspaso']):
        return ("NEUTRAL", "Cuenta transitoria/interna")
    
    # FX: Diferencia tipo cambio
    if any(kw in nombre_lower for kw in ['tipo de cambio', 'diferencia cambio', 'ajuste cambiario']):
        return ("4.2", "Diferencia tipo de cambio")
    
    # Operación - Cobros
    if any(kw in nombre_lower for kw in ['facturas por cobrar', 'clientes', 'cuentas por cobrar', 'ventas']):
        return ("1.1.1", "Cobros por ventas")
    
    # Operación - Pagos a proveedores
    if any(kw in nombre_lower for kw in ['proveedores', 'cuentas por pagar', 'acreedores', 'aduana']):
        return ("1.2.1", "Pagos a proveedores")
    
    # Operación - Pagos a empleados
    if any(kw in nombre_lower for kw in ['remuneracion', 'sueldo', 'salario', 'honorario', 'empleado']):
        return ("1.2.2", "Pagos a empleados")
    
    # Operación - Intereses
    if 'interes' in nombre_lower:
        if monto >= 0:
            return ("1.2.4", "Intereses recibidos")
        else:
            return ("1.2.3", "Intereses pagados")
    
    # Operación - Impuestos
    if any(kw in nombre_lower for kw in ['impuesto', 'iva', 'ppm', 'renta']):
        return ("1.2.5", "Impuestos")
    
    # Inversión - PPE
    if any(kw in nombre_lower for kw in ['propiedad', 'planta', 'equipo', 'maquinaria', 'vehiculo']):
        return ("2.3", "Compra PPE")
    
    # Financiamiento - Préstamos
    if any(kw in nombre_lower for kw in ['prestamo', 'credito', 'deuda']):
        if monto >= 0:
            return ("3.0.1", "Préstamos recibidos")
        else:
            return ("3.1.2", "Pagos préstamos")
    
    # Transferencias internas
    if any(kw in nombre_lower for kw in ['transferencia', 'traspaso', 'transfer']):
        return ("NEUTRAL", "Posible transferencia interna")
    
    return (None, None)


# ===================== RENDER HELPERS (IAS 7 Tree) =====================

def render_ias7_tree_node(node, cuentas_por_concepto, docs_por_concepto, act_color="#2ecc71"):
    """
    Renderiza un nodo del árbol IAS 7 con su composición de cuentas y documentos.
    """
    c_id = node.get("id", "")
    c_nombre = node.get("nombre", "")
    c_tipo = node.get("tipo", "LINEA")
    c_nivel = node.get("nivel", 3)
    monto_real = node.get("monto_real", 0)
    monto_proy = node.get("monto_proyectado", 0)
    monto = node.get("monto_display", monto_real + monto_proy)
    
    # Estilos por tipo y nivel
    indent = (c_nivel - 1) * 25
    if c_tipo == "HEADER":
        font_weight = "bold"
        font_size = "1.15em" if c_nivel == 1 else "1.05em"
        bg_color = "transparent"
        border_l = f"4px solid {act_color}"
    elif c_tipo == "TOTAL":
        font_weight = "bold"
        font_size = "1.1em"
        bg_color = f"{act_color}15"
        border_l = f"4px solid {act_color}"
    else:  # LINEA
        font_weight = "normal"
        font_size = "1em"
        bg_color = "#1a1a2e"
        border_l = "none"
    
    # Color del monto
    if monto > 0:
        monto_color = "#2ecc71"
    elif monto < 0:
        monto_color = "#e74c3c"
    else:
        monto_color = "#718096"
    
    # Indicadores adicionales
    has_cuentas = c_id in cuentas_por_concepto and len(cuentas_por_concepto[c_id]) > 0
    has_docs = c_id in docs_por_concepto and len(docs_por_concepto[c_id]) > 0
    
    # Renderizar el nodo principal
    if c_tipo in ("HEADER", "TOTAL") or monto != 0 or has_cuentas or has_docs:
        st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; 
                    padding: 10px 15px; margin-left: {indent}px; border-radius: 6px; 
                    margin-top: {8 if c_nivel == 1 else 3}px; border-left: {border_l};
                    background: {bg_color};">
            <div style="flex-grow: 1;">
                <span style="font-family: monospace; color: #718096; font-size: 0.8em; margin-right: 8px;">{c_id}</span>
                <span style="font-weight: {font_weight}; font-size: {font_size}; color: #e0e0e0;">{c_nombre}</span>
            </div>
                <span style="color: {monto_color}; font-weight: bold; font-family: monospace; font-size: 1.1em;">
                    {fmt_flujo(monto) if (c_tipo == "TOTAL" or (c_tipo == "LINEA" and monto != 0)) else ""}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Drill-down para LINEAs con composición
        if c_tipo == "LINEA" and (has_cuentas or has_docs):
            with st.expander(f"🔍 Ver composición de {c_id}", expanded=False):
                if has_cuentas:
                    render_account_composition(c_id, cuentas_por_concepto[c_id], monto_real)
                if has_docs:
                    render_document_details(c_id, docs_por_concepto[c_id])


def render_account_composition(concepto_id, cuentas, subtotal):
    """Renderiza la tabla de composición por cuentas contables."""
    st.markdown(f"<div style='font-size:0.85em; color:#a0aec0; margin-bottom: 6px; font-weight: bold;'>📊 Composición contable ({concepto_id})</div>", unsafe_allow_html=True)
    
    h_c1, h_c2, h_c3, h_c4 = st.columns([1, 2.5, 1.2, 0.8])
    h_c1.caption("**Código**")
    h_c2.caption("**Nombre**")
    h_c3.caption("**Monto**")
    h_c4.caption("**% Línea**")
    
    divisor = abs(subtotal) if subtotal != 0 else 1
    
    for cuenta in cuentas[:15]:
        codigo = cuenta.get('codigo', '')
        nombre = cuenta.get('nombre', '')[:40]
        monto_c = cuenta.get('monto', 0)
        pct = abs(monto_c) / divisor * 100 if divisor != 1 else 0
        
        monto_color = "#2ecc71" if monto_c >= 0 else "#e74c3c"
        monto_display = f"+${monto_c:,.0f}" if monto_c >= 0 else f"-${abs(monto_c):,.0f}"
        
        cc1, cc2, cc3, cc4 = st.columns([1, 2.5, 1.2, 0.8])
        with cc1:
            st.markdown(f"<span style='color: #718096; font-family: monospace; font-size: 0.85em;'>{codigo}</span>", unsafe_allow_html=True)
        with cc2:
            st.caption(nombre)
        with cc3:
            st.markdown(f"<span style='color:{monto_color}; font-size: 0.9em;'>{monto_display}</span>", unsafe_allow_html=True)
        with cc4:
            st.caption(f"{pct:.1f}%")
    
    if len(cuentas) > 15:
        st.caption(f"... y {len(cuentas) - 15} cuentas más")


def render_document_details(concepto_id, documentos):
    """Renderiza la tabla de documentos proyectados."""
    st.markdown(f"<div style='font-size:0.85em; color:#f39c12; margin: 12px 0 6px 0; font-weight: bold;'>🟡 Detalles Proyectados ({concepto_id})</div>", unsafe_allow_html=True)
    
    h1, h2, h3, h4, h5 = st.columns([1.2, 1.8, 0.8, 0.8, 1])
    h1.caption("**Documento**")
    h2.caption("**Partner**")
    h3.caption("**Venc.**")
    h4.caption("**Estado**")
    h5.caption("**Monto**")
    
    for doc in documentos[:20]:
        monto_d = doc.get('monto', 0)
        color_d = "#f39c12" if monto_d >= 0 else "#d35400"
        fmt_d = f"+${monto_d:,.0f}" if monto_d >= 0 else f"-${abs(monto_d):,.0f}"
        
        d1, d2, d3, d4, d5 = st.columns([1.2, 1.8, 0.8, 0.8, 1])
        d1.caption(doc.get('documento', '')[:15])
        d2.caption(doc.get('partner', '')[:20])
        d3.caption(str(doc.get('fecha_venc', ''))[:10])
        d4.caption(doc.get('estado', ''))
        d5.markdown(f"<span style='color:{color_d}; font-size: 0.9em;'>{fmt_d}</span>", unsafe_allow_html=True)
    
    if len(documentos) > 20:
        st.caption(f"... y {len(documentos) - 20} documentos más")


def render_ias7_tree_activity(actividad_data, cuentas_por_concepto, docs_por_concepto, actividad_key, color):
    """Renderiza una actividad completa como árbol IAS 7."""
    act_nombre = actividad_data.get("nombre", actividad_key)
    subtotal = actividad_data.get("subtotal", 0)
    conceptos = actividad_data.get("conceptos", [])
    
    subtotal_color = "#2ecc71" if subtotal >= 0 else "#e74c3c"
    
    with st.expander(f"📊 {act_nombre} ({fmt_flujo(subtotal)})", expanded=(actividad_key == "OPERACION")):
        for concepto in sorted(conceptos, key=lambda x: x.get("order", x.get("id", ""))):
            render_ias7_tree_node(
                node={
                    "id": concepto.get("id") or concepto.get("codigo"),
                    "nombre": concepto.get("nombre"),
                    "tipo": concepto.get("tipo", "LINEA"),
                    "nivel": concepto.get("nivel", 3),
                    "monto_real": concepto.get("monto", 0),
                    "monto_proyectado": concepto.get("monto_proyectado", 0),
                    "monto_display": concepto.get("monto", 0),
                },
                cuentas_por_concepto=cuentas_por_concepto,
                docs_por_concepto=docs_por_concepto,
                act_color=color
            )
        
        subtotal_nombre = actividad_data.get("subtotal_nombre", "Subtotal")
        st.markdown(f"""
        <div style="background: linear-gradient(90deg, {color}22, transparent); 
                    padding: 12px 15px; border-radius: 8px; margin-top: 10px;
                    border-left: 3px solid {color};">
            <span style="color: #a0aec0;">{subtotal_nombre}:</span>
            <span style="color: {subtotal_color}; font-size: 1.2em; font-weight: bold; margin-left: 10px;">
                {fmt_flujo(subtotal)}
            </span>
        </div>
        """, unsafe_allow_html=True)
