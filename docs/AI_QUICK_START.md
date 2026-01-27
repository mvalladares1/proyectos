# 🤖 Guía Rápida: Resúmenes de IA para Trazabilidad

## Configuración Inicial (Solo una vez)

### 1. Instalar Ollama

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

**Windows:**
Descargar desde: https://ollama.com/download/windows

### 2. Iniciar Ollama

```bash
ollama serve
```

Deja esta terminal abierta. Ollama quedará corriendo en segundo plano.

### 3. Descargar el Modelo

En otra terminal:
```bash
ollama pull llama3.2
```

Esto descargará ~2GB. Solo se hace una vez.

### 4. Probar la Instalación

```bash
cd /home/feli/proyectos
python scripts/test_ollama_integration.py
```

Si ves "✅ Todas las pruebas pasaron exitosamente", ¡estás listo!

## Uso Diario

### 1. Asegúrate de que Ollama esté corriendo

```bash
# Ver si Ollama está activo
ps aux | grep ollama

# Si no está activo, iniciarlo
ollama serve
```

### 2. Usar en el Dashboard

1. Ve a **Rendimiento → Trazabilidad**
2. Genera un diagrama (cualquier tipo de búsqueda)
3. Verás la sección **"🤖 Resumen Inteligente"** debajo del diagrama
4. Haz clic en **"✨ Generar Resumen"**
5. Espera 5-10 segundos
6. ¡Listo! Verás un resumen detallado generado por IA

## Ejemplos de Resúmenes

### Por Proveedor
```
Resumen de Trazabilidad - Proveedor: FELIPE ANDRES ASIAIN RIFFO

Del 1 al 31 de diciembre de 2025, se recibieron 12 pallets de este proveedor
con un peso total de 2,458 kg. Los productos pasaron por 3 procesos de 
transformación: limpieza, clasificación y empaque. El 85% fue despachado 
a NATURIN LTD entre el 15 y 28 de diciembre. Se observa un tiempo promedio 
de procesamiento de 4 días desde recepción hasta despacho.
```

### Por Rango de Fechas
```
Análisis del Período: 15-30 Diciembre 2025

Actividad de Recepciones:
- 45 recepciones de 8 proveedores diferentes
- Peso total ingresado: 12,340 kg
- Principales proveedores: AGRICOLA LA CORTINA (35%), AGRICOLA COX (22%)

Producción:
- 67 procesos de transformación ejecutados
- Eficiencia: 95% (merma de 5%)

Despachos:
- 38 ventas completadas
- 3 clientes principales: NATURIN LTD, WALMART, TOTTUS
- Peso despachado: 11,723 kg
```

### Por Pallet
```
Trazabilidad Detallada - Pallet PACK000742-C

Origen:
- Proveedor: SOCIEDAD AGRICOLA DEL HUERTO LTDA
- Recepción: 22-12-2025 (RF/RFP/IN/00510)
- Peso inicial: 485 kg

Transformación:
- Proceso 1: Limpieza y desinfección (23-12-2025)
- Proceso 2: Clasificación por calibre (24-12-2025)  
- Proceso 3: Empaque en bins (24-12-2025)

Destino:
- Cliente: NATURIN LTD
- Despacho: 28-12-2025 (RF/RFP/OUT/00733)
- Peso final: 460 kg
- Tiempo total en planta: 6 días
```

## Consejos

- **Primera vez es más lenta**: La primera generación puede tardar 15-20 segundos. Las siguientes son más rápidas.
- **Resumen se mantiene**: Una vez generado, el resumen se guarda en la sesión. No necesitas regenerarlo si cambias de pestaña.
- **Modelos alternativos**: Si tienes buena computadora, prueba `llama3.1` para resúmenes más detallados.

## Solución de Problemas

### "No se pudo conectar con Ollama"
```bash
# Iniciar Ollama
ollama serve
```

### "Modelo no encontrado"
```bash
# Descargar el modelo
ollama pull llama3.2
```

### Respuestas muy lentas
```bash
# Usa un modelo más pequeño
ollama pull phi3
```

Luego edita `backend/services/ai_service.py` línea 13:
```python
self.model = "phi3"  # En lugar de "llama3.2"
```

## Recursos

- Documentación completa: `docs/AI_INTEGRATION.md`
- Script de prueba: `scripts/test_ollama_integration.py`
- Servicio de IA: `backend/services/ai_service.py`
- Endpoint API: `backend/routers/containers.py`

## Soporte

Si tienes problemas:
1. Ejecuta el script de prueba: `python scripts/test_ollama_integration.py`
2. Revisa los logs de Ollama: `journalctl -u ollama -f` (Linux)
3. Verifica que el puerto 11434 no esté ocupado: `lsof -i :11434`

