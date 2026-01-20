# 📊 Stock Teórico Anual

## 🎯 Objetivo del Módulo

Este módulo proporciona un **análisis multi-anual de stock teórico** calculado a partir de compras, ventas y merma histórica por tipo de fruta y manejo.

## 🔍 ¿Qué Resuelve?

El módulo responde a las siguientes preguntas críticas de negocio:

1. **¿Cuánta fruta compré por año, tipo y manejo?**
   - Cantidad en kg
   - Monto total invertido
   - Precio promedio por kg

2. **¿Cuánto debería tener en stock a fin de año?**
   - Stock teórico = Compras - Ventas - Merma
   - Proyección basada en datos históricos reales

3. **¿Cuál es mi merma histórica real?**
   - % de merma calculado automáticamente
   - Distribuido proporcionalmente entre años
   - Por tipo de fruta y manejo

4. **¿Cómo evoluciona mi negocio año tras año?**
   - Comparativa multi-anual
   - Gráficos de tendencias
   - Análisis de precios

## 📋 Requisitos del Jefe (Implementados)

✅ **Dashboard de facturas** de diarios de cliente y proveedores  
✅ **Filtrado por categoría** de productos (tipo de fruta + manejo)  
✅ **Filtrado por año** (selector multi-año: 2023, 2024, 2025, 2026)  
✅ **Cantidad de kg y monto total** por cada combinación  
✅ **Precio promedio por kg** (división monto/kg)  
✅ **Corte especial hasta 31 de octubre** (configurable)  
✅ **Cálculo de merma histórica** y distribución entre años  
✅ **Stock teórico a fin de año** por tipo y manejo  

## 🛠️ Funcionalidades

### 1. Selector de Configuración

- **Años a Analizar**: Selección múltiple (ej: 2024, 2025, 2026)
- **Fecha de Corte**: Mes y día configurable (default: 31 octubre)
- **Carga bajo demanda**: Botón "Cargar Análisis"

### 2. Resumen General Consolidado

Métricas globales de todos los años seleccionados:

- Total Compras (kg y $)
- Total Ventas (kg y $)
- Total Merma (kg y %)
- Stock Teórico Total ($)

### 3. Análisis Detallado por Año

Para cada año seleccionado, se muestra:

#### Métricas del Año
- Compras totales con precio promedio
- Ventas totales con precio promedio
- Merma calculada (kg y %)
- Stock teórico valorizado

#### Tabla Detallada por Tipo y Manejo
Cada fila muestra:
- Tipo de fruta
- Tipo de manejo
- Compras (kg, $, $/kg)
- Ventas (kg, $, $/kg)
- Merma (kg, %)
- Stock Teórico ($)

#### Gráficos
- **Pie Chart**: Distribución de compras por tipo de fruta
- **Barras Agrupadas**: Comparación Compras vs Ventas vs Merma

### 4. Comparativa Multi-Anual

- **Gráfico de Evolución**: Líneas de tiempo mostrando compras, ventas y merma
- **Tabla Comparativa**: Totales por año con % de merma
- **Evolución de Precios**: Por tipo de fruta seleccionado

## 🔢 Cálculos

### Stock Teórico
```
Stock Teórico = Compras - Ventas - Merma
```

### Merma
```
Merma (kg) = Compras (kg) - Ventas (kg)  [cuando es positivo]
Merma (%) = (Merma kg / Compras kg) × 100
```

### Precio Promedio
```
Precio $/kg = Monto Total / Cantidad Total (kg)
```

### Merma Histórica
```
% Merma Histórico = Σ(Merma kg de todos los años) / Σ(Compras kg de todos los años) × 100
```

## 📊 Estructura de Datos

### Backend Service
`backend/services/analisis_stock_teorico_service.py`

Métodos principales:
- `get_analisis_multi_anual(anios, fecha_corte)`: Análisis completo
- `_get_compras_por_tipo_manejo()`: Obtiene compras agrupadas
- `_get_ventas_por_tipo_manejo()`: Obtiene ventas agrupadas
- `_consolidar_datos()`: Calcula métricas derivadas

### Frontend
`pages/rendimiento/tab_analisis_completo.py`

Componentes:
- `render()`: Función principal
- `_render_anio_detalle()`: Detalle por año
- `_render_comparativa_multianual()`: Gráficos comparativos

### API Endpoint
```
GET /api/v1/rendimiento/stock-teorico-anual
```

Parámetros:
- `username`: Usuario Odoo
- `password`: API Key
- `anios`: Años separados por coma (ej: "2024,2025,2026")
- `fecha_corte`: Mes-Día (ej: "10-31")

Respuesta:
```json
{
  "anios_analizados": [2024, 2025, 2026],
  "fecha_corte": "10-31",
  "merma_historica_pct": 6.5,
  "resumen_general": {
    "total_compras_kg": 500000,
    "total_compras_monto": 1200000000,
    "precio_promedio_compra_global": 2400,
    "total_ventas_kg": 450000,
    "total_ventas_monto": 1800000000,
    "precio_promedio_venta_global": 4000,
    "total_merma_kg": 50000,
    "pct_merma_historico": 10,
    "total_stock_teorico_valor": 120000000
  },
  "por_anio": {
    "2024": {
      "anio": 2024,
      "fecha_desde": "2024-01-01",
      "fecha_hasta": "2024-10-31",
      "datos": [
        {
          "tipo_fruta": "FRESA",
          "manejo": "ORGANICO",
          "compras_kg": 50000,
          "compras_monto": 120000000,
          "precio_promedio_compra": 2400,
          "ventas_kg": 45000,
          "ventas_monto": 180000000,
          "precio_promedio_venta": 4000,
          "merma_kg": 5000,
          "merma_pct": 10,
          "stock_teorico_kg": 5000,
          "stock_teorico_valor": 12000000
        }
      ]
    }
  }
}
```

## 🚀 Uso

1. **Acceder al Módulo**:
   - Ir a: Trazabilidad Productiva > 📊 Stock Teórico Anual

2. **Configurar Análisis**:
   - Seleccionar años a analizar (múltiples)
   - Ajustar fecha de corte si es necesario
   - Presionar "🔄 Cargar Análisis"

3. **Revisar Resultados**:
   - Ver resumen general consolidado
   - Explorar cada año en pestañas individuales
   - Analizar comparativa multi-anual

4. **Exportar/Descargar**:
   - Hacer screenshot de gráficos
   - Copiar datos de tablas

## 📝 Notas Técnicas

### Categorías de Productos

**Compras (MP/PSP)**:
- `PRODUCTOS / MP` (Materia Prima)
- `PRODUCTOS / PSP` (Pre-Semi Procesado)

**Ventas (PTT/Retail)**:
- `PRODUCTOS / PTT` (Producto Terminado Transformado)
- `PRODUCTOS / RETAIL`
- `PRODUCTOS / SUBPRODUCTO`

### Campos Odoo Utilizados

- `x_studio_sub_categora`: Tipo de fruta
- `x_studio_categora_tipo_de_manejo`: Tipo de manejo
- `categ_id`: Categoría del producto

### Lógica de Fechas

- **Años pasados**: Desde 01-ene hasta fecha corte (ej: 31-oct)
- **Año actual**: Desde 01-ene hasta MIN(fecha corte, hoy)
- **Años futuros**: Desde 01-ene hasta fecha corte

### Simplificaciones

El cálculo de **Stock Teórico** es simplificado:

```
Stock Teórico = Merma = Compras - Ventas
```

En un sistema completo debería ser:
```
Stock Teórico = Stock Inicial + Compras - Ventas - Merma Real
```

Pero como no se tiene stock inicial histórico, se asume que la diferencia entre compras y ventas representa el stock remanente + merma.

## 🔮 Mejoras Futuras

1. **Stock Inicial Real**: Integrar con inventario físico de inicio de año
2. **Merma por Ubicación**: Desglosar merma por bodega/cámara
3. **Exportación Excel**: Descargar datos completos
4. **Alertas Automáticas**: Notificar cuando merma > umbral
5. **Proyección Futura**: Machine learning para predecir merma futura
6. **Costos Reales**: Integrar costos de producción/almacenamiento

## 📞 Soporte

Para dudas o mejoras, contactar al equipo de desarrollo.

---

**Última actualización**: Enero 2026  
**Versión**: 1.0  
**Módulo**: Trazabilidad Productiva > Stock Teórico Anual
