# Implementación: Detección de Guías Duplicadas en Dashboard de Pallets

## 📋 Resumen

Se ha implementado exitosamente la funcionalidad para detectar y visualizar guías de despacho duplicadas en el tab "Pallets por Recepción" del dashboard de Recepciones.

## ✨ Características Implementadas

### 1. **Detección Automática de Duplicados** 
   - El sistema identifica automáticamente todas las guías de despacho que aparecen en múltiples recepciones
   - Solo cuenta guías no vacías para evitar falsos positivos

### 2. **Indicadores Visuales**
   - Icono de advertencia ⚠️ junto a cada guía duplicada en la tabla
   - Banner de advertencia amarillo en la parte superior cuando se detectan duplicados
   - Ejemplo: `⚠️ 2 guía(s) duplicada(s) detectada(s): GD-2024-001, GD-2024-015`

### 3. **Enlaces Directos a Odoo**
   - Columna "Ver en Odoo" con enlaces clickeables (🔗 Abrir)
   - Al hacer clic, se abre directamente el registro en Odoo
   - Formato: `https://riofuturo.server98c6e.oerpondemand.net/web#id={ID}&model=stock.picking&view_type=form`

## 🔧 Archivos Modificados

### Backend
**Archivo:** `backend/services/recepcion_service.py`
**Función:** `get_recepciones_pallets()`

**Cambios realizados:**
```python
# 1. Identificar guías duplicadas
guias_count = {}
for item in resultado:
    guia = item["guia_despacho"]
    if guia:  # Solo contar guías no vacías
        guias_count[guia] = guias_count.get(guia, 0) + 1

# 2. Marcar duplicados y agregar URL de Odoo
odoo_url = client.url  # URL base de Odoo
for item in resultado:
    guia = item["guia_despacho"]
    # Marcar si la guía está duplicada
    item["es_duplicada"] = guias_count.get(guia, 0) > 1 if guia else False
    # Agregar URL para ir directamente al registro
    item["odoo_url"] = f"{odoo_url}/web#id={item['id']}&model=stock.picking&view_type=form"
```

### Frontend
**Archivo:** `pages/recepciones/tab_pallets.py`

**Cambios realizados:**
1. **Columna visual para guías duplicadas:**
```python
def format_guia_duplicada(row):
    guia = row.get('guia_despacho', '')
    es_duplicada = row.get('es_duplicada', False)
    if es_duplicada and guia:
        return f"⚠️ {guia}"
    return guia

df_view['guia_display'] = df_view.apply(format_guia_duplicada, axis=1)
```

2. **Banner de advertencia:**
```python
guias_dup = df_view[df_view['es_duplicada'] == True]
if len(guias_dup) > 0:
    guias_duplicadas_lista = guias_dup['guia_despacho'].unique()
    st.warning(f"⚠️ **{len(guias_duplicadas_lista)} guía(s) duplicada(s) detectada(s):** 
                {', '.join(str(g) for g in guias_duplicadas_lista)}")
```

3. **Columna de enlaces a Odoo:**
```python
"odoo_url": st.column_config.LinkColumn(
    "Ver en Odoo",
    width="small",
    help="Click para abrir en Odoo",
    display_text="🔗 Abrir"
)
```

## 📊 Estructura de Datos

### Campos Agregados a la Respuesta del API

```json
{
  "id": 1234,
  "albaran": "ALB-001",
  "fecha": "2026-01-15",
  "productor": "Productor A",
  "guia_despacho": "GD-2024-001",
  "cantidad_pallets": 10,
  "total_kg": 500.0,
  "manejo": "Orgánico",
  "tipo_fruta": "Arándano",
  "origen": "RFP",
  "es_duplicada": true,  // ← NUEVO
  "odoo_url": "https://riofuturo.server98c6e.oerpondemand.net/web#id=1234&model=stock.picking&view_type=form"  // ← NUEVO
}
```

## 🎯 Casos de Uso

### Escenario 1: Guías Únicas
- No se muestra banner de advertencia
- Las guías aparecen sin icono ⚠️
- Enlaces a Odoo disponibles normalmente

### Escenario 2: Guías Duplicadas
1. Usuario consulta pallets en rango de fechas
2. Sistema detecta que "GD-2024-001" aparece 2 veces
3. Se muestra banner: `⚠️ 1 guía(s) duplicada(s) detectada(s): GD-2024-001`
4. En la tabla, todas las filas con "GD-2024-001" muestran: `⚠️ GD-2024-001`
5. Usuario puede hacer clic en "🔗 Abrir" para revisar cada recepción en Odoo

## 🧪 Pruebas

Se ha creado un script de prueba (`test_guias_duplicadas.py`) que simula el proceso completo:

**Resultados del test:**
```
Resumen de guias:
  GD-2024-001: 2 ocurrencia(s) - [!] DUPLICADA
  GD-2024-015: 2 ocurrencia(s) - [!] DUPLICADA
  GD-2024-030: 1 ocurrencia(s) - [OK] UNICA

[!] ADVERTENCIA: 2 guia(s) duplicada(s):
    GD-2024-001, GD-2024-015
```

## 🚀 Cómo Usar

1. **Navegar al Dashboard:**
   - Ir a: Dashboard de Recepciones → Tab "📦 Pallets por Recepción"

2. **Consultar Datos:**
   - Seleccionar rango de fechas
   - Elegir origen (RFP, VILKUN, SAN JOSE)
   - Clic en "🔍 Consultar Pallets"

3. **Revisar Duplicados:**
   - Si hay duplicados, aparecerá el banner de advertencia
   - Las filas con guías duplicadas tendrán el icono ⚠️

4. **Acceder a Odoo:**
   - Clic en "🔗 Abrir" en la columna "Ver en Odoo"
   - Se abre la recepción directamente en Odoo en una nueva pestaña

## 📝 Notas Técnicas

- **Performance:** La detección se realiza en memoria después de obtener datos de Odoo
- **Cache:** Los datos mantienen el TTL de 120 segundos del endpoint original
- **Filtros:** Los filtros de manejo y tipo de fruta se aplican ANTES de la detección de duplicados
- **URL Odoo:** Se obtiene dinámicamente desde la configuración del cliente Odoo

## ✅ Ventajas

1. **Detección Automática:** No requiere intervención manual
2. **Visual Intuitivo:** Fácil identificación de problemas
3. **Acceso Directo:** Un solo clic para ir a Odoo
4. **Información Completa:** Se mantienen todos los filtros y métricas existentes
5. **Sin Impacto en Performance:** Procesamiento ligero en memoria

## 🔄 Próximos Pasos (Opcional)

Si se requiere, se podrían agregar:
- [ ] Filtro específico para ver solo guías duplicadas
- [ ] Exportación de reporte de duplicados
- [ ] Notificaciones automáticas al detectar duplicados
- [ ] Histórico de guías duplicadas por período
