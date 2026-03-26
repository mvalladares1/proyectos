# PROMPT COMPLETO PARA MIGRACIÓN — Dashboard de Producción (Rio Futuro)

> **Fecha de extracción:** 13 de marzo de 2026
> **Tecnología actual:** Streamlit (Python frontend) + FastAPI (Python backend) + Odoo ERP (XML-RPC)
> **Objetivo:** Recrear 1:1 el Dashboard de Producción en un nuevo framework/aplicación.

---

## 1. VISIÓN GENERAL DEL SISTEMA

### 1.1 Arquitectura Actual
```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│   FRONTEND          │     │    BACKEND API       │     │   ODOO ERP          │
│   (Streamlit)       │────▶│    (FastAPI)          │────▶│   (XML-RPC)         │
│   Puerto 8501       │     │    Puerto 8000       │     │   Cloud Hosted      │
│                     │     │                      │     │                     │
│  - 2_Produccion.py  │     │  - /api/v1/produccion│     │  - mrp.production   │
│  - produccion/      │     │  - /api/v1/rendimiento│    │  - stock.move.line  │
│    └ 14 archivos    │     │  - /api/v1/etiquetas │     │  - stock.quant.pack │
│                     │     │  - /api/v1/automat.  │     │  - product.product  │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

### 1.2 Stack Tecnológico
- **Frontend:** Streamlit >= 1.35.0 (Python)
- **Backend:** FastAPI >= 0.104.0 (Python)
- **ERP:** Odoo (instancia: `https://riofuturo.server98c6e.oerpondemand.net`, BD: `riofuturo-master`)
- **Conexión ERP:** XML-RPC (`xmlrpc.client`)
- **Gráficos frontend:** Plotly, Altair, ECharts (via `streamlit-echarts`)
- **Tablas:** Pandas DataFrames renderizados con `st.dataframe()`
- **PDF:** reportlab, fpdf, PyPDF2
- **HTTP:** httpx + requests
- **Cache:** `@st.cache_data(ttl=...)` en frontend, diskcache en backend
- **Auth:** Tokens de sesión con cookies, validación contra backend

### 1.3 Estructura del Módulo Producción
El dashboard de Producción es una aplicación multi-tab con **7 tabs principales**, cada uno en su archivo:

| Tab | Archivo | Tamaño | Descripción |
|-----|---------|--------|-------------|
| 📊 Reportería General | `tab_reporteria.py` (53 KB) | Principal | KPIs consolidados, volumen de masa, gráficos por sala/túnel |
| 📋 Detalle de OF | `tab_detalle.py` (25 KB) | Sub-tabs internos | Lista OFs con filtros, sub-tab Monitor Diario, Kg por Línea, Pallets Disponibles |
| 📦 Clasificación | `tab_clasificacion.py` (23 KB) | | Clasificación de pallets por categoría/producto |
| 🏢 Pallets por Sala | `tab_pallets_por_sala.py` (57 KB) | | Distribución de pallets en salas de proceso |
| 🏷️ Etiquetas | `tab_etiquetas.py` (46 KB) | Siempre visible | Generación y gestión de etiquetas de pallet |
| 🔍 Trazabilidad | `tab_trazabilidad.py` (29 KB) | Siempre visible | Trazabilidad de lotes PT → MP, visualización de grafos |
| ⚙️ Automatización OF | `tab_automatizacion_of.py` (16 KB) | Permiso especial | Automatización con pallets para órdenes de fabricación |

**Archivos de soporte:**
| Archivo | Tamaño | Función |
|---------|--------|---------|
| `shared.py` (15 KB) | Módulo compartido | Constantes, API calls, formateo, session state, gráficos base |
| `graficos.py` (33 KB) | Módulo de gráficos | Gráficos Altair complejos (salas, túneles, congelado, vaciado) |
| `tab_monitor_diario.py` (44 KB) | Sub-tab | Monitor de producción en tiempo real |
| `tab_kg_por_linea.py` (164 KB) | Sub-tab | Detalle masivo de kg por línea de producción |
| `tab_pallets_disponibles.py` (20 KB) | Sub-tab | Pallets disponibles para despacho |
| `sidebar_trigger.py` (2 KB) | Sidebar helper | Trigger para SO asociada |

---

## 2. SISTEMA DE AUTENTICACIÓN Y PERMISOS

### 2.1 Flujo de Autenticación
1. El usuario ingresa email + API Key de Odoo
2. Se crea sesión con token via `POST /api/v1/auth/validate`
3. Token se almacena en: `st.session_state`, `query_params`, y cookies del navegador
4. Cada request al backend incluye `username` y `password` como query params
5. El backend autentica cada request contra Odoo via XML-RPC

### 2.2 Sistema de Permisos
```python
# Permisos por dashboard (lista vacía = todos tienen acceso)
"produccion": []  # Todos los usuarios autenticados

# Permisos por página/tab específica
"produccion.reporteria_general": []    # Todos
"produccion.detalle_of": []            # Todos
"produccion.clasificacion": []         # Todos
"produccion.automatizacion_of": []     # Todos
```

### 2.3 Construction Dinámica de Tabs
Los tabs se construyen dinámicamente según permisos:
```python
# Tabs condicionales por permiso
if tiene_acceso_pagina("produccion", "reporteria_general"):
    tabs.append("reporteria")
if tiene_acceso_pagina("produccion", "detalle_of"):
    tabs.append("detalle")
if tiene_acceso_pagina("produccion", "clasificacion"):
    tabs.append("clasificacion")
    tabs.append("pallets_sala")  # Usa el mismo permiso que clasificación
# Siempre visibles:
tabs.append("etiquetas")
tabs.append("trazabilidad")
# Permiso especial:
if tiene_acceso_pagina("produccion", "automatizacion_of"):
    tabs.append("automatizacion")
```

---

## 3. TAB 1: REPORTERÍA GENERAL (tab_reporteria.py)

### 3.1 Controles/Filtros Superiores
1. **Selector de Período** (radio horizontal):
   - `📆 Última Semana` → hoy - 7 días a hoy (inputs ocultos)
   - `📊 Acumulado Temporada` → desde 20/Nov del año anterior hasta hoy (inputs ocultos)
   - `📅 Período Personalizado` → muestra dos date_inputs (Desde/Hasta, formato DD/MM/YYYY)
   
   **Lógica de temporada:** si hoy >= 20 de noviembre → inicio_temporada = 20/Nov del año actual; sino → 20/Nov del año anterior

2. **Checkbox "Solo fabricaciones terminadas (done)"** → `value=True` por defecto

3. **Filtro de Planta** (2 checkboxes):
   - `☑ RFP` (Río Futuro Procesos)
   - `☑ VILKUN`
   - Lógica: MOs con nombre que empieza con "VLK" → VILKUN; resto → RIO FUTURO

4. **Agrupación de Gráficos** (radio horizontal): Día | **Semana** (default) | Mes

5. **Botón "🔄 Consultar Reportería"** (type=primary) — dispara la consulta

### 3.2 Llamada API Principal
```
GET /api/v1/rendimiento/dashboard
  ?username=...&password=...&fecha_inicio=YYYY-MM-DD&fecha_fin=YYYY-MM-DD&solo_terminadas=true
  Timeout: 180s
  Cache TTL: 120s
```

**Respuesta (estructura `dashboard`):**
```json
{
  "overview": {
    "total_mos": 150,
    "kg_mp_total": 500000.0,
    "kg_pt_total": 350000.0,
    "rendimiento_general": 70.0,
    "frutas": [...],
    "manejos": [...]
  },
  "consolidado": {
    "por_fruta": [...],
    "por_manejo": [...]
  },
  "salas": [...],
  "mos": [
    {
      "mo_id": 12345,
      "mo_name": "RF/P26M/00001",
      "fecha": "2026-01-15",
      "producto": "Cereza IQF",
      "especie": "Cereza",
      "manejo": "IQF",
      "kg_mp": 5000.0,
      "kg_pt": 3500.0,
      "rendimiento": 70.0,
      "sala": "Sala 1",
      "sala_tipo": "PROCESO" | "CONGELADO",
      "sala_name": "...",
      "dotacion": 15,
      "hh_efectiva": 120.0,
      "kg_hh": 29.2,
      "estado": "done",
      "planta": "RIO FUTURO",
      "product_name": "..."
    }
  ]
}
```

### 3.3 Sección "Volumen de Masa" (función `_render_volumen_masa`)
- **4 KPIs en fila:**
  - 📦 Kg MP Total
  - 📤 Kg PT Total
  - 🏭 Kg Proceso (filtra por `sala_tipo == "PROCESO"`)
  - ❄️ Kg Congelado (filtra por `sala_tipo == "CONGELADO"`)
  - Formateo: separador de miles con punto (chileno): `1.234.567`

- **2 Tabs internos**: "🏭 Salas (Proceso)" y "❄️ Túneles (Congelado)"

- **Gráfico de Barras Apiladas por Sala** (Plotly):
  - Eje X: Período (Día/Semana/Mes)
  - Eje Y: Kg PT
  - Una barra por sala, apiladas
  - Colores distintos por sala
  - Click en barra → modal con detalles de ODFs
  - Hover: sala, kg PT, kg MP, cantidad de órdenes
  - Fondo transparente, fuente blanca (dark theme)

- **Clasificación de Túneles:**
  - Túnel Estático vs Túnel Continuo
  - Si el nombre del producto contiene `[1.4]` + `TÚNEL CONTINUO` → se agrupa como Túnel Continuo
  - Túnel Continuo cuenta como tipo CONGELADO

- **Modal de ODFs** (st.dialog):
  - Tabla con: ODF, Fecha, Producto, Especie, Manejo, Kg PT, Kg MP, Rendimiento, Sala, Dotación, HH Efectiva, Kg/HH, Estado, Planta
  - Enlaces a Odoo: URL directa al formulario de mrp.production en Odoo

### 3.4 Sección KPIs con Sub-Tabs (función `_render_kpis_tabs`)
Dentro de Reportería se renderizan sub-secciones adicionales:

- **Tabla resumida de KPIs por fruta/manejo**
- **Gráficos consolidados** (desde `graficos.py`):
  - `grafico_salas_consolidado()` — Altair chart de kg por sala agrupado por período
  - `grafico_tuneles_consolidado()` — Altair chart de kg por túnel
  - `grafico_congelado_semanal()` — Altair chart de congelado con tendencias
  - `grafico_vaciado_por_sala()` — Altair chart de vaciado de salas

### 3.5 Descarga Excel
- Botón para descargar datos en formato Excel (.xlsx)
- Usa `openpyxl` y `io.BytesIO`

---

## 4. TAB 2: DETALLE DE OF (tab_detalle.py)

### 4.1 Controles
- Selector de fechas con valores por defecto de última semana
- Selector de estado (dropdown): Todos, Borrador, Confirmado, En Progreso, Por Cerrar, Hecho, Cancelado
- Mapeo: `{'draft': 'Borrador', 'confirmed': 'Confirmado', 'progress': 'En Progreso', 'to_close': 'Por Cerrar', 'done': 'Hecho', 'cancel': 'Cancelado'}`

### 4.2 API Calls
```
GET /api/v1/produccion/ordenes?username=...&password=...&estado=done&fecha_desde=...&fecha_hasta=...
GET /api/v1/produccion/ordenes/{of_id}?username=...&password=...
GET /api/v1/produccion/kpis?username=...&password=...
```

### 4.3 Vista de Lista de OFs
- Tabla con todas las OFs en el período
- Al seleccionar una OF → vista de detalle expandida

### 4.4 Vista de Detalle de OF
Cuando el usuario selecciona una OF individual:
- **KPIs de la OF:** Producto, Estado, Kg MP, Kg PT, Rendimiento
- **Componentes consumidos:** tabla con producto, lote, cantidad, precio unitario, PxQ
  - Gráfico pie + barras horizontales de distribución por producto
- **Subproductos (output):** misma estructura
- **Gráficos ECharts** (`streamlit-echarts`): gráfico circular/barras interactivos

### 4.5 Sub-Tabs Internos
El tab Detalle contiene 3 sub-tabs adicionales:

#### 4.5.1 Monitor Diario (`tab_monitor_diario.py`, 44 KB)
- Monitor en tiempo real de producción del día
- **API Calls:**
  ```
  GET /api/v1/produccion/monitor/activos?username=...&password=...
  GET /api/v1/produccion/monitor/cerrados?username=...&password=...&fecha=YYYY-MM-DD
  GET /api/v1/produccion/monitor/evolucion?username=...&password=...&fecha=YYYY-MM-DD
  GET /api/v1/produccion/monitor/salas?username=...&password=...
  GET /api/v1/produccion/monitor/productos?username=...&password=...
  POST /api/v1/produccion/monitor/snapshot (toma foto del estado actual)
  GET /api/v1/produccion/monitor/snapshots (historial de snapshots)
  POST /api/v1/produccion/monitor/report_pdf (genera PDF del reporte)
  ```
- Muestra OFs activas (en progreso) con estado en tiempo real
- Muestra OFs cerradas del día con métricas
- Gráfico de evolución temporal de producción
- Agrupación por sala y por producto
- Función de snapshot (toma foto del estado) y generación de PDF

#### 4.5.2 Kg por Línea (`tab_kg_por_linea.py`, 164 KB — archivo más grande)
- Análisis masivo de kg producidos por línea de producción
- **API Call:**
  ```
  GET /api/v1/rendimiento/dashboard?username=...&password=...&fecha_inicio=...&fecha_fin=...
  ```
- Gráficos detallados de kg por cada línea/sala de producción
- Tablas extensivas con datos de producción por línea

#### 4.5.3 Pallets Disponibles (`tab_pallets_disponibles.py`, 20 KB)
- Inventario de pallets disponibles para despacho
- **API Calls:**
  ```
  GET /api/v1/produccion/pallets-disponibles?username=...&password=...
  GET /api/v1/produccion/pallets-disponibles/productos-2026?username=...&password=...
  GET /api/v1/produccion/pallets-disponibles/proveedores?username=...&password=...
  ```
- Filtros por producto y proveedor
- Vista de pallets con cantidades

---

## 5. TAB 3: CLASIFICACIÓN (tab_clasificacion.py)

### 5.1 Funcionalidad
- Consulta clasificación de pallets por categoría de producto
- Filtros por fecha, tipo de producto, categoría

### 5.2 API Calls
```
GET /api/v1/produccion/clasificacion
  ?username=...&password=...&fecha_desde=...&fecha_hasta=...
  Timeout: 30s

POST /api/v1/produccion/report_clasificacion
  Body: { payload con datos de clasificación }
  → Genera reporte PDF/Excel de clasificación
```

### 5.3 Visualización
- Tabla de clasificación con filtros multiselect por categoría
- Gráficos ECharts interactivos (pie chart de distribución)
- Gráficos Plotly (barras horizontales por producto)
- Descarga Excel y PDF del reporte

---

## 6. TAB 4: PALLETS POR SALA (tab_pallets_por_sala.py)

### 6.1 Funcionalidad
- Distribución de pallets en cada sala de proceso
- Vista global de la planta con estado de cada sala

### 6.2 API Calls
```
GET /api/v1/produccion/productos_pt
  ?username=...&password=...
  → Lista de productos terminados (PT)

GET /api/v1/produccion/clasificacion
  ?username=...&password=...&fecha_desde=...&fecha_hasta=...
  → Datos de clasificación para calcular pallets por sala
```

### 6.3 Visualización
- Vista de cada sala con sus pallets
- Filtros por producto PT
- Gráficos de distribución por sala (barras, pie charts)
- Tabla detallada con información de cada pallet

---

## 7. TAB 5: ETIQUETAS (tab_etiquetas.py)

### 7.1 Funcionalidad
Módulo complejo para gestión de etiquetas de pallet:
- Búsqueda de órdenes de producción
- Listado de pallets por orden
- Generación de etiquetas PDF
- Impresión directa en impresora Zebra

### 7.2 API Calls
```
GET /api/v1/etiquetas/buscar_ordenes
  ?termino=...&username=...&password=...
  → Busca OFs por nombre/referencia

GET /api/v1/etiquetas/pallets_orden
  ?orden_name=...&username=...&password=...
  → Lista pallets de una orden específica

GET /api/v1/etiquetas/clientes
  ?username=...&password=...
  → Lista de clientes

GET /api/v1/etiquetas/full_trace
  → Trazabilidad completa de un pallet

GET /api/v1/etiquetas/trace_lot
  → Trazabilidad de un lote específico

GET /api/v1/etiquetas/search_lots
  → Búsqueda de lotes

GET /api/v1/etiquetas/prev_candidates
  → Candidatos previos para etiquetas

GET /api/v1/etiquetas/find_package
  → Buscar paquete/pallet

GET /api/v1/etiquetas/info_etiqueta/{package_id}
  → Información completa de etiqueta

POST /api/v1/etiquetas/reservar
  → Reservar pallet para despacho

POST /api/v1/etiquetas/generar_etiqueta_pdf
  → Genera PDF de etiqueta individual

POST /api/v1/etiquetas/generar_etiquetas_multiples_pdf
  → Genera PDF de múltiples etiquetas

POST /api/v1/etiquetas/imprimir_zebra
  → Envía a impresora Zebra
```

### 7.3 Modelo de Datos de Etiqueta
- Número de pallet (package)
- Producto terminado
- Lote PT
- Cantidad (kg)
- Fecha de producción
- Orden de fabricación
- Cliente destino
- Información de trazabilidad

---

## 8. TAB 6: TRAZABILIDAD (tab_trazabilidad.py)

### 8.1 Funcionalidad
Trazabilidad completa de lotes productivos — desde materia prima hasta producto terminado:
- Búsqueda por nombre de lote PT
- Visualización gráfica del flujo de trazabilidad
- Múltiples formatos de visualización

### 8.2 API Calls
```
GET /api/v1/etiquetas/full_trace
  → Trazabilidad completa desde pallet/lote

GET /api/v1/etiquetas/trace_lot
  → Trazabilidad de lote específico

GET /api/v1/rendimiento/trazabilidad-inversa/{lote_pt_name}
  → Trazabilidad inversa: de PT a MP

POST /api/v1/rendimiento/trazabilidad-pallets
  Body: ["PALLET-001", "PALLET-002"]
  → Trazabilidad completa de pallets
```

### 8.3 Visualizaciones
- Tabla de resultados de trazabilidad
- Gráfico de red/flujo (usa componentes de la carpeta `components/`):
  - `visjs_network` — Vis.js Network graph
  - `nivo_sankey` — Sankey diagram
  - `sigma_graph` — Sigma.js graph
  - `flow_timeline` — Timeline flow
- Transformers en backend:
  - `reactflow_transformer.py`
  - `sankey_transformer.py`
  - `visjs_transformer.py`

---

## 9. TAB 7: AUTOMATIZACIÓN OF (tab_automatizacion_of.py)

### 9.1 Funcionalidad
Automatización de procesos de fabricación con pallets:
- Buscar orden de fabricación
- Validar pallets
- Agregar pallets a una OF

### 9.2 API Calls
```
POST /api/v1/automatizaciones/procesos/buscar-orden
  → Busca una OF para automatización

POST /api/v1/automatizaciones/procesos/validar-pallets
  → Valida que los pallets son válidos para la OF

POST /api/v1/automatizaciones/procesos/agregar-pallets
  → Agrega pallets a la OF (operación de escritura en Odoo)
```

### 9.3 Flujo
1. Usuario busca una OF por nombre
2. Sistema muestra información de la OF
3. Usuario selecciona/escanea pallets
4. Sistema valida los pallets contra la OF
5. Usuario confirma → sistema agrega pallets a Odoo

---

## 10. SERVICIOS BACKEND (LÓGICA DE NEGOCIO)

### 10.1 ProduccionService (`produccion_service.py`, 29 KB)
Conecta a Odoo via XML-RPC para:
- `get_ordenes_fabricacion(estado, fecha_desde, fecha_hasta)` → Consulta `mrp.production`
- `get_of_detail(of_id)` → Detalle completo de una OF:
  - Componentes consumidos (`stock.move.line` con `production_id`)
  - Subproductos producidos
  - KPIs calculados: rendimiento, kg/HH
  - Costos operacionales
- `get_kpis()` → Resumen general de KPIs
- `get_resumen()` → Resumen de producción
- `get_clasificacion_pallets(fecha_desde, fecha_hasta)` → Clasificación de pallets

### 10.2 RendimientoService (`rendimiento_service.py`, 63 KB)
El servicio más grande y complejo:
- `get_mos_por_periodo(fecha_inicio, fecha_fin, solo_terminadas)`:
  - Consulta `mrp.production` filtrado por fechas y estado
  - Campos: name, product_id, date_start, date_finished, state, qty_producing, product_qty, etc.
- `get_consumos_batch(mos)`:
  - Para cada MO, consulta `stock.move.line` donde `production_id` coincide
  - Obtiene: producto, lote, qty_done, precio unitario
- `get_produccion_batch(mos)`:
  - Obtiene producción (output) de cada MO desde `stock.move.line`
- `get_costos_operacionales_batch(mos)`:
  - Obtiene costos: dotación, HH efectiva, etc.
- `get_trazabilidad_inversa(lote_pt_name)`:
  - Desde un lote de PT, rastrea hasta los lotes de MP originales
- `get_trazabilidad_pallets(pallet_names)`:
  - Trazabilidad completa de pallets
- **`get_dashboard_completo(fecha_inicio, fecha_fin, solo_terminadas)` — ENDPOINT CENTRAL:**
  - Combina todos los datos en una sola respuesta
  - Calcula rendimientos por fruta, manejo, sala, planta
  - Agrupa MOs con toda su información
  - Retorna: overview, consolidado, salas, mos
- `get_inventario_trazabilidad(fecha_desde, fecha_hasta)`:
  - Inventario con trazabilidad completa

### 10.3 EtiquetasPalletService (`etiquetas_pallet_service.py`, 76 KB)
Servicio para etiquetas:
- Búsqueda de órdenes de producción
- Obtención de pallets por orden (consulta `stock.quant.package`)
- Trazabilidad completa de pallets
- Generación de PDFs de etiquetas (usa `reportlab`)
- Reserva de pallets
- Impresión Zebra (ZPL commands)
- Consulta de lotes (`stock.lot`)

### 10.4 MonitorProduccionService (`monitor_produccion_service.py`, 28 KB)
Monitoreo en tiempo real:
- OFs activas (estado 'progress')
- OFs cerradas del día
- Evolución temporal
- Agrupación por sala/producto
- Snapshots de estado
- Generación de reportes PDF

### 10.5 MonitorReportService (`monitor_report_service.py`, 21 KB)
Generación de reportes PDF del monitor diario:
- Usa `reportlab` para generar PDFs
- Incluye tablas, gráficos, métricas

### 10.6 PalletsDisponiblesService (`pallets_disponibles_service.py`, 22 KB)
Inventario de pallets:
- Consulta pallets en stock disponibles para despacho
- Filtra por producto, proveedor
- Agrupa por ubicación

### 10.7 ProduccionReportService (`produccion_report_service.py`, 20 KB)
Reportes de clasificación y producción:
- Genera reportes Excel/PDF de clasificación
- Formatos personalizados

### 10.8 ExcelService (`excel_service.py`, 16 KB)
Generación de archivos Excel:
- Usa `openpyxl`
- Templates personalizados
- Formato chileno (números con punto separador de miles, coma decimal)

### 10.9 TrazabilidadPalletService (`trazabilidad_pallet_service.py`, 9 KB)
Trazabilidad específica de pallets

### 10.10 TriggerSOAsociadaService (`trigger_so_asociada_service.py`, 11 KB)
Asocia órdenes de venta (SO) con órdenes de fabricación

### 10.11 RevertirConsumoService (`revertir_consumo_service.py`, 28 KB)
Operación de escritura en Odoo para revertir consumos incorrectos

### 10.12 Traceability Service (`traceability/`, 144 KB total)
Sistema completo de trazabilidad visual:
- `traceability_service.py` (96 KB) — lógica principal
- `reactflow_transformer.py` — transforma datos a formato React Flow
- `sankey_transformer.py` — transforma a diagrama Sankey
- `visjs_transformer.py` — transforma a Vis.js network

### 10.13 Túneles Service (`tuneles/`, 36 KB total)
Lógica de túneles de congelado:
- Constants: tipos de túnel, categorías
- Helpers: funciones auxiliares
- Pallet validator: validación de pallets en túneles
- Pendientes: gestión de pendientes en túneles

---

## 11. MODELOS DE DATOS ODOO (XML-RPC)

### 11.1 Modelos Consultados
```python
# Órdenes de fabricación
model = "mrp.production"
fields = ["name", "product_id", "date_start", "date_finished", "state",
          "qty_producing", "product_qty", "origin", "company_id",
          "x_studio_sala", "x_studio_dotacion", "x_studio_hh_efectiva"]

# Movimientos de stock (consumos y producción)
model = "stock.move.line"
fields = ["product_id", "lot_id", "qty_done", "location_id", "location_dest_id",
          "package_id", "x_studio_precio_unitario", "production_id",
          "product_category_name"]

# Paquetes (pallets)
model = "stock.quant.package"
fields = ["name", "quant_ids", "location_id"]

# Lotes
model = "stock.lot"
fields = ["name", "product_id", "create_date"]

# Productos
model = "product.product"
fields = ["name", "categ_id", "type", "uom_id"]

# Clientes
model = "res.partner"
```

### 11.2 Campos Custom Odoo (Studio)
Estos campos NO son estándar de Odoo, fueron creados con Odoo Studio:
- `mrp.production.x_studio_sala` — Sala de proceso
- `mrp.production.x_studio_dotacion` — Dotación (número de trabajadores)
- `mrp.production.x_studio_hh_efectiva` — Horas-hombre efectivas
- `stock.move.line.x_studio_precio_unitario` — Precio unitario personalizado

---

## 12. GRÁFICOS Y VISUALIZACIONES (DETALLE)

### 12.1 Gráficos Plotly (en shared.py y tab_reporteria.py)
```python
# Pie Chart (Donut)
go.Pie(labels, values, hole=0.4, textinfo="percent")
# Config: fondo transparente, fuente blanca, margin(l=20, r=140, t=30, b=30)

# Barras Horizontales
go.Bar(x=values, y=labels, orientation="h", marker=dict(color="#00cc66"))
# Config: fondo transparente, fuente blanca, height=380

# Barras Apiladas por Período/Sala (tab_reporteria)
go.Bar(x=periodos, y=kg_values, name=sala)
# barmode='stack', fondo transparente, categorías ordenadas cronológicamente
# Click event → abre modal con ODFs detalladas
```

### 12.2 Gráficos Altair (en graficos.py)
```python
# grafico_salas_consolidado: Chart combinado barras + línea de rendimiento
# grafico_tuneles_consolidado: Barras por túnel con línea de rendimiento
# grafico_congelado_semanal: Vista semanal de congelado con tendencia
# grafico_vaciado_por_sala: Barras horizontales de vaciado por sala

# Todos usan:
# - alt.Chart(df).mark_bar() / mark_line() / mark_point()
# - Colores consistentes, esquema dark
# - Tooltips con formato chileno
# - Eje temporal con labels formateados
```

### 12.3 ECharts (via streamlit-echarts)
- Gráficos circulares interactivos en Detalle de OF
- Configuración de opciones en diccionarios Python

### 12.4 Componentes de Red/Grafos
Para trazabilidad visual (carpeta `components/`):
- **Vis.js Network:** Nodos y aristas para flujo de trazabilidad
- **Sankey diagram:** Diagrama Sankey para flujo MP → PT
- **React Flow:** Diagrama de flujo interactivo

---

## 13. ESTILOS Y DISEÑO VISUAL

### 13.1 Theme
- **Dark theme obligatorio**
- Colores base:
  - Background principal: `#0e1117`
  - Sidebar background: `#262730`
  - Cards: `#1e293b` con borde `#334155`
  - Texto: `#ffffff`
  - Accent/Success: `#00cc66`, `#00ff88`
  - KPI accent: `#4fd1c5`
  - Skeleton shimmer: gradient entre `#2a2a4a` y `#3a3a5a`

### 13.2 CSS Inyectado
```css
/* Card de info */
.info-card {
    background-color: #1e293b;
    padding: 20px;
    border-radius: 10px;
    border: 1px solid #334155;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

/* Card de volumen */
.volumen-card {
    background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%);
    padding: 20px;
    border-radius: 12px;
    text-align: center;
}
.volumen-card h2 { color: #4fd1c5; font-size: 2.5rem; }
.volumen-card p { color: #a0aec0; }

/* Skeleton loader animado */
@keyframes shimmer {
    0% { background-position: -1000px 0; }
    100% { background-position: 1000px 0; }
}
.skeleton {
    background: linear-gradient(90deg, #2a2a4a 25%, #3a3a5a 50%, #2a2a4a 75%);
    background-size: 1000px 100%;
    animation: shimmer 2s infinite;
    border-radius: 8px;
}
```

### 13.3 Formateo de Números (Formato Chileno)
```python
# Miles con punto, decimales con coma
# 1.234.567,89 (no 1,234,567.89)
def fmt_numero(valor, decimales=0):
    formatted = f"{valor:,.{decimales}f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return formatted

# Porcentaje: "95,3%"
def fmt_porcentaje(valor, decimales=1):
    return f"{fmt_numero(valor, decimales)}%"
```

### 13.4 Alertas por Rendimiento
```python
# 🟢 >= 95%
# 🟡 >= 90% 
# 🔴 < 90%
# (En graficos.py: 🟢 >= 90%, 🟡 >= 85%, 🔴 < 85%)
```

### 13.5 Layout
- `layout="wide"` — ancho completo de pantalla
- Uso extensivo de `st.columns()` para layouts en grilla
- `st.tabs()` para navegación principal y sub-navegación
- `st.expander()` para secciones colapsables
- `st.dialog()` para modales
- `st.fragment()` para renders parciales sin recargar toda la página

---

## 14. TÍTULO, SUBTÍTULOS E ICONOS

```
🏭 Dashboard de Producción
  Caption: "Monitorea rendimientos productivos y detalle de órdenes de fabricación"

Tabs:
  📊 Reportería General
  📋 Detalle de OF
  📦 Clasificación
  🏢 Pallets por Sala
  🏷️ Etiquetas
  🔍 Trazabilidad
  ⚙️ Automatización OF

Sub-elementos:
  📅 Seleccionar Período
  🏭 Filtro de Planta
  📊 Agrupación de Gráficos
  🔄 Consultar Reportería (botón primario)
  📦 Kg MP Total / 📤 Kg PT Total / 🏭 Kg Proceso / ❄️ Kg Congelado
```

---

## 15. FUNCIONALIDADES ESPECIALES

### 15.1 Filtro por Planta
```python
def detectar_planta(mo_name, sala_name=None):
    """
    - Si MO empieza con "VLK" → VILKUN
    - Si sala contiene "VILKUN" o "VLK" → VILKUN
    - Resto → RIO FUTURO
    """
```

### 15.2 Cache
- Frontend: `@st.cache_data(ttl=120)` para dashboard, `ttl=300` para ordenes/kpis
- Backend: `diskcache` para respuestas costosas

### 15.3 Progress Bar al Cargar
```
Fase 1: "🔗 Conectando con Odoo..." (20%)
Fase 2: "📊 Consultando datos de producción..." (50%)
Fase 3: "⚙️ Procesando rendimientos..." (80%)
Fase 4: ✅ Completado (100%) → limpia progress y muestra toast
```

### 15.4 Skeleton Loader
Mientras los datos cargan, se muestra un skeleton animado con shimmer effect.

### 15.5 Toast Notifications
```python
st.toast("✅ Datos de reportería cargados", icon="✅")
st.toast(f"❌ Error: {str(e)[:100]}", icon="❌")
```

### 15.6 URLs a Odoo
```python
odoo_url = f"https://riofuturo.server98c6e.oerpondemand.net/web#id={mo_id}&menu_id=390&cids=1&action=604&model=mrp.production&view_type=form"
```

### 15.7 Generación de PDFs
- Reportes Monitor Diario (via `monitor_report_service.py`)
- Etiquetas de Pallet (via `etiquetas_pallet_service.py` + `generador_etiquetas.py`)
- Reportes de Clasificación (via `produccion_report_service.py`)
- Usa `reportlab` y `fpdf`

### 15.8 Impresión Zebra
- Generación de comandos ZPL
- Envío a impresora Zebra vía red/USB

---

## 16. CONEXIÓN ODOO — DETALLES TÉCNICOS

### 16.1 OdooClient (shared/odoo_client.py)
```python
class OdooClient:
    DEFAULT_URL = "https://riofuturo.server98c6e.oerpondemand.net"
    DEFAULT_DB = "riofuturo-master"
    
    # Conexión: XML-RPC con timeout de 30s
    # Autenticación: common.authenticate(db, username, password, {})
    # Operaciones: models.execute_kw(db, uid, password, model, method, domain, kwargs)
    
    # Métodos disponibles:
    # search(model, domain, limit, order) → List[int]
    # read(model, ids, fields) → List[Dict]
    # search_read(model, domain, fields, limit, order, offset) → List[Dict]
    # create(model, vals) → int
    # write(model, ids, vals) → bool
    # execute(model, method, args) → Any
```

### 16.2 Variables de Entorno
```env
ODOO_URL=https://riofuturo.server98c6e.oerpondemand.net
ODOO_DB=riofuturo-master
ENV=prod  # o "development"
API_URL=http://127.0.0.1:8000
```

---

## 17. INVENTARIO COMPLETO DE ARCHIVOS

### Frontend (14 archivos, ~507 KB)
```
frontend/
├── 2_Produccion.py                    (4.2 KB)  - Orquestador principal
└── pages/produccion/
    ├── __init__.py                    (0 KB)
    ├── shared.py                      (14.6 KB) - Utilidades compartidas
    ├── graficos.py                    (32.5 KB) - Gráficos Altair
    ├── sidebar_trigger.py             (1.8 KB)  - Sidebar trigger
    ├── tab_reporteria.py              (52.9 KB) - Reportería General
    ├── tab_detalle.py                 (25.4 KB) - Detalle de OF
    ├── tab_clasificacion.py           (23 KB)   - Clasificación
    ├── tab_pallets_por_sala.py        (56.6 KB) - Pallets por Sala
    ├── tab_etiquetas.py               (45.8 KB) - Etiquetas
    ├── tab_trazabilidad.py            (28.7 KB) - Trazabilidad
    ├── tab_automatizacion_of.py       (15.8 KB) - Automatización OF
    ├── tab_monitor_diario.py          (43.8 KB) - Monitor Diario (sub-tab)
    ├── tab_kg_por_linea.py            (164.4 KB)- Kg por Línea (sub-tab)
    └── tab_pallets_disponibles.py     (19.6 KB) - Pallets Disponibles (sub-tab)
```

### Backend (30+ archivos, ~650 KB)
```
backend/
├── main.py                            (3.1 KB)  - FastAPI app
├── cache.py                           (6.3 KB)  - Sistema de cache
├── config/settings.py                 (1.2 KB)  - Configuración
├── routers/
│   ├── produccion.py                  (17.3 KB) - Router producción
│   ├── rendimiento.py                 (14.9 KB) - Router rendimiento
│   ├── etiquetas.py                   (16.2 KB) - Router etiquetas
│   └── automatizaciones.py            (44.5 KB) - Router automatizaciones
├── services/
│   ├── produccion_service.py          (29.1 KB) - Servicio producción
│   ├── rendimiento_service.py         (63.1 KB) - Servicio rendimiento
│   ├── etiquetas_pallet_service.py    (76 KB)   - Servicio etiquetas
│   ├── monitor_produccion_service.py  (28.2 KB) - Monitor producción
│   ├── monitor_report_service.py      (21.3 KB) - Reportes monitor
│   ├── pallets_disponibles_service.py (21.8 KB) - Pallets disponibles
│   ├── produccion_report_service.py   (19.9 KB) - Reportes producción
│   ├── excel_service.py               (16.1 KB) - Generador Excel
│   ├── trazabilidad_pallet_service.py (9.2 KB)  - Trazabilidad pallets
│   ├── trigger_so_asociada_service.py (10.8 KB) - Trigger SO
│   ├── revertir_consumo_service.py    (28.4 KB) - Revertir consumos
│   ├── traceability/
│   │   ├── traceability_service.py    (96.3 KB) - Servicio trazabilidad
│   │   ├── reactflow_transformer.py   (11.3 KB) - Transformer ReactFlow
│   │   ├── sankey_transformer.py      (15.2 KB) - Transformer Sankey
│   │   └── visjs_transformer.py       (20.3 KB) - Transformer Vis.js
│   ├── tuneles/
│   │   ├── constants.py               (2.8 KB)
│   │   ├── helpers.py                 (4.1 KB)
│   │   ├── pallet_validator.py        (14 KB)
│   │   └── pendientes.py             (14 KB)
│   └── report/
│       ├── aggregators.py             (17 KB)
│       ├── constants.py               (0.2 KB)
│       └── formatters.py             (1.3 KB)
└── utils/
    ├── generador_etiquetas.py         (7 KB)
    └── pdf_generator.py              (3.3 KB)
```

### Shared (7 archivos)
```
shared/
├── __init__.py
├── auth.py                            (18 KB)   - Autenticación
├── odoo_client.py                     (9.8 KB)  - Cliente XML-RPC
├── constants.py                       (1 KB)    - Constantes globales
├── cookies.py                         (5 KB)    - Manejo de cookies
├── permissions.json                   (2.6 KB)  - Permisos por dashboard/página
├── aprobaciones.json                  (3.4 KB)  - Config aprobaciones
└── exclusiones.json                   (0.1 KB)  - Exclusiones
```

### Assets
```
assets/
└── RFP - LOGO OFICIAL.png            (94.4 KB) - Logo oficial de Rio Futuro
```

---

## 18. DEPENDENCIAS (requirements.txt)

```
# Backend
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0
httpx>=0.25.0
python-multipart>=0.0.6

# Frontend
streamlit>=1.35.0
pandas>=2.1.0
plotly>=5.18.0
altair>=5.2.0
openpyxl>=3.1.0
matplotlib>=3.7.0
streamlit-echarts>=0.4.0

# Shared
requests>=2.31.0
python-dateutil>=2.8.2

# PDF
reportlab>=4.0
fpdf>=1.7.2
PyPDF2>=3.0.0

# Cache
diskcache>=5.6.3
```

---

## 19. INSTRUCCIONES PARA MIGRACIÓN

### Paso 1: Leer todos los archivos fuente
Los archivos están en la carpeta `MIGRACION_PRODUCCION/`. Léelos **todos** — son el código fuente completo y funcional.

### Paso 2: Recrear la estructura de datos
El backend se comunica con Odoo ERP via XML-RPC. Si quieres mantener la conexión a Odoo, necesitarás replicar el `OdooClient`. Si quieres usar otra fuente de datos, mapea las respuestas API documentadas arriba.

### Paso 3: Recrear la UI
Cada tab es un módulo independiente con su función `render(username, password)`. Recrea:
1. Los controles/filtros (selectores de período, checkboxes, botones)
2. Los KPIs (métricas numéricas formateadas al estilo chileno)
3. Los gráficos (Plotly para interactivos, Altair para analytics, ECharts para circulares)
4. Las tablas (DataFrames con formateo)
5. La descarga de Excel/PDF
6. Los modales/dialogs
7. La generación de etiquetas y PDFs
8. La impresión Zebra

### Paso 4: Mantener el diseño visual
- Theme dark obligatorio con los colores especificados
- Formato numérico chileno
- Skeleton loaders mientras carga
- Toast notifications
- Progress bars durante consultas largas
- Layout responsive con columnas

### Paso 5: Mantener la lógica de negocio
- Detección de planta (RFP vs VILKUN) por nombre de MO y sala
- Clasificación de túneles (Estático vs Continuo)
- Cálculo de temporada (20 Nov → 20 Nov)
- Rendimiento = (Kg PT / Kg MP) × 100
- Alertas por color según rendimiento

---

## 20. NOTAS FINALES

- **Todos los archivos fuente están en la carpeta `MIGRACION_PRODUCCION/`** — son código funcional completo
- El sistema es **producción activa** de la empresa Rio Futuro (procesadora de frutas en Chile)
- Los datos son reales de Odoo (no mocks)
- Las credenciales son por usuario (no hardcodeadas)
- El dashboard maneja ~150+ OFs por semana con cientos de miles de kg
- El archivo más grande es `tab_kg_por_linea.py` (164 KB) — contiene lógica muy detallada
- Total del código: ~1.2 MB de Python funcional
