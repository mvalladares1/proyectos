# Sistema de Reconciliación ODF → Sale Orders

## 🎯 Objetivo

Automatizar el cálculo y actualización de los campos:
- `x_studio_kg_totales_po`
- `x_studio_kg_consumidos_po`
- `x_studio_kg_disponibles_po`

## 🏗️ Arquitectura

### **Flujo de Datos**

```
┌─────────────────────────────────────────────────────────┐
│  ODOO (Automatización existente)                        │
│  • Digitador ingresa x_studio_po_cliente_1              │
│  • Busca SOs donde origin == PO Cliente                 │
│  • Llena x_studio_po_asociada = "S00843, S00912"        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  TU SISTEMA (Backend FastAPI)                           │
│  • Lee x_studio_po_asociada                             │
│  • Parsea SOs: ["S00843", "S00912"]                     │
│  • Lee sale.order.line de cada SO                       │
│  • Lee subproductos de la ODF                           │
│  • Match: subproducto.product_id == so_line.product_id  │
│  • Calcula totales                                      │
│  • ESCRIBE a Odoo                                       │
└─────────────────────────────────────────────────────────┘
```

## 📦 Componentes Implementados

### 1. **Servicio de Reconciliación**
`backend/services/odf_reconciliation_service.py`

**Métodos principales**:
- `parse_pos_asociadas(po_str)` → Parsea "S00843, S00912" → ["S00843", "S00912"]
- `get_so_lines(so_names)` → Obtiene líneas de las SOs
- `get_subproductos_odf(odf_id)` → Obtiene productos terminados de la ODF
- `reconciliar_odf(odf_id, dry_run)` → **Proceso completo**
- `reconciliar_odfs_por_fecha(inicio, fin)` → Reconciliación masiva

### 2. **API Endpoints**
`backend/routers/odf_reconciliation.py`

**Endpoints disponibles**:

```
POST /api/v1/odf-reconciliation/odf/{odf_id}/reconciliar
  - Reconcilia una ODF específica
  - Query param: dry_run (bool)
  
POST /api/v1/odf-reconciliation/reconciliar-rango
  - Reconcilia ODFs en rango de fechas
  - Query params: fecha_inicio, fecha_fin, dry_run
  
GET /api/v1/odf-reconciliation/odf/{odf_id}/preview
  - Preview sin escribir (siempre dry_run=True)
  
GET /api/v1/odf-reconciliation/parsear-pos/{po_string}
  - Utilitario para parsear strings de POs
```

### 3. **Scripts**

**Test Manual**:
```bash
python scripts/test_odf_reconciliation.py
```
- Prueba con ODF WH/Transf/00779
- Muestra preview
- Pide confirmación
- Escribe a Odoo
- Verifica valores

**Scheduled Job**:
```bash
python scripts/scheduled_odf_reconciliation.py
```
- Reconcilia ODFs de últimos 7 días
- Logs en `logs/odf_reconciliation.log`
- Para ejecutar diariamente (ej: 18:00)

## 🔧 Configuración

### **1. Variables de Entorno**

Crear/actualizar `.env`:
```bash
ODOO_USERNAME=mvalladares@riofuturo.cl
ODOO_PASSWORD=tu_api_key_aqui
```

### **2. Registrar Router**

Ya está registrado en `backend/main.py`:
```python
from backend.routers import odf_reconciliation
app.include_router(odf_reconciliation.router)
```

### **3. Configurar Scheduled Job (Opcional)**

**Windows Task Scheduler**:
```
Trigger: Diario a las 18:00
Action: python C:\path\to\scripts\scheduled_odf_reconciliation.py
```

**Linux Crontab**:
```bash
# Ejecutar diariamente a las 18:00
0 18 * * * cd /path/to/proyecto && python scripts/scheduled_odf_reconciliation.py
```

## 🎮 Uso desde Dashboard

### **Opción 1: Reconciliar ODF Individual**

```python
import streamlit as st
import requests

# En tu página de Streamlit
if st.button("Reconciliar ODF"):
    response = requests.post(
        f"http://localhost:8000/api/v1/odf-reconciliation/odf/{odf_id}/reconciliar",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    resultado = response.json()
    
    st.success(f"✅ Actualizado")
    st.metric("KG Totales", f"{resultado['kg_totales_po']:,.2f}")
    st.metric("KG Consumidos", f"{resultado['kg_consumidos_po']:,.2f}")
    st.metric("KG Disponibles", f"{resultado['kg_disponibles_po']:,.2f}")
```

### **Opción 2: Reconciliar por Rango de Fechas**

```python
import streamlit as st
import requests
from datetime import date, timedelta

# Filtros
col1, col2 = st.columns(2)
with col1:
    fecha_inicio = st.date_input("Desde", date.today() - timedelta(days=7))
with col2:
    fecha_fin = st.date_input("Hasta", date.today())

if st.button("Reconciliar ODFs"):
    response = requests.post(
        "http://localhost:8000/api/v1/odf-reconciliation/reconciliar-rango",
        params={
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat()
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    
    resultado = response.json()
    
    st.success(f"✅ {resultado['odfs_reconciliadas']} ODFs actualizadas")
    st.info(f"ℹ️ {resultado['odfs_sin_po']} sin PO")
    if resultado['odfs_error'] > 0:
        st.warning(f"⚠️ {resultado['odfs_error']} con errores")
```

## 📊 Ejemplo Real (ODF 00779)

**Input (Odoo)**:
```
ODF: WH/Transf/00779
x_studio_po_asociada = "S00843"
```

**Procesamiento**:
```
SO S00843:
  • [402122000] FB MK Conv. IQF A 10 kg: 21,600 kg

ODF Subproductos:
  • [402122000] FB MK Conv. IQF A 10 kg: 5,330 kg ✅ Match
  • [402172000] FB MK Conv. IQF Retail: 250 kg
  • [602141000] FB S/V Conv.: 648 kg
  • ... otros

Cálculo:
  KG Totales = 21,600 (de la SO)
  KG Consumidos = 5,330 (subproducto que coincide)
  KG Disponibles = 16,270
  Avance = 24.7%
```

**Output (Escrito a Odoo)**:
```
x_studio_kg_totales_po = 21,600.00
x_studio_kg_consumidos_po = 5,330.00
x_studio_kg_disponibles_po = 16,270.00
```

## ✅ Validación

Para probar el sistema completo:

```bash
# 1. Ejecutar test manual
python scripts/test_odf_reconciliation.py

# 2. Verificar en Odoo que los campos se actualizaron

# 3. Probar desde API
curl -X POST "http://localhost:8000/api/v1/odf-reconciliation/odf/5614/reconciliar" \
  -H "Authorization: Bearer YOUR_TOKEN"

# 4. Preview (sin escribir)
curl -X GET "http://localhost:8000/api/v1/odf-reconciliation/odf/5614/preview" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🚨 Casos Especiales

### **Múltiples SOs**
```
x_studio_po_asociada = "S00843, S00912, S00915"

KG Totales = sum(líneas de S00843) + sum(líneas de S00912) + sum(líneas de S00915)
KG Consumidos = sum(subproductos que coinciden con cualquier SO)
```

### **Sin PO Asociada**
```
x_studio_po_asociada = "" o null

→ No se actualiza, se registra en log como "sin_po"
```

### **Producto en SO pero no producido**
```
SO tiene: [402122000] 21,600 kg
ODF subproductos: (vacío o sin coincidencias)

→ KG Totales = 21,600
→ KG Consumidos = 0
→ KG Disponibles = 21,600
```

## 📝 Notas Importantes

1. **Producto Principal vs Subproductos**:
   - `product_id` de la ODF puede ser placeholder (ej: "[2.2] PROCESO PTT")
   - Los productos REALES están en `stock.move` con `location_dest_id.usage = 'internal'`

2. **Estados de Movimientos**:
   - El sistema lee `quantity_done` (ejecutado)
   - Funciona con ODFs en cualquier estado (draft, confirmed, progress, to_close, done)

3. **Prorrateo**:
   - Solo se cuentan subproductos que **coincidan exactamente** con productos de las SOs
   - No hay estimación ni distribución proporcional

4. **Escritura a Odoo**:
   - Usa `odoo.models.execute_kw(..., 'write', ...)`
   - Solo actualiza los 3 campos `x_studio_kg_*`
   - No modifica otros campos de la ODF

## 🔮 Próximos Pasos

1. ✅ **Validar con ODF 00779** (test script)
2. ✅ **Probar con múltiples SOs**
3. ✅ **Configurar scheduled job**
4. ⏳ **Integrar en dashboard Streamlit**
5. ⏳ **Agregar visualizaciones de avance**
6. ⏳ **Alertas cuando avance > 100% o < 0%**
