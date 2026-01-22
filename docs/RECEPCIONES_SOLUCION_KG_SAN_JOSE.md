# SOLUCIÓN A PROBLEMAS EN RECEPCIONES

## Fecha: 2026-01-22
## Problemas identificados y resueltos

---

## 1. SAN JOSE no aparece en Curva de Abastecimiento ✅ RESUELTO

### **Problema:**
- La curva de abastecimiento solo tenía checkboxes para RFP y VILKÚN
- SAN JOSE no se podía seleccionar, por lo tanto no aparecía en la curva

### **Causa raíz:**
- Faltaba el checkbox para SAN JOSE en `pages/recepciones/tab_curva.py`
- El filtro solo permitía 2 plantas cuando en realidad hay 3

### **Solución aplicada:**
**Archivo modificado:** `pages/recepciones/tab_curva.py`

1. **Línea ~28-38**: Agregado checkbox para SAN JOSE
   ```python
   col_pl1, col_pl2, col_pl3 = st.columns(3)  # Cambio: ahora 3 columnas
   with col_pl1:
       curva_rfp = st.checkbox("🏭 RFP", value=True, key="curva_rfp")
   with col_pl2:
       curva_vilkun = st.checkbox("🌿 VILKÚN", value=True, key="curva_vilkun")
   with col_pl3:
       curva_san_jose = st.checkbox("🏘️ SAN JOSE", value=True, key="curva_san_jose")  # NUEVO
   ```

2. **Línea ~104-113**: Actualizado constructor de lista de plantas
   ```python
   plantas_list = []
   if curva_rfp:
       plantas_list.append("RFP")
   if curva_vilkun:
       plantas_list.append("VILKUN")
   if curva_san_jose:
       plantas_list.append("SAN JOSE")  # NUEVO
   ```

### **Resultado:**
- ✅ SAN JOSE ahora aparece como opción en la curva
- ✅ Coherencia con pestaña KPIs y Calidad que ya tenía este filtro
- ✅ Datos de SAN JOSE se incluyen correctamente en la comparación proyectado vs real

---

## 2. Diferencia de Kg entre KPIs y Calidad 🔍 DIAGNÓSTICO

### **Problema:**
- Los kg mostrados en diferentes secciones no coinciden
- Usuario reporta: "tengo diferencia de kg al comparar con kpis y calidad"

### **Causas posibles identificadas:**

#### **A. BANDEJAS vs MP (Materia Prima)**
El sistema separa dos tipos de productos:
- **MP (Materia Prima)**: Fruta que se procesa (Arándano, Frambuesa, etc.)
- **BANDEJAS**: Envases/contenedores que NO son fruta

**Ubicación en código:**
- `pages/recepciones/tab_kpis.py` línea ~145-175
- Se suman por separado:
  ```python
  total_kg_mp = 0.0        # Solo fruta
  total_bandejas = 0.0     # Solo bandejas
  ```

**Métricas mostradas:**
- **"Total Kg Recepcionados MP"**: Solo fruta (excluye bandejas)
- **"Bandejas recepcionadas"**: Solo bandejas
- Si sumas TODO sin distinguir, obtendrás un número más alto

#### **B. EXCLUSIONES DE VALORIZACIÓN**
Algunas recepciones están excluidas de la suma de costos:
- Se cargan desde `data/exclusiones_valorizacion.json`
- Estas recepciones SÍ cuentan para kg pero NO para costos

**Ubicación en código:**
- `pages/recepciones/tab_kpis.py` línea ~141-143
- `pages/recepciones/shared.py` función `get_exclusiones()`

#### **C. FILTROS DE ORIGEN**
Antes de la corrección de hoy:
- **KPIs**: Incluía RFP + VILKÚN + SAN JOSE ✅
- **Curva**: Solo incluía RFP + VILKÚN ❌ (corregido hoy)

Esta diferencia causaba que SAN JOSE apareciera en KPIs pero no en curva.

#### **D. ESTADO DE RECEPCIONES**
El filtro "Solo recepciones hechas" afecta qué recepciones se cuentan:
- **state = 'done'**: Recepciones completadas/validadas
- **state = 'assigned'**: Recepciones pendientes/en proceso
- Si el checkbox está desactivado, se incluyen todos los estados

**Ubicación en código:**
- `backend/services/recepcion_service.py` línea ~103-105

#### **E. PRODUCTOS CON CATEGORÍA "PRODUCTOS"**
El sistema filtra solo productos cuya categoría contiene "PRODUCTOS":
- Excluye servicios (WiFi, telecomunicaciones, etc.)
- Excluye productos de otras categorías no relacionadas con fruta

### **Script de diagnóstico creado:**
📄 **`scripts/debug_recepciones_kg.py`**

Este script te ayuda a identificar exactamente de dónde viene la diferencia:

**Cómo usar:**
1. Editar líneas 14-15 con tus credenciales:
   ```python
   USERNAME = "user@riofuturo.cl"
   PASSWORD = "tu_password"
   ```

2. Ejecutar:
   ```bash
   python scripts/debug_recepciones_kg.py
   ```

3. El script mostrará:
   - Kg MP por origen (RFP, VILKÚN, SAN JOSE)
   - Kg Bandejas por origen
   - Kg Otros (productos no clasificados)
   - Recepciones en estados diferentes a 'done'
   - Totales globales

**Ejemplo de salida:**
```
====================================================================
RECEPCIONES POR ORIGEN (solo estado done):
--------------------------------------------------------------------

RFP:
  Total recepciones: 45
  Kg MP:          12,345.67
  Kg Bandejas:     1,234.56
  Kg Otros:            0.00
  Kg TOTAL:       13,580.23

VILKÚN:
  Total recepciones: 23
  ...

====================================================================
RESUMEN GLOBAL:
====================================================================
Total Kg MP (sin bandejas):      15,678.90
Total Kg Bandejas:                 2,456.78
Total Kg GLOBAL:                  18,135.68
====================================================================
```

### **Cómo comparar:**

1. **En la interfaz (KPIs):**
   - Anotar "Total Kg Recepcionados MP" (ej: 15,678.90 kg)
   - Anotar "Bandejas recepcionadas" (ej: 2,456.78 kg)
   - Verificar filtros de origen seleccionados
   - Verificar rango de fechas

2. **Ejecutar el script:**
   - Usar el MISMO rango de fechas
   - Comparar "Total Kg MP" del script con interfaz
   - Comparar "Total Kg Bandejas" del script con interfaz

3. **Si NO coinciden:**
   - Verificar que los 3 orígenes estén seleccionados (RFP + VILKÚN + SAN JOSE)
   - Verificar que "Solo recepciones hechas" esté activado/desactivado igual
   - Verificar exclusiones de valorización (no afectan kg, solo costos)

---

## 3. Resumen de cambios en archivos

### Archivos modificados:

1. **`pages/recepciones/tab_curva.py`**
   - ✅ Agregado checkbox para SAN JOSE
   - ✅ Actualizada lógica de construcción de lista de plantas
   - ✅ Actualizado mensaje de advertencia

### Archivos creados:

2. **`scripts/debug_recepciones_kg.py`**
   - 🆕 Script de diagnóstico para comparar kg
   - Analiza recepciones por origen
   - Separa MP vs Bandejas vs Otros
   - Detecta recepciones en estados no-done

---

## 4. Próximos pasos recomendados

### Validación:
1. ✅ Deploy a producción de cambios en `tab_curva.py`
2. 🔍 Ejecutar `debug_recepciones_kg.py` para comparar números
3. 📊 Verificar que SAN JOSE aparezca en curva de abastecimiento
4. 📈 Comparar kg de KPIs vs script de debug

### Si persisten diferencias:
1. Verificar exclusiones de valorización (`data/exclusiones_valorizacion.json`)
2. Verificar que no haya recepciones duplicadas
3. Verificar que los overrides de origen estén correctos (`OVERRIDE_ORIGEN_PICKING`)

---

## 5. Configuración de IDs de origen

**Verificado en código:**
```python
ORIGEN_PICKING_MAP = {
    "RFP": 1,          # picking_type_id = 1
    "VILKUN": 217,     # picking_type_id = 217
    "SAN JOSE": 164    # picking_type_id = 164
}
```

Estos IDs están configurados en:
- `backend/services/recepcion_service.py` línea ~97-101
- Verificar que coincidan con Odoo si hay problemas

---

## 6. Referencias de código

### KPIs - Suma de kg:
- `pages/recepciones/tab_kpis.py:145-175` - Lógica de suma MP vs Bandejas
- `pages/recepciones/tab_kpis.py:203` - Métrica mostrada

### Curva - Filtros:
- `pages/recepciones/tab_curva.py:28-38` - Checkboxes de origen
- `pages/recepciones/tab_curva.py:104-113` - Construcción de lista

### Backend - Filtrado:
- `backend/services/recepcion_service.py:39-54` - Función get_recepciones_mp
- `backend/services/recepcion_service.py:97-101` - Mapeo de orígenes
- `backend/routers/recepcion.py:14-26` - Endpoint con parámetros origen

---

## Autor
GitHub Copilot - 2026-01-22

## Notas
- Todos los cambios son retrocompatibles
- No se requieren cambios en base de datos
- El script de debug es opcional pero muy útil para diagnóstico
