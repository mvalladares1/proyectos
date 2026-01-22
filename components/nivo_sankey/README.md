# Componente Nivo Sankey

Diagrama Sankey usando Nivo (React) para Streamlit con orientación **vertical**.

## Características

- ✅ **Orientación vertical nativa** - Flujo de arriba hacia abajo (proveedores → procesos → clientes)
- ✅ **Tooltips personalizados** - Información detallada en hover
- ✅ **Colores preservados** - Usa los mismos colores que el backend define
- ✅ **Animaciones suaves** - Transiciones nativas de Nivo
- ✅ **Sin dependencias Python** - Todo desde CDN (React + Nivo)

## Uso

```python
from components.nivo_sankey import render_nivo_sankey

# data debe tener el formato Plotly Sankey (se convierte automáticamente)
data = {
    "nodes": [
        {"label": "🏭 Proveedor", "color": "#9b59b6", "detail": {...}},
        ...
    ],
    "links": [
        {"source": 0, "target": 1, "value": 100, "color": "rgba(...)"},
        ...
    ]
}

render_nivo_sankey(data, height=800)
```

## Estructura de datos

### Entrada (formato Plotly)
- `nodes[].label`: Texto a mostrar
- `nodes[].color`: Color del nodo (hex o rgba)
- `nodes[].detail`: Metadata para tooltips
  - `type`: SUPPLIER, RECEPTION, PALLET_IN, PALLET_OUT, PROCESS, CUSTOMER
  - Campos específicos por tipo (date, qty, products, etc.)
- `links[].source`: Índice del nodo fuente
- `links[].target`: Índice del nodo destino
- `links[].value`: Cantidad (kg)
- `links[].color`: Color del link

### Salida (formato Nivo)
Se transforma automáticamente a:
- `nodes[].id`: String único
- `nodes[].nodeColor`: Color del nodo
- `nodes[].label`: Texto truncado si es muy largo
- `nodes[].metadata`: Info para tooltips
- `links[].source`: ID del nodo fuente (string)
- `links[].target`: ID del nodo destino (string)

## Configuración

### Layout
- `layout: 'vertical'` - Flujo de arriba hacia abajo
- `align: 'justify'` - Distribución balanceada
- `nodeThickness: 18` - Ancho de barras
- `nodeSpacing: 24` - Separación entre nodos

### Interactividad
- Hover sobre nodos: Muestra tooltip con metadata
- Animaciones: `motionConfig: 'gentle'`
- Link gradients: Activado para mejor visualización

## Limitaciones

1. **Interactividad unidireccional**: Los clicks en nodos NO actualizan session_state
2. **Bundle size**: ~150-200KB desde CDN (React + Nivo)
3. **Sin pan/zoom nativo**: Nivo no incluye controles de zoom (usar scroll del navegador)

## Versiones

- React: 18
- @nivo/core: 0.87.0
- @nivo/sankey: 0.87.0

## Comparación vs Plotly

| Característica | Plotly | Nivo |
|---------------|---------|------|
| Orientación vertical | ⚠️ Se corta/deforma | ✅ Nativo |
| Estética | ⚠️ Básica | ✅ Moderna |
| Tooltips | ✅ Buenos | ✅ Personalizables |
| Pan/Zoom | ✅ Incluido | ⚠️ Solo scroll |
| Bundle | ✅ Python only | ⚠️ ~200KB JS |
| Mantención | ✅ Fácil | ⚠️ Versiones CDN |
