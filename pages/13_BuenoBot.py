"""
🤖 BUENOBOT - Quality Assurance & Security Dashboard
Sistema de control de calidad y seguridad para Rio Futuro Dashboards.

Permite:
- Ejecutar scans de QA (Quick/Full)
- Ver progreso en tiempo real
- Analizar resultados por categoría
- Descargar reportes
- Comparar con scans anteriores
"""
import streamlit as st
import sys
import os
from pathlib import Path
import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Configuración de la página
st.set_page_config(
    page_title="🤖 BUENOBOT",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Importar autenticación
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.auth import proteger_pagina, obtener_info_sesion, get_credenciales

# Requerir autenticación
proteger_pagina()

# Obtener info de sesión
session_info = obtener_info_sesion()
username = session_info.get("email", "Unknown")

# === CONFIGURACIÓN ===
API_BASE = os.environ.get("API_URL", "http://127.0.0.1:8002")
BUENOBOT_API = f"{API_BASE}/buenobot"

# === CSS PERSONALIZADO ===
st.markdown("""
<style>
    /* Gate Status Cards */
    .gate-pass {
        background: linear-gradient(135deg, #10B981 0%, #059669 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);
    }
    .gate-warn {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(245, 158, 11, 0.3);
    }
    .gate-fail {
        background: linear-gradient(135deg, #EF4444 0%, #DC2626 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        box-shadow: 0 4px 6px rgba(239, 68, 68, 0.3);
    }
    .gate-running {
        background: linear-gradient(135deg, #3B82F6 0%, #2563EB 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.7; }
    }
    
    /* Findings */
    .finding-critical {
        background-color: #FEE2E2;
        border-left: 4px solid #EF4444;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .finding-high {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .finding-medium {
        background-color: #FEF9C3;
        border-left: 4px solid #EAB308;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    .finding-low {
        background-color: #DBEAFE;
        border-left: 4px solid #3B82F6;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0 8px 8px 0;
    }
    
    /* Check Status */
    .check-passed { color: #10B981; font-weight: bold; }
    .check-failed { color: #EF4444; font-weight: bold; }
    .check-skipped { color: #6B7280; }
    
    /* Log viewer */
    .log-viewer {
        background-color: #1E1E1E;
        color: #D4D4D4;
        font-family: 'Consolas', 'Monaco', monospace;
        font-size: 12px;
        padding: 1rem;
        border-radius: 8px;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)


# === HELPER FUNCTIONS ===

def api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Realiza una request al API de BUENOBOT"""
    url = f"{BUENOBOT_API}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        else:
            response = requests.request(method, url, json=data, timeout=30)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error(f"❌ No se pudo conectar al API: {url}")
        return {"error": "Connection error"}
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error HTTP: {e}")
        return {"error": str(e)}
    except Exception as e:
        st.error(f"❌ Error: {e}")
        return {"error": str(e)}


def get_gate_status_html(status: str, reason: str = "") -> str:
    """Genera HTML para el status del gate"""
    status_lower = status.lower()
    emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌", "running": "🔄"}.get(status_lower, "❓")
    
    return f"""
    <div class="gate-{status_lower}">
        {emoji} {status.upper()}
        <div style="font-size: 0.9rem; font-weight: normal; margin-top: 0.5rem;">
            {reason}
        </div>
    </div>
    """


def format_duration(seconds: float) -> str:
    """Formatea duración en segundos a formato legible"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


def get_severity_color(severity: str) -> str:
    """Retorna color para severidad"""
    colors = {
        "critical": "#EF4444",
        "high": "#F59E0B",
        "medium": "#EAB308",
        "low": "#3B82F6",
        "info": "#6B7280"
    }
    return colors.get(severity.lower(), "#6B7280")


# === INICIALIZAR SESSION STATE ===
if "buenobot_current_scan" not in st.session_state:
    st.session_state.buenobot_current_scan = None
if "buenobot_auto_refresh" not in st.session_state:
    st.session_state.buenobot_auto_refresh = False


# === HEADER ===
st.title("🤖 BUENOBOT")
st.markdown("**Quality Assurance & Security Dashboard** - Sistema de control de calidad y seguridad")

# Verificar salud del API
health = api_request("GET", "/health")
if "error" not in health:
    col1, col2, col3 = st.columns(3)
    col1.metric("Estado API", "🟢 Online")
    col2.metric("Scans Activos", health.get("active_scans", 0))
    col3.metric("Checks Disponibles", health.get("checks_available", 0))
else:
    st.error("⚠️ BUENOBOT API no disponible. Verifique que el backend esté corriendo.")
    st.stop()

st.divider()


# === TABS PRINCIPALES ===
tab_scan, tab_history, tab_results, tab_config = st.tabs([
    "🚀 Ejecutar Scan",
    "📋 Historial",
    "📊 Resultados",
    "⚙️ Configuración"
])


# === TAB: EJECUTAR SCAN ===
with tab_scan:
    st.subheader("Iniciar nuevo scan")
    
    col1, col2 = st.columns(2)
    
    with col1:
        environment = st.selectbox(
            "🌍 Entorno",
            options=["dev", "prod"],
            index=0,
            help="Seleccione el entorno a escanear. Dev es más seguro para pruebas."
        )
        
        if environment == "prod":
            st.warning("⚠️ Escanear producción puede afectar el rendimiento. Use con precaución.")
    
    with col2:
        scan_type = st.selectbox(
            "📋 Tipo de Scan",
            options=["quick", "full"],
            index=0,
            format_func=lambda x: "⚡ Quick Scan (~2 min)" if x == "quick" else "🔍 Full Scan (~5-10 min)",
            help="Quick: Health + Lint + Deps + Secrets + Permisos básicos. Full: Todo lo anterior + Tests + Performance + Infra."
        )
    
    # Descripción del scan
    if scan_type == "quick":
        st.info("""
        **Quick Scan incluye:**
        - ✓ Health endpoints
        - ✓ Lint (Ruff)
        - ✓ Vulnerabilidades (pip-audit)
        - ✓ Secrets scan
        - ✓ Validación de permisos
        - ✓ Autenticación endpoints
        - ✓ Conectividad Odoo
        - ✓ Latencia básica
        """)
    else:
        st.info("""
        **Full Scan incluye todo de Quick más:**
        - ✓ Type checking (Mypy)
        - ✓ Import cycles
        - ✓ Bandit security scan
        - ✓ Docker security config
        - ✓ CORS & headers
        - ✓ Docker containers status
        - ✓ Error logs analysis
        - ✓ System resources
        - ✓ Performance completo (P95)
        """)
    
    # Botón ejecutar
    col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 1])
    
    with col_btn1:
        if st.button("🚀 Ejecutar Scan", type="primary", use_container_width=True):
            with st.spinner("Iniciando scan..."):
                result = api_request("POST", "/scan", {
                    "environment": environment,
                    "scan_type": scan_type,
                    "triggered_by": username
                })
                
                if "error" not in result:
                    scan_id = result.get("scan_id")
                    st.session_state.buenobot_current_scan = scan_id
                    st.session_state.buenobot_auto_refresh = True
                    st.success(f"✅ Scan iniciado: **{scan_id}**")
                    st.rerun()
    
    with col_btn2:
        if st.button("🔄 Refrescar", use_container_width=True):
            st.rerun()
    
    # === PROGRESO DEL SCAN ACTUAL ===
    if st.session_state.buenobot_current_scan:
        st.divider()
        st.subheader(f"📡 Scan en progreso: {st.session_state.buenobot_current_scan}")
        
        scan_status = api_request("GET", f"/scan/{st.session_state.buenobot_current_scan}/status")
        
        if "error" not in scan_status:
            status = scan_status.get("status", "unknown")
            gate_status = scan_status.get("gate_status", "unknown")
            progress = scan_status.get("progress", {})
            
            # Gate Status
            if status == "running":
                st.markdown(get_gate_status_html("running", "Scan en ejecución..."), unsafe_allow_html=True)
            else:
                st.markdown(
                    get_gate_status_html(gate_status, scan_status.get("gate_reason", "")), 
                    unsafe_allow_html=True
                )
            
            # Progress bar
            if progress and status == "running":
                total = progress.get("total_checks", 1)
                completed = progress.get("completed_checks", 0)
                current = progress.get("current_check", "")
                percentage = progress.get("percentage", 0)
                
                st.progress(percentage / 100)
                st.caption(f"**{completed}/{total}** checks completados | Actual: **{current}**")
            
            # Logs en tiempo real
            if status == "running":
                with st.expander("📜 Logs en tiempo real", expanded=True):
                    logs_data = api_request("GET", f"/scan/{st.session_state.buenobot_current_scan}/logs?tail=30")
                    logs = logs_data.get("logs", [])
                    
                    log_text = "\n".join(logs[-30:])
                    st.code(log_text, language="bash")
                
                # Auto-refresh
                if st.session_state.buenobot_auto_refresh:
                    time.sleep(2)
                    st.rerun()
            
            # Si terminó
            if status in ["done", "failed", "cancelled"]:
                st.session_state.buenobot_auto_refresh = False
                
                summary = scan_status.get("summary", {})
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("✅ Passed", summary.get("passed", 0))
                col2.metric("❌ Failed", summary.get("failed", 0))
                col3.metric("⚠️ Warnings", summary.get("warnings", 0))
                col4.metric("⏱️ Duración", format_duration(scan_status.get("duration_seconds", 0)))
                
                # Botones de acción
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button("📊 Ver Resultados Completos"):
                        st.session_state.buenobot_view_scan = st.session_state.buenobot_current_scan
                        st.session_state.buenobot_current_scan = None
                with col_b:
                    if st.button("🔄 Re-ejecutar Fallidos"):
                        result = api_request("POST", f"/rerun-failed/{st.session_state.buenobot_current_scan}")
                        if "error" not in result:
                            st.success(result.get("message", "Re-ejecutando..."))
                with col_c:
                    if st.button("✖️ Cerrar"):
                        st.session_state.buenobot_current_scan = None
                        st.rerun()


# === TAB: HISTORIAL ===
with tab_history:
    st.subheader("📋 Historial de Scans")
    
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🔄 Actualizar lista"):
            st.rerun()
    
    scans = api_request("GET", "/scans?limit=20")
    
    if isinstance(scans, list) and len(scans) > 0:
        for scan in scans:
            scan_id = scan.get("scan_id", "")
            status = scan.get("status", "unknown")
            gate = scan.get("gate_status", "unknown")
            env = scan.get("environment", "?")
            scan_type_hist = scan.get("scan_type", "?")
            created = scan.get("created_at", "")
            duration = scan.get("duration_seconds")
            summary = scan.get("summary", "")
            commit = scan.get("commit_sha", "")[:8] if scan.get("commit_sha") else ""
            
            # Emoji de gate
            gate_emoji = {"pass": "✅", "warn": "⚠️", "fail": "❌"}.get(gate, "❓")
            env_emoji = "🧪" if env == "dev" else "🚀"
            type_emoji = "⚡" if scan_type_hist == "quick" else "🔍"
            
            with st.expander(
                f"{gate_emoji} **{scan_id}** | {env_emoji} {env.upper()} | {type_emoji} {scan_type_hist} | {created[:16] if created else 'N/A'}"
            ):
                col1, col2, col3 = st.columns(3)
                col1.write(f"**Status:** {status}")
                col2.write(f"**Duración:** {format_duration(duration) if duration else 'N/A'}")
                col3.write(f"**Commit:** `{commit}`" if commit else "")
                
                st.write(f"**Resumen:** {summary}")
                
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    if st.button(f"📊 Ver", key=f"view_{scan_id}"):
                        st.session_state.buenobot_view_scan = scan_id
                with col_b:
                    if st.button(f"📄 Markdown", key=f"md_{scan_id}"):
                        st.session_state.buenobot_download_scan = scan_id
                with col_c:
                    if st.button(f"🗑️ Eliminar", key=f"del_{scan_id}"):
                        # Implementar si se necesita
                        st.warning("Función no implementada aún")
    else:
        st.info("No hay scans en el historial. Ejecute su primer scan en la pestaña anterior.")


# === TAB: RESULTADOS ===
with tab_results:
    st.subheader("📊 Resultados de Scan")
    
    # Selector de scan
    scan_to_view = st.session_state.get("buenobot_view_scan")
    
    if not scan_to_view:
        # Obtener último scan
        scans = api_request("GET", "/scans?limit=5")
        if isinstance(scans, list) and scans:
            scan_options = {s["scan_id"]: f"{s['scan_id']} - {s.get('gate_status', '?').upper()} - {(s.get('created_at') or '')[:16]}" for s in scans}
            selected = st.selectbox("Seleccionar scan:", options=list(scan_options.keys()), format_func=lambda x: scan_options[x])
            scan_to_view = selected
        else:
            st.info("No hay scans disponibles para mostrar.")
            st.stop()
    
    if scan_to_view:
        scan_data = api_request("GET", f"/scan/{scan_to_view}")
        
        if "error" not in scan_data:
            metadata = scan_data.get("metadata") or {}
            git_info = metadata.get("git_info") or {}
            
            # Header con info del scan
            st.markdown(f"### Scan: `{scan_to_view}`")
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Entorno", (metadata.get("environment") or "?").upper())
            col2.metric("Tipo", metadata.get("scan_type") or "?")
            col3.metric("Duración", format_duration(scan_data.get("duration_seconds") or 0))
            commit_sha = git_info.get("commit_sha") if git_info else None
            col4.metric("Commit", commit_sha[:8] if commit_sha else "N/A")
            
            # Gate Status
            gate_status = scan_data.get("gate_status") or "unknown"
            gate_reason = scan_data.get("gate_reason", "")
            st.markdown(get_gate_status_html(gate_status, gate_reason), unsafe_allow_html=True)
            
            st.divider()
            
            # === CHECKLIST GO/NO-GO ===
            checklist = scan_data.get("checklist", {})
            if checklist:
                st.markdown("### ✅ Checklist Go/No-Go")
                cols = st.columns(3)
                for i, (item, passed) in enumerate(checklist.items()):
                    emoji = "✅" if passed else "❌"
                    cols[i % 3].write(f"{emoji} {item}")
                st.divider()
            
            # === TOP FINDINGS ===
            top_findings = scan_data.get("top_findings", [])
            if top_findings:
                st.markdown("### 🔴 Top Hallazgos")
                for finding in top_findings:
                    severity = finding.get("severity", "info")
                    color = get_severity_color(severity)
                    
                    st.markdown(f"""
                    <div class="finding-{severity}">
                        <strong style="color: {color};">[{severity.upper()}]</strong> {finding.get('title', '')}
                        <br><span style="color: #666;">{finding.get('description', '')}</span>
                        {f"<br><code>{finding.get('location', '')}</code>" if finding.get('location') else ""}
                    </div>
                    """, unsafe_allow_html=True)
                st.divider()
            
            # === RESULTADOS POR CATEGORÍA ===
            st.markdown("### 📁 Resultados por Categoría")
            
            results = scan_data.get("results", {})
            
            for category, checks in results.items():
                category_name = category.replace("_", " ").title()
                
                # Contar estados
                passed = len([c for c in checks if c.get("status") == "passed"])
                failed = len([c for c in checks if c.get("status") == "failed"])
                total = len(checks)
                
                # Color del header según resultados
                if failed > 0:
                    header_color = "🔴"
                elif passed == total:
                    header_color = "🟢"
                else:
                    header_color = "🟡"
                
                with st.expander(f"{header_color} **{category_name}** ({passed}/{total} passed)"):
                    for check in checks:
                        check_name = check.get("check_name", "Unknown")
                        check_status = check.get("status", "unknown")
                        duration_ms = check.get("duration_ms", 0)
                        summary_text = check.get("summary", "")
                        findings = check.get("findings", [])
                        
                        status_emoji = "✅" if check_status == "passed" else "❌" if check_status == "failed" else "⚪"
                        
                        st.markdown(f"**{status_emoji} {check_name}** ({duration_ms}ms)")
                        if summary_text:
                            st.caption(summary_text)
                        
                        if findings:
                            for f in findings[:3]:  # Limitar
                                severity = f.get("severity", "info")
                                st.markdown(
                                    f"<small style='color: {get_severity_color(severity)};'>• [{severity}] {f.get('title', '')}</small>",
                                    unsafe_allow_html=True
                                )
                        st.write("---")
            
            # === RECOMENDACIONES ===
            recommendations = scan_data.get("recommendations", [])
            if recommendations:
                st.markdown("### 💡 Recomendaciones")
                for rec in recommendations:
                    priority = rec.get("priority", "P2")
                    priority_color = {"P0": "🔴", "P1": "🟠", "P2": "🔵"}.get(priority, "⚪")
                    
                    st.markdown(f"**{priority_color} [{priority}] {rec.get('title', '')}**")
                    st.write(rec.get("description", ""))
            
            # === AI ANALYSIS v3.0 ===
            ai_analysis = scan_data.get("ai_analysis", {})
            summary_ai_enabled = scan_data.get("summary", {}).get("ai_enabled", False)
            
            if ai_analysis or summary_ai_enabled:
                st.divider()
                st.markdown("### 🤖 AI Analysis (v3.0)")
                
                if ai_analysis.get("enabled", False):
                    # AI info header
                    ai_cols = st.columns(4)
                    ai_cols[0].metric("🔧 Motor", ai_analysis.get("engine_used", "N/A"))
                    ai_cols[1].metric("📊 Risk Score", f"{ai_analysis.get('risk_score', 0)}/100")
                    ai_cols[2].metric("🎯 Confianza", f"{ai_analysis.get('confidence', 0):.0%}")
                    cached_str = "✓ Cache" if ai_analysis.get("cached") else "Fresh"
                    ai_cols[3].metric("⏱️ Tiempo", f"{ai_analysis.get('analysis_ms', 0)}ms {cached_str}")
                    
                    # Summary
                    if ai_analysis.get("summary"):
                        st.info(f"**Resumen IA:** {ai_analysis.get('summary')}")
                    
                    # Root causes
                    root_causes = ai_analysis.get("root_causes", [])
                    if root_causes:
                        st.markdown("#### 🔍 Root Causes")
                        for rc in root_causes:
                            severity_emoji = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵"}.get(rc.get("severity", "medium"), "⚪")
                            st.markdown(f"**{severity_emoji} {rc.get('cause', '')}**")
                            if rc.get("explanation"):
                                st.caption(rc.get("explanation"))
                    
                    # AI Recommendations
                    ai_recs = ai_analysis.get("recommendations", [])
                    if ai_recs:
                        st.markdown("#### 💡 AI Recommendations")
                        for rec in ai_recs:
                            priority = rec.get("priority", "P2")
                            effort = rec.get("effort", "medium")
                            effort_emoji = {"low": "🟢", "medium": "🟡", "high": "🔴"}.get(effort, "⚪")
                            
                            with st.expander(f"**[{priority}]** {rec.get('title', '')} (Effort: {effort_emoji} {effort})"):
                                st.write(rec.get("description", ""))
                                if rec.get("code_example"):
                                    st.code(rec.get("code_example"), language="python")
                    
                    # Anomalies
                    anomalies = ai_analysis.get("notable_anomalies", [])
                    if anomalies:
                        st.markdown("#### ⚠️ Anomalías Detectadas")
                        st.write(", ".join(f"`{a}`" for a in anomalies))
                    
                    # Re-analyze button
                    col_ai_a, col_ai_b = st.columns(2)
                    with col_ai_a:
                        if st.button("🔄 Re-analizar con IA (Deep)"):
                            with st.spinner("Ejecutando análisis profundo..."):
                                result = api_request("POST", f"/scan/{scan_to_view}/ai/reanalyze?mode=deep&force=true")
                                if "error" not in result:
                                    st.success("Análisis completado. Recarga para ver resultados.")
                                    st.rerun()
                                else:
                                    st.error(f"Error: {result.get('error', result.get('detail', 'Unknown'))}")
                    
                elif ai_analysis.get("skipped_reason"):
                    st.warning(f"AI Analysis omitido: {ai_analysis.get('skipped_reason')}")
                elif ai_analysis.get("error"):
                    st.error(f"AI Analysis error: {ai_analysis.get('error')}")
                else:
                    st.info("AI Analysis no disponible para este scan. Puedes ejecutarlo manualmente:")
                    if st.button("🤖 Ejecutar AI Analysis"):
                        with st.spinner("Analizando con IA..."):
                            result = api_request("POST", f"/scan/{scan_to_view}/ai/reanalyze?mode=basic")
                            if "error" not in result:
                                st.success("Análisis completado. Recarga para ver resultados.")
                                st.rerun()
                            else:
                                st.error(f"Error: {result.get('error', result.get('detail', 'Unknown'))}")
            
            # === DESCARGAR REPORTE ===
            st.divider()
            col1, col2 = st.columns(2)
            
            with col1:
                # JSON
                json_str = json.dumps(scan_data, indent=2, default=str)
                st.download_button(
                    "📥 Descargar JSON",
                    data=json_str,
                    file_name=f"buenobot_scan_{scan_to_view}.json",
                    mime="application/json"
                )
            
            with col2:
                # Markdown
                md_response = requests.get(f"{BUENOBOT_API}/scan/{scan_to_view}/report?format=markdown")
                if md_response.status_code == 200:
                    st.download_button(
                        "📥 Descargar Markdown",
                        data=md_response.text,
                        file_name=f"buenobot_scan_{scan_to_view}.md",
                        mime="text/markdown"
                    )


# === TAB: CONFIGURACIÓN ===
with tab_config:
    st.subheader("⚙️ Configuración de BUENOBOT")
    
    st.markdown("### Checks Disponibles")
    
    checks = api_request("GET", "/checks")
    
    if isinstance(checks, list):
        # Agrupar por categoría
        by_category = {}
        for check in checks:
            cat = check.get("category", "other")
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(check)
        
        for category, cat_checks in sorted(by_category.items()):
            category_name = category.replace("_", " ").title()
            with st.expander(f"📁 **{category_name}** ({len(cat_checks)} checks)"):
                for check in cat_checks:
                    quick = "⚡" if check.get("in_quick") else ""
                    full = "🔍" if check.get("in_full") else ""
                    
                    st.markdown(f"""
                    **{check.get('name', '')}** {quick}{full}
                    - ID: `{check.get('id', '')}`
                    - {check.get('description', '')}
                    """)
    
    st.divider()
    
    st.markdown("### Información del Sistema")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **API Endpoint:** `{BUENOBOT_API}`
        
        **Usuario actual:** {username}
        """)
    
    with col2:
        if health and "error" not in health:
            st.success(f"""
            **Scans totales:** {health.get('total_scans', 'N/A')}
            
            **Checks disponibles:** {health.get('checks_available', 'N/A')}
            """)
    
    # === AI CONFIGURATION v3.0 ===
    st.divider()
    st.markdown("### 🤖 AI Engine Configuration (v3.0)")
    
    ai_config = api_request("GET", "/ai/config")
    
    if isinstance(ai_config, dict) and "error" not in ai_config:
        col_ai1, col_ai2 = st.columns(2)
        
        with col_ai1:
            ai_enabled = ai_config.get("ai_enabled", False)
            status_emoji = "✅" if ai_enabled else "❌"
            st.markdown(f"**Estado:** {status_emoji} {'Habilitado' if ai_enabled else 'Deshabilitado'}")
            st.markdown(f"**Motor por defecto:** `{ai_config.get('default_engine', 'N/A')}`")
            st.markdown(f"**OpenAI configurado:** {'✓' if ai_config.get('openai_configured') else '✗'}")
            if ai_config.get("openai_configured"):
                st.markdown(f"**Modelo OpenAI:** `{ai_config.get('openai_model', 'N/A')}`")
        
        with col_ai2:
            st.markdown(f"**Motor local URL:** `{ai_config.get('local_engine_url', 'N/A')}`")
            st.markdown(f"**Motor local modo:** `{ai_config.get('local_engine_mode', 'N/A')}`")
            st.markdown(f"**Cache habilitado:** {'✓' if ai_config.get('cache_enabled') else '✗'}")
            st.markdown(f"**Max findings a IA:** {ai_config.get('max_findings_to_ai', 'N/A')}")
        
        # === CONFIGURAR OpenAI ===
        st.markdown("---")
        st.markdown("#### 🔑 Configurar OpenAI API")
        
        with st.expander("⚙️ Habilitar/Configurar OpenAI", expanded=not ai_config.get("openai_configured", False)):
            st.info("""
            **¿Cómo obtener una API Key?**
            1. Ve a [platform.openai.com](https://platform.openai.com)
            2. Inicia sesión o crea cuenta
            3. Ve a API Keys → Create new secret key
            4. Copia la key aquí
            """)
            
            with st.form("openai_config_form"):
                new_api_key = st.text_input(
                    "OpenAI API Key",
                    type="password",
                    placeholder="sk-...",
                    help="Tu API key de OpenAI (sk-...)"
                )
                
                new_model = st.selectbox(
                    "Modelo",
                    options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                    index=0,
                    help="gpt-4o-mini es rápido y económico, gpt-4o es más potente"
                )
                
                enable_ai = st.checkbox(
                    "Habilitar AI Analysis automático",
                    value=ai_enabled,
                    help="Cuando está habilitado, cada scan ejecuta análisis IA automáticamente"
                )
                
                submitted = st.form_submit_button("💾 Guardar Configuración", type="primary")
                
                if submitted:
                    if new_api_key or enable_ai != ai_enabled:
                        config_data = {
                            "ai_enabled": enable_ai,
                        }
                        if new_api_key:
                            config_data["openai_api_key"] = new_api_key
                            config_data["openai_model"] = new_model
                            config_data["default_engine"] = "openai"
                        
                        result = api_request("POST", "/ai/config", config_data)
                        if "error" not in result:
                            st.success("✅ Configuración guardada exitosamente")
                            st.rerun()
                        else:
                            st.error(f"Error: {result.get('error', result.get('detail', 'Unknown'))}")
                    else:
                        st.warning("No hay cambios para guardar")
        
        # Test OpenAI connection
        if ai_config.get("openai_configured"):
            if st.button("🧪 Probar conexión OpenAI"):
                with st.spinner("Probando conexión..."):
                    test_result = api_request("POST", "/ai/test")
                    if "error" not in test_result and test_result.get("success"):
                        st.success(f"✅ Conexión exitosa! Modelo: {test_result.get('model')}, Latencia: {test_result.get('latency_ms')}ms")
                    else:
                        st.error(f"❌ Error de conexión: {test_result.get('error', 'Unknown')}")
        
        # Cache stats
        cache_stats = api_request("GET", "/ai/cache/stats")
        if isinstance(cache_stats, dict) and cache_stats.get("enabled"):
            st.markdown("#### 📦 Cache Stats")
            cache_cols = st.columns(4)
            cache_cols[0].metric("Entradas", cache_stats.get("total_entries", 0))
            cache_cols[1].metric("Tamaño", f"{cache_stats.get('total_size_kb', 0):.1f} KB")
            cache_cols[2].metric("Expiradas", cache_stats.get("expired", 0))
            cache_cols[3].metric("TTL", f"{cache_stats.get('ttl_hours', 0)}h")
            
            if st.button("🗑️ Limpiar Cache"):
                result = api_request("POST", "/ai/cache/clear")
                if "error" not in result:
                    st.success(f"Cache limpiado: {result.get('cleared', 0)} entradas")
                    st.rerun()
    else:
        st.warning("No se pudo obtener configuración de AI")


# === FOOTER ===
st.divider()
st.caption("🤖 BUENOBOT v3.0.0 - Quality Assurance & Security con AI híbrida para Rio Futuro Dashboards")
