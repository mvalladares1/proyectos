# Fix: Recepciones - Excel Detallado y Reporte de Defectos

**Fecha**: 2025-01-29
**Autor**: Asistente AI
**Archivos Modificados**: `pages/recepciones/tab_kpis.py`

## Problemas Reportados

### 1. Excel por Producto Detallado
**Síntoma**: Al hacer clic en "📊 Generar Excel Detallado", la página hace re-render completo y scroll automático al final.

**Causa**: El botón no estaba envuelto en un `@st.fragment`, causando que Streamlit re-renderice toda la página.

**Solución**: 
- Envolvió toda la lógica del Excel Detallado en un fragment `render_excel_detallado()`
- El fragment se renderiza de forma aislada sin afectar el resto de la página
- Elimina el scroll automático al final

### 2. Reporte de Defectos
**Síntoma**: Error al generar reporte: `name 'origen_filtro' is not defined`

**Causa**: 
- La variable `origen_filtro` no estaba definida en el scope de la función
- El código intentaba acceder a `origen_filtro` directamente en línea 895
- La variable correcta estaba en `st.session_state.origen_filtro_usado`

**Solución**:
- Agregó definición de variable desde session_state: `origen_filtro_usado = st.session_state.get('origen_filtro_usado', [])`
- Corrigió el código para usar `origen_filtro_usado` en vez de `origen_filtro`
- Envolvió toda la lógica en fragment `render_excel_defectos()`

## Cambios Realizados

### Archivo: `pages/recepciones/tab_kpis.py`

#### 1. Excel Detallado (líneas ~811-866)

**ANTES**:
```python
# Botón extra: descargar Excel DETALLADO (una fila por producto) desde el backend
det_col1, det_col2 = st.columns([1,3])
with det_col1:
    if st.button("📊 Generar Excel Detallado", ...):
        # ... código de generación ...
```

**DESPUÉS**:
```python
# Botón extra: descargar Excel DETALLADO (una fila por producto) desde el backend
@st.fragment
def render_excel_detallado():
    """Fragment para generar Excel detallado sin hacer re-render de toda la página."""
    det_col1, det_col2 = st.columns([1,3])
    with det_col1:
        if st.button("📊 Generar Excel Detallado", ...):
            # ... código de generación ...

# Renderizar fragment de Excel detallado
render_excel_detallado()
```

#### 2. Reporte de Defectos (líneas ~868-933)

**ANTES**:
```python
st.subheader("📊 Reporte de Defectos (Mora y Frambuesa)")
def_col1, def_col2 = st.columns([1,3])
with def_col1:
    if st.button("🔬 Generar Reporte de Defectos", ...):
        # ...
        # Pasar origen si existe
        if origen_filtro:  # ❌ ERROR: variable no definida
            params_defectos['origen'] = origen_filtro
```

**DESPUÉS**:
```python
@st.fragment
def render_excel_defectos():
    """Fragment para generar Excel de defectos sin hacer re-render de toda la página."""
    st.subheader("📊 Reporte de Defectos (Mora y Frambuesa)")
    
    def_col1, def_col2 = st.columns([1,3])
    with def_col1:
        if st.button("🔬 Generar Reporte de Defectos", ...):
            # Obtener origen filtro desde session_state
            origen_filtro_usado = st.session_state.get('origen_filtro_usado', [])  # ✅
            
            # Pasar origen si existe
            if origen_filtro_usado:  # ✅ Ahora usa la variable correcta
                params_defectos['origen'] = ','.join(origen_filtro_usado)

# Renderizar fragment de defectos
render_excel_defectos()
```

#### 3. Corrección de errores de sintaxis

**ANTES**:
```python
except Exception as e:
    except Exception as e:  # ❌ Doble except
        st.error(f"Error: {e}")
```

**DESPUÉS**:
```python
    except Exception as e:  # ✅ Un solo except
        st.error(f"Error: {e}")
```

## Resultados Esperados

✅ **Excel Detallado**: 
- No hace re-render completo de la página
- No scrollea automáticamente al final
- Solo actualiza el fragment correspondiente

✅ **Reporte de Defectos**:
- No genera error de variable indefinida
- Usa correctamente `origen_filtro_usado` desde session_state
- Genera el reporte de defectos correctamente

✅ **Experiencia de Usuario**:
- Interfaz más fluida y responsiva
- No pierde posición de scroll al generar reportes
- Mejor separación de concerns con fragments

## Notas Técnicas

### ¿Qué es un `@st.fragment`?

Un fragment en Streamlit 1.x+ permite aislar partes de la UI que pueden actualizarse de forma independiente sin re-ejecutar todo el script. Beneficios:

1. **Performance**: Solo re-renderiza el fragment, no toda la página
2. **UX**: Mantiene scroll position y estado del resto de la UI
3. **Modularidad**: Separa lógica en componentes independientes

### Variables en Session State

- `origen_filtro_usado`: Lista de orígenes filtrados por el usuario (ej: ['CUARTEL_7', 'FUNDO_CENTRAL'])
- Se almacena en `st.session_state` para persistir entre reruns
- Patrón seguro: `st.session_state.get('key', default_value)` para evitar KeyError

## Testing

Para verificar los cambios:

1. Ir a página de Recepciones → Tab KPIs
2. Hacer clic en "📊 Generar Excel Detallado"
   - ✅ No debe scrollear al final
   - ✅ Solo actualiza la sección del botón
3. Hacer clic en "🔬 Generar Reporte de Defectos"
   - ✅ No debe mostrar error de `origen_filtro`
   - ✅ Debe generar archivo Excel correctamente

## Relacionados

- [FIX_LINEAS_CREDITO.md](./FIX_LINEAS_CREDITO.md) - Fix anterior de duplicación en líneas de crédito
- Streamlit Fragments: https://docs.streamlit.io/library/api-reference/execution-flow/st.fragment
