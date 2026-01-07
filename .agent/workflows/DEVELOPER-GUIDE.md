# 🎯 Contexto para Desarrolladores - Rio Futuro Dashboards

**Última actualización**: 2026-01-07

---

## 📋 PROMPT INICIAL

Eres un desarrollador senior trabajando en el proyecto **Rio Futuro Dashboards**, una plataforma de análisis empresarial para industria alimentaria (arándanos). El sistema gestiona producción, finanzas, logística y comercial integrándose con Odoo 16 ERP.

**Tu misión**: Implementar nuevas funcionalidades siguiendo los estándares existentes de modularización, optimización y experiencia de usuario.

---

## 🏗️ ARQUITECTURA DEL PROYECTO

### Stack Tecnológico

```
Frontend:  Streamlit 1.52.2
Backend:   FastAPI 0.128.0 + Uvicorn
Database:  Odoo 16 (XML-RPC)
Deploy:    Docker (Blue-Green) + NGINX
Server:    debian@167.114.114.51
```

### Estructura de Capas

```
┌─────────────────────────────────────────┐
│  FRONTEND (Streamlit)                   │
│  - pages/*.py (11 dashboards)           │
│  - Tabs modularizados en subdirectorios │
│  - Componentes reutilizables            │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
┌──────────────▼──────────────────────────┐
│  BACKEND (FastAPI)                      │
│  - routers/ (16 endpoints)              │
│  - services/ (22 servicios de negocio)  │
│  - cache.py (Redis-style caching)       │
└──────────────┬──────────────────────────┘
               │ XML-RPC
┌──────────────▼──────────────────────────┐
│  ODOO 16 ERP                            │
│  - Modelos de negocio                   │
│  - Datos transaccionales                │
└─────────────────────────────────────────┘
```

---

## 📐 ESTÁNDARES DE CÓDIGO

### 1. Modularización

**OBLIGATORIO**: Cada dashboard debe tener tabs separados

```python
# ❌ MAL - Todo en un archivo
# pages/1_Recepciones.py (500 líneas)

# ✅ BIEN - Tabs modularizados
pages/
  1_Recepciones.py              # Orquestador (50 líneas)
  recepciones/
    __init__.py
    shared.py                    # Funciones comunes
    tab_kpis.py                  # Tab específico
    tab_curva.py                 # Tab específico
    tab_gestion.py               # Tab específico
```

**Ejemplo de implementación**:

```python
# pages/1_Recepciones.py
import streamlit as st
from recepciones import tab_kpis, tab_curva, tab_gestion

st.set_page_config(page_title="Recepciones", layout="wide")

# Tabs
tab1, tab2, tab3 = st.tabs(["📊 KPIs", "📈 Curva", "⚙️ Gestión"])

with tab1:
    tab_kpis.render()

with tab2:
    tab_curva.render()

with tab3:
    tab_gestion.render()
```

```python
# pages/recepciones/tab_kpis.py
import streamlit as st
import httpx
from .shared import format_currency, get_api_url

def render():
    """Renderiza el tab de KPIs"""
    st.header("KPIs de Recepciones")
    
    # Fetch data
    data = fetch_kpi_data()
    
    # Mostrar métricas
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Kg", f"{data['total_kg']:,.0f}")
    # ...
    
def fetch_kpi_data():
    """Obtiene datos del backend"""
    response = httpx.get(f"{get_api_url()}/api/v1/recepcion/kpis")
    return response.json()
```

### 2. Backend Services

**Patrón**: Router → Service → Odoo

```python
# backend/routers/recepcion.py
from fastapi import APIRouter
from ..services import recepcion_service

router = APIRouter(prefix="/api/v1/recepcion", tags=["recepcion"])

@router.get("/kpis")
async def get_kpis(fecha_inicio: str, fecha_fin: str):
    """Endpoint para KPIs - Solo orquestación"""
    return await recepcion_service.calcular_kpis(fecha_inicio, fecha_fin)
```

```python
# backend/services/recepcion_service.py
from shared.odoo_client import get_odoo_connection

async def calcular_kpis(fecha_inicio: str, fecha_fin: str):
    """Lógica de negocio - Aquí va la complejidad"""
    odoo = get_odoo_connection()
    
    # 1. Obtener datos de Odoo
    recepciones = odoo.execute_kw(
        'stock.picking',
        'search_read',
        [[['date', '>=', fecha_inicio], ['date', '<=', fecha_fin]]],
        {'fields': ['name', 'product_qty', 'price_unit']}
    )
    
    # 2. Procesar datos
    total_kg = sum(r['product_qty'] for r in recepciones)
    costo_promedio = sum(r['price_unit'] for r in recepciones) / len(recepciones)
    
    # 3. Retornar resultado estructurado
    return {
        "total_kg": total_kg,
        "costo_promedio": costo_promedio,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
```

### 3. Optimización y Caché

**SIEMPRE** cachear datos de Odoo:

```python
# backend/services/rendimiento_service.py
from ..cache import get_cache, set_cache
import hashlib

async def obtener_rendimientos(params: dict):
    """Servicio con caché"""
    
    # 1. Generar cache key
    cache_key = f"rendimientos_{hashlib.md5(str(params).encode()).hexdigest()}"
    
    # 2. Intentar obtener de caché
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    # 3. Si no existe, consultar Odoo
    odoo = get_odoo_connection()
    data = odoo.execute_kw(...)  # Query costoso
    
    # 4. Procesar datos
    resultado = procesar_rendimientos(data)
    
    # 5. Guardar en caché (5 minutos)
    set_cache(cache_key, resultado, ttl=300)
    
    return resultado
```

---

## 🎨 ESTÁNDARES VISUALES

### 1. Layout Consistente

```python
import streamlit as st

# ✅ SIEMPRE: Layout wide
st.set_page_config(
    page_title="Nombre Dashboard",
    page_icon="🔥",
    layout="wide"
)

# ✅ Header con descripción
st.title("📊 Nombre del Dashboard")
st.markdown("Descripción breve del propósito del dashboard")

# ✅ Sidebar para filtros
with st.sidebar:
    st.header("Filtros")
    fecha_inicio = st.date_input("Fecha Inicio")
    fecha_fin = st.date_input("Fecha Fin")
```

### 2. Paleta de Colores

```python
# Definir en shared/constants.py
COLORS = {
    "primary": "#1f77b4",      # Azul
    "success": "#2ca02c",       # Verde
    "warning": "#ff7f0e",       # Naranja
    "danger": "#d62728",        # Rojo
    "info": "#17becf",          # Cyan
    "neutral": "#7f7f7f",       # Gris
}

# Usar en gráficos
import plotly.graph_objects as go
from shared.constants import COLORS

fig = go.Figure()
fig.add_trace(go.Bar(
    x=dates,
    y=values,
    marker_color=COLORS["primary"]
))
```

### 3. Métricas con Delta

```python
# ✅ Mostrar cambios vs periodo anterior
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="Kg Recepcionados",
        value=f"{kg_actual:,.0f}",
        delta=f"{delta_kg:+,.0f}",
        delta_color="normal"  # "normal", "inverse", "off"
    )
```

### 4. Gráficos Interactivos

```python
import plotly.express as px

# ✅ SIEMPRE: Plotly (no matplotlib)
# Razón: Interactivo, responsive, mejor UX

fig = px.line(
    df,
    x="fecha",
    y="valor",
    title="Evolución Temporal",
    labels={"fecha": "Fecha", "valor": "Valor (USD)"}
)

# Configuración estándar
fig.update_layout(
    hovermode="x unified",
    showlegend=True,
    height=400,
    margin=dict(l=0, r=0, t=40, b=0)
)

st.plotly_chart(fig, use_container_width=True)
```

### 5. Tablas de Datos

```python
import pandas as pd

# ✅ Para tablas simples
st.dataframe(
    df,
    use_container_width=True,
    height=400,
    hide_index=True
)

# ✅ Para tablas con formato
st.dataframe(
    df.style
        .format({"precio": "${:,.2f}", "cantidad": "{:,.0f}"})
        .background_gradient(subset=["rendimiento"], cmap="RdYlGn")
)
```

---

## 🚀 PROCESO DE DESARROLLO

### Flujo Estándar

```
1. ANÁLISIS
   ├─ Entender requerimiento
   ├─ Definir datos necesarios de Odoo
   └─ Diseñar estructura de tabs

2. BACKEND PRIMERO
   ├─ Crear servicio en services/
   ├─ Crear endpoint en routers/
   ├─ Implementar caché
   └─ Probar con curl/Postman

3. FRONTEND
   ├─ Crear estructura modular
   ├─ Implementar tabs
   ├─ Conectar con backend
   └─ Aplicar estándares visuales

4. TESTING
   ├─ Probar en DEV
   ├─ Verificar performance
   ├─ Validar con usuarios
   └─ Deploy a PROD
```

### Checklist de Código

```
Backend:
□ Servicio separado en services/
□ Endpoint en routers/
□ Caché implementado
□ Manejo de errores con try/except
□ Logging apropiado
□ Type hints en funciones
□ Docstrings en funciones públicas

Frontend:
□ Tabs modularizados
□ Funciones compartidas en shared.py
□ Layout wide configurado
□ Sidebar para filtros
□ Métricas con delta
□ Gráficos con Plotly
□ Tablas formateadas
□ Loading states (st.spinner)
□ Manejo de errores (st.error)

Performance:
□ Queries optimizadas a Odoo
□ Caché en datos estáticos
□ @st.cache_data en funciones pesadas
□ Evitar loops innecesarios
□ DataFrames optimizados (no append en loops)
```

---

## 📊 PATRONES COMUNES

### Pattern 1: Dashboard con KPIs + Gráfico + Tabla

```python
# pages/X_MiDashboard.py
import streamlit as st
from mi_dashboard import tab_resumen, tab_detalle

st.set_page_config(page_title="Mi Dashboard", layout="wide")

tab1, tab2 = st.tabs(["📊 Resumen", "📋 Detalle"])

with tab1:
    tab_resumen.render()
    
with tab2:
    tab_detalle.render()
```

```python
# pages/mi_dashboard/tab_resumen.py
import streamlit as st
import httpx
import plotly.express as px
from .shared import get_api_url, format_number

@st.cache_data(ttl=300)
def fetch_data(fecha_inicio, fecha_fin):
    response = httpx.get(
        f"{get_api_url()}/api/v1/mi-endpoint/resumen",
        params={"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}
    )
    return response.json()

def render():
    st.header("📊 Resumen")
    
    # Filtros en sidebar
    with st.sidebar:
        fecha_inicio = st.date_input("Desde")
        fecha_fin = st.date_input("Hasta")
    
    # Cargar datos
    with st.spinner("Cargando datos..."):
        data = fetch_data(str(fecha_inicio), str(fecha_fin))
    
    # KPIs
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Métrica 1", format_number(data["kpi1"]))
    with col2:
        st.metric("Métrica 2", format_number(data["kpi2"]))
    # ...
    
    # Gráfico
    st.subheader("Evolución Temporal")
    fig = px.line(data["grafico"], x="fecha", y="valor")
    st.plotly_chart(fig, use_container_width=True)
    
    # Tabla
    st.subheader("Detalle por Categoría")
    st.dataframe(data["tabla"], use_container_width=True)
```

### Pattern 2: Filtros Dinámicos

```python
# Filtros que dependen unos de otros
proveedores = st.multiselect("Proveedores", options=lista_proveedores)

# Filtrar categorías según proveedores seleccionados
categorias_filtradas = obtener_categorias(proveedores)
categorias = st.multiselect("Categorías", options=categorias_filtradas)

# Aplicar filtros al backend
data = fetch_data(proveedores=proveedores, categorias=categorias)
```

### Pattern 3: Descarga de Reportes

```python
import io
import pandas as pd

# Botón de descarga Excel
df = pd.DataFrame(data)
buffer = io.BytesIO()

with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    df.to_excel(writer, index=False, sheet_name='Datos')

st.download_button(
    label="📥 Descargar Excel",
    data=buffer.getvalue(),
    file_name=f"reporte_{fecha_inicio}_{fecha_fin}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
```

---

## 🔧 CONFIGURACIÓN Y VARIABLES

### Variables de Entorno

```python
# shared/constants.py
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
ENV = os.getenv("ENV", "development")

# Odoo connection
ODOO_URL = os.getenv("ODOO_URL", "https://odoo.riofuturo.com")
ODOO_DB = os.getenv("ODOO_DB", "riofuturo")
```

### Configuración de Página

```python
# Siempre al inicio del archivo
st.set_page_config(
    page_title="Nombre Dashboard",
    page_icon="🔥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Hide Streamlit branding
hide_streamlit_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
```

---

## 🎯 EJEMPLOS ESPECÍFICOS

### Agregar Nuevo Dashboard

```bash
# 1. Crear estructura
pages/
  12_NuevoDashboard.py
  nuevo_dashboard/
    __init__.py
    shared.py
    tab_resumen.py
    tab_detalle.py
```

```python
# 2. Implementar orquestador (12_NuevoDashboard.py)
import streamlit as st
from shared.auth import require_auth
from nuevo_dashboard import tab_resumen, tab_detalle

require_auth()  # Proteger con autenticación

st.set_page_config(page_title="Nuevo Dashboard", layout="wide")
st.title("🔥 Nuevo Dashboard")

tab1, tab2 = st.tabs(["📊 Resumen", "📋 Detalle"])

with tab1:
    tab_resumen.render()
    
with tab2:
    tab_detalle.render()
```

```python
# 3. Crear backend service (backend/services/nuevo_service.py)
from shared.odoo_client import get_odoo_connection
from ..cache import get_cache, set_cache

async def obtener_resumen(params: dict):
    cache_key = f"nuevo_resumen_{params}"
    
    cached = get_cache(cache_key)
    if cached:
        return cached
    
    odoo = get_odoo_connection()
    
    # Query a Odoo
    data = odoo.execute_kw(
        'mi.modelo',
        'search_read',
        [[['fecha', '>=', params['fecha_inicio']]]],
        {'fields': ['campo1', 'campo2']}
    )
    
    # Procesar
    resultado = procesar_data(data)
    
    set_cache(cache_key, resultado, ttl=300)
    return resultado
```

```python
# 4. Crear endpoint (backend/routers/nuevo.py)
from fastapi import APIRouter
from ..services import nuevo_service

router = APIRouter(prefix="/api/v1/nuevo", tags=["nuevo"])

@router.get("/resumen")
async def get_resumen(fecha_inicio: str, fecha_fin: str):
    params = {"fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin}
    return await nuevo_service.obtener_resumen(params)
```

```python
# 5. Registrar router (backend/main.py)
from .routers import nuevo

app.include_router(nuevo.router)
```

### Agregar Tab a Dashboard Existente

```python
# 1. Crear archivo de tab
# pages/recepciones/tab_nuevo.py

import streamlit as st

def render():
    st.header("Nuevo Tab")
    # ... implementación
```

```python
# 2. Importar en orquestador
# pages/1_Recepciones.py

from recepciones import tab_kpis, tab_curva, tab_gestion, tab_nuevo

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 KPIs",
    "📈 Curva",
    "⚙️ Gestión",
    "🆕 Nuevo"  # <-- Agregar aquí
])

with tab4:
    tab_nuevo.render()
```

---

## ⚠️ ERRORES COMUNES A EVITAR

### 1. No Cachear Datos

```python
# ❌ MAL - Consulta en cada rerun
def render():
    data = httpx.get(f"{API_URL}/api/data").json()
    st.dataframe(data)

# ✅ BIEN - Cachear resultado
@st.cache_data(ttl=300)
def fetch_data():
    return httpx.get(f"{API_URL}/api/data").json()

def render():
    data = fetch_data()
    st.dataframe(data)
```

### 2. Lógica de Negocio en Frontend

```python
# ❌ MAL - Cálculos complejos en Streamlit
recepciones = fetch_recepciones()
rendimiento = sum(r['output'] for r in recepciones) / sum(r['input'] for r in recepciones)

# ✅ BIEN - Cálculos en backend
rendimiento = httpx.get(f"{API_URL}/api/rendimiento").json()
```

### 3. No Modularizar

```python
# ❌ MAL - Todo en un archivo de 500 líneas
# pages/1_Recepciones.py con todos los tabs inline

# ✅ BIEN - Tabs en archivos separados
# pages/1_Recepciones.py (orquestador)
# pages/recepciones/tab_kpis.py
# pages/recepciones/tab_curva.py
```

### 4. Queries Ineficientes

```python
# ❌ MAL - Query por cada item
for item_id in item_ids:
    item = odoo.execute_kw('product.product', 'read', [item_id])
    # procesar...

# ✅ BIEN - Una sola query
items = odoo.execute_kw(
    'product.product',
    'search_read',
    [[['id', 'in', item_ids]]],
    {'fields': ['name', 'price']}
)
```

### 5. No Manejar Errores

```python
# ❌ MAL - Sin try/except
data = httpx.get(f"{API_URL}/api/data").json()

# ✅ BIEN - Manejar errores
try:
    response = httpx.get(f"{API_URL}/api/data", timeout=10.0)
    response.raise_for_status()
    data = response.json()
except httpx.HTTPError as e:
    st.error(f"Error conectando al servidor: {e}")
    st.stop()
```

---

## 📚 RECURSOS Y REFERENCIAS

### Documentación

- **Streamlit**: https://docs.streamlit.io
- **FastAPI**: https://fastapi.tiangolo.com
- **Plotly**: https://plotly.com/python
- **Pandas**: https://pandas.pydata.org

### Archivos Clave del Proyecto

```
.agent/workflows/
  ├─ DASHBOARD_STRUCTURE.md       # Estructura completa
  ├─ project-structure.md          # Arquitectura
  ├─ debugging.md                  # Debugging guide
  ├─ docker-deployment.md          # Deploy completo
  ├─ DEPLOYMENT-QUICKSTART.md      # Deploy rápido
  └─ EJEMPLO-DEPLOY.md             # Ejemplo paso a paso
```

### Módulos de Referencia

**Bien implementados** (úsalos como referencia):
- `pages/11_Relacion_Comercial.py` - Modularización perfecta
- `backend/services/flujo_caja_service.py` - Caché y optimización
- `pages/finanzas/tab_flujo_caja.py` - Visualizaciones complejas

---

## ✅ CHECKLIST FINAL

Antes de hacer commit:

```
Código:
□ Sigue estructura modular
□ Backend service + router creados
□ Frontend tabs separados
□ Caché implementado donde corresponde
□ Type hints agregados
□ Docstrings en funciones públicas
□ Sin print statements (usar logging)
□ Manejo de errores con try/except

Visualización:
□ Layout wide configurado
□ Paleta de colores consistente
□ Gráficos con Plotly (no matplotlib)
□ Métricas con deltas apropiados
□ Tablas formateadas
□ Loading states implementados

Performance:
□ Queries a Odoo optimizados
□ @st.cache_data en funciones fetch
□ Sin loops innecesarios
□ DataFrames construidos eficientemente

Testing:
□ Probado en DEV
□ Sin errores en logs
□ Performance aceptable (<3s carga)
□ Responsive en móvil

Deploy:
□ Commit con mensaje descriptivo
□ Push a GitHub
□ Deploy a DEV y verificado
□ Deploy a PROD solo si DEV OK
```

---

## 🎓 ONBOARDING RÁPIDO

### Día 1: Setup

```bash
# 1. Clonar repo
git clone https://github.com/mvalladares1/proyectos.git
cd proyectos

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar .env
cp .env.example .env
# Editar con credenciales

# 4. Correr localmente
streamlit run Home.py
```

### Día 2: Explorar

- Leer `.agent/workflows/DASHBOARD_STRUCTURE.md`
- Revisar un dashboard existente (ej: 11_Relacion_Comercial.py)
- Ver cómo se estructura backend/routers y backend/services
- Probar hacer cambios menores en DEV

### Día 3: Primera Funcionalidad

- Agregar un tab nuevo a un dashboard existente
- Crear endpoint backend simple
- Implementar caché
- Deploy a DEV

---

## 🚀 COMIENZA AQUÍ

**Tu primera tarea**:

1. Lee este documento completo
2. Revisa `pages/11_Relacion_Comercial.py` como ejemplo
3. Explora `backend/services/comercial_service.py`
4. Haz un cambio menor (agregar un campo a una tabla)
5. Sigue el proceso: Backend → Frontend → DEV → PROD

**Cuando tengas dudas**:
- Consulta `.agent/workflows/` (documentación completa)
- Busca ejemplos en código existente
- Pregunta antes de inventar patterns nuevos

**Recuerda**: Consistencia > Creatividad. Sigue los patterns existentes.

---

**¡Bienvenido al equipo! 🚀**
