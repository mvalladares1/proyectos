# Guía para Agregar Páginas

**Última actualización:** 07 de Enero 2026

---

## Convención de Nombres

Los archivos de páginas siguen el patrón: `N_Nombre.py`
- `N` = número de orden (1-11)
- `Nombre` = nombre del dashboard en PascalCase

**Ejemplo:** `1_Recepciones.py`, `6_Finanzas.py`

---

## Estructura Mínima de una Página

```python
"""
Descripción breve del dashboard
"""
import streamlit as st
from shared.auth import proteger_pagina, get_credenciales

st.set_page_config(page_title="Nombre", page_icon="📊", layout="wide")

if not proteger_pagina():
    st.stop()

username, password = get_credenciales()

st.title("📊 Nombre del Dashboard")
# ... contenido
```

---

## Checklist para Nuevo Dashboard

1. [ ] Crear archivo `pages/N_Nombre.py`
2. [ ] Agregar docstring con descripción
3. [ ] Configurar `st.set_page_config`
4. [ ] Agregar autenticación (`proteger_pagina`)
5. [ ] Si necesita API: crear router en `backend/routers/`
6. [ ] Si necesita servicio: crear en `backend/services/`
7. [ ] Actualizar `Home.py` con el slug en `DASHBOARD_CATEGORIES`
8. [ ] Commit, push y deploy

---

## Dashboards Actuales (11)

| # | Archivo | Título | Icono | Tabs/Módulos |
|---|---------|--------|-------|--------------|
| 1 | `1_Recepciones.py` | Recepciones | 📥 | KPIs, Curva, Gestión, Aprobaciones |
| 2 | `2_Produccion.py` | Producción | 🏭 | Detalle, Reportería |
| 3 | `3_Bandejas.py` | Bandejas | 📊 | Control por proveedor |
| 4 | `4_Stock.py` | Stock | 📦 | Cámaras, Pallets, Movimientos |
| 5 | `5_Containers.py` | Containers | 🚢 | Pedidos, Producción |
| 6 | `6_Finanzas.py` | Finanzas | 💰 | YTD, Mensualizado, Flujo Caja, CG |
| 7 | `7_Rendimiento.py` | Rendimiento | ⚡ | Consolidado, Por Lote, Proveedor |
| 8 | `8_Compras.py` | Compras | 🛒 | OC, Líneas Crédito |
| 9 | `9_Permisos.py` | Permisos | ⚙️ | Administración usuarios |
| 10 | `10_Automatizaciones.py` | Automatizaciones | 🤖 | Túneles Estáticos, Crear Orden |
| 11 | `11_Relacion_Comercial.py` | Relación Comercial | 🤝 | Deudas, Saldos |

---

## Estructura de Tabs (Módulos)

### Recepciones (`pages/recepciones/`)
- `tab_kpis.py` - KPIs y métricas
- `tab_curva.py` - Curva de abastecimiento
- `tab_gestion.py` - Gestión de recepciones
- `tab_aprobaciones.py` - Aprobaciones de calidad

### Finanzas (`pages/finanzas/`)
- `tab_ytd.py` - Year-to-Date
- `tab_mensualizado.py` - Mensualizado
- `tab_flujo_caja.py` - Flujo de Caja
- `tab_cg.py` - Centro de Gastos
- `tab_agrupado.py` - Vista agrupada
- `tab_detalle.py` - Detalle líneas

### Producción (`pages/produccion/`)
- `tab_detalle.py` - Detalle MOs
- `tab_reporteria.py` - Reportería

### Stock (`pages/stock/`)
- Cámaras y ubicaciones
- Movimientos de pallets

---

## Backend Relacionado

| Dashboard | Router | Service |
|-----------|--------|---------|
| Recepciones | `recepcion.py` | `recepcion_service.py`, `abastecimiento_service.py` |
| Producción | `produccion.py` | `produccion_service.py`, `produccion_report_service.py` |
| Finanzas | `flujo_caja.py`, `estado_resultado.py` | `flujo_caja_service.py`, `estado_resultado_service.py` |
| Stock | `stock.py` | `stock_service.py` |
| Compras | `compras.py` | `compras_service.py` |
| Automatizaciones | `automatizaciones.py` | `tuneles_service.py` |
| Relación Comercial | `comercial.py` | `comercial_service.py` |
