# G6 Graph Component

Componente de Streamlit para visualización de grafos usando AntV G6 con layout dagre (tipo Sankey).

## 🎯 Características

- ✅ **Layout Dagre**: Flujo automático tipo Sankey
- ✅ **Zoom/Pan**: Navegación fluida
- ✅ **Drag & Drop**: Arrastra nodos y canvas
- ✅ **Orientación flexible**: LR, RL, TB, BT
- ✅ **Edges proporcionales**: Grosor basado en `value`
- ✅ **Interactivo**: Click en nodos/edges
- ✅ **Performance**: Maneja 5000+ nodos

## 🚀 Build e Instalación

### 1. Instalar dependencias

```bash
cd components/g6_graph/frontend
npm install
```

### 2. Build para producción

```bash
npm run build
```

Esto genera `frontend/build/` que Streamlit usa automáticamente.

### 3. Desarrollo (opcional)

```bash
# Terminal 1: Frontend dev server
cd components/g6_graph/frontend
npm start

# Terminal 2: Streamlit (cambiar _RELEASE = False en __init__.py)
streamlit run pages/4_Rendimiento.py
```

## 📦 Uso en Python

```python
from components.g6_graph import g6_graph
from components.g6_graph.transformer import transform_sankey_to_g6

# Si tienes datos de Plotly Sankey
sankey_data = {
    "nodes": [
        {"label": "Nodo A", "color": "#5B8FF9"},
        {"label": "Nodo B", "color": "#5AD8A6"}
    ],
    "links": [
        {"source": 0, "target": 1, "value": 100}
    ]
}

# Transformar y renderizar
g6_data = transform_sankey_to_g6(sankey_data)

event = g6_graph(
    nodes=g6_data["nodes"],
    edges=g6_data["edges"],
    layout="dagre",
    direction="LR",  # Left-Right
    height=800
)

# Manejar clicks
if event:
    if event["type"] == "node_click":
        st.write(f"Clicked node: {event['node']['label']}")
```

## 🎨 Formato de datos

### Nodos
```python
{
    "id": "unique_id",
    "label": "Display name",
    "color": "#5B8FF9",
    "size": [150, 60]  # [width, height]
}
```

### Edges
```python
{
    "source": "node_id_1",
    "target": "node_id_2",
    "value": 100,        # Afecta grosor del edge
    "label": "100",
    "color": "#b5b5b5"
}
```

## 🔧 Configuración

### Dirección del flujo
- `LR`: Left to Right (default, como Sankey horizontal)
- `RL`: Right to Left
- `TB`: Top to Bottom (Sankey vertical)
- `BT`: Bottom to Top

### Layout
Usa internamente `dagre` con configuración optimizada para flujos tipo Sankey.

## 🐛 Troubleshooting

**Error: Component not found**
```bash
cd components/g6_graph/frontend
npm run build
```

**Nodos se superponen**
- Incrementa `nodesep` y `ranksep` en `G6Graph.jsx`
- Ajusta `size` de los nodos

**Performance con grafos grandes**
- G6 usa Canvas, maneja bien hasta 10k nodos
- Para grafos masivos, considera filtrar datos

## 📚 Referencias

- [AntV G6 Docs](https://g6.antv.antgroup.com/en/)
- [Dagre Layout](https://github.com/dagrejs/dagre)
- [Streamlit Components](https://docs.streamlit.io/library/components)
