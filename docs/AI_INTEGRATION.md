# Integración de IA para Resúmenes de Trazabilidad

## Descripción

Este sistema integra Ollama (modelo de IA local) para generar resúmenes inteligentes de datos de trazabilidad. El usuario puede generar un diagrama de trazabilidad y luego solicitar un resumen contextualizado generado por IA.

## Características

- **Resúmenes contextualizados** según el tipo de búsqueda:
  - Trazabilidad por proveedor
  - Trazabilidad por rango de fechas
  - Trazabilidad por pallet específico
  - Trazabilidad por guía de despacho
  - Trazabilidad por venta

- **Análisis inteligente** que incluye:
  - Flujo completo desde proveedores hasta clientes
  - Volúmenes y pesos procesados
  - Procesos de transformación
  - Fechas importantes
  - Observaciones relevantes

- **Modelo ligero y rápido**: Usa Llama 3.2, optimizado para respuestas rápidas

## Instalación de Ollama

### Linux

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS

```bash
brew install ollama
```

### Windows

Descarga el instalador desde: https://ollama.com/download/windows

## Configuración

### 1. Iniciar el servicio de Ollama

```bash
ollama serve
```

El servicio quedará escuchando en `http://localhost:11434`

### 2. Descargar el modelo Llama 3.2

```bash
ollama pull llama3.2
```

Este es un modelo pequeño (~2GB) optimizado para respuestas rápidas.

### Modelos alternativos

Si deseas usar un modelo diferente, puedes modificar el archivo `backend/services/ai_service.py`:

```python
class AIService:
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # <-- Cambiar aquí
```

Modelos recomendados:
- `llama3.2` - Pequeño y rápido (2GB)
- `llama3.1` - Más grande y preciso (4.7GB)
- `mistral` - Alternativa rápida (4.1GB)
- `phi3` - Ultra ligero (2.3GB)

## Uso

### 1. En el Dashboard de Trazabilidad

1. Genera un diagrama de trazabilidad usando cualquier modo de búsqueda
2. Verás aparecer una nueva sección **"🤖 Resumen Inteligente"**
3. Haz clic en **"✨ Generar Resumen"**
4. Espera de 5-10 segundos mientras la IA analiza los datos
5. El resumen aparecerá en un cuadro informativo

### 2. Tipos de Resúmenes

#### Por Proveedor
Analiza todas las recepciones, procesos y despachos relacionados con un proveedor en un rango de fechas.

#### Por Rango de Fechas
Proporciona un resumen ejecutivo de toda la actividad en el período, incluyendo volúmenes, proveedores y clientes.

#### Por Pallet
Traza el historial completo de un pallet específico desde su origen hasta su destino final.

#### Por Guía de Despacho
Resume la composición y origen de todos los productos en una guía específica.

#### Por Venta
Detalla el origen de los productos vendidos, procesos aplicados y fechas clave.

## Arquitectura

```
┌─────────────┐
│  Frontend   │
│  (Streamlit)│
└──────┬──────┘
       │
       │ POST /api/v1/containers/traceability/ai-summary
       │ { search_context, traceability_data }
       ↓
┌──────────────┐
│  Backend API │
│  (FastAPI)   │
└──────┬───────┘
       │
       │ generate_traceability_summary()
       ↓
┌──────────────┐
│  AI Service  │
│  (ai_service)│
└──────┬───────┘
       │
       │ POST /api/generate
       │ { model, prompt, options }
       ↓
┌──────────────┐
│   Ollama     │
│  (Local LLM) │
└──────────────┘
```

## Archivos Principales

### Backend

- **`backend/services/ai_service.py`**: Servicio principal de IA
  - Comunicación con Ollama
  - Construcción de prompts contextualizados
  - Extracción de estadísticas

- **`backend/routers/containers.py`**: Endpoint de API
  - `POST /api/v1/containers/traceability/ai-summary`
  - Validación de request
  - Manejo de errores

### Frontend

- **`pages/rendimiento/content.py`**: Integración en UI
  - Función `render_ai_summary()`
  - Botón de generación
  - Manejo de estado

## Troubleshooting

### Error: "No se pudo conectar con Ollama"

**Solución**: Verifica que Ollama esté corriendo:
```bash
ollama serve
```

### Error: "Modelo no encontrado"

**Solución**: Descarga el modelo:
```bash
ollama pull llama3.2
```

### Respuestas muy lentas

**Solución**: 
1. Usa un modelo más pequeño (phi3)
2. Reduce `num_predict` en `ai_service.py`
3. Verifica que tu CPU/GPU sea suficiente

### Respuestas de baja calidad

**Solución**:
1. Usa un modelo más grande (llama3.1)
2. Ajusta `temperature` en `ai_service.py`
3. Mejora los prompts en `_build_*_context()`

## Configuración Avanzada

### Ajustar parámetros del modelo

En `backend/services/ai_service.py`:

```python
response = await client.post(
    f"{self.ollama_url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,    # 0.0 = determinístico, 1.0 = creativo
            "top_p": 0.9,          # Muestreo nucleus
            "num_predict": 500,    # Máximo de tokens
        }
    }
)
```

### Personalizar prompts

Cada tipo de búsqueda tiene su propio método de construcción de prompt:

- `_build_sale_context()` - Para ventas
- `_build_date_range_context()` - Para rangos de fechas
- `_build_pallet_context()` - Para pallets
- `_build_guide_context()` - Para guías
- `_build_generic_context()` - Genérico

## Mejoras Futuras

- [ ] Soporte para streaming de respuestas
- [ ] Cache de resúmenes previos
- [ ] Exportación de resúmenes a PDF
- [ ] Comparación entre períodos
- [ ] Alertas automáticas basadas en IA
- [ ] Integración con sistema de notificaciones

## Recursos

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Llama 3.2 Model Card](https://ollama.com/library/llama3.2)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Streamlit Documentation](https://docs.streamlit.io/)

