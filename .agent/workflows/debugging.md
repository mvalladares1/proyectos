---
description: Estándar de debugging para el proyecto Dashboard Rio Futuro
---

# Estándares de Debugging

Este documento describe las prácticas recomendadas para realizar debugging en el proyecto siguiendo los estándares de la industria.

## 1. Uso del Módulo `logging` de Python

En lugar de usar `print()`, utiliza el módulo `logging` estándar de Python:

```python
import logging

# Configuración básica al inicio del archivo
logger = logging.getLogger(__name__)

# Niveles de logging (de menor a mayor severidad):
logger.debug("Información detallada para diagnóstico")
logger.info("Confirmación de que las cosas funcionan")
logger.warning("Algo inesperado, pero el programa sigue funcionando")
logger.error("Error que impide ejecutar alguna función")
logger.critical("Error grave que puede detener el programa")
```

## 2. Configuración Centralizada del Logging

Configura el logging en un archivo central (ej: `config/logging_config.py`):

```python
import logging
import os

def setup_logging():
    level = logging.DEBUG if os.getenv("DEBUG") == "true" else logging.INFO
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
```

## 3. Variables de Entorno para Control

Usa variables de entorno para habilitar/deshabilitar debug:

```bash
# En .env
DEBUG=true
LOG_LEVEL=DEBUG
```

```python
# En el código
import os
DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    logger.debug(f"Datos recibidos: {data}")
```

## 4. Archivos de Debug Temporales

Si necesitas crear scripts de debug temporales:

1. **Nombrarlos claramente**: `debug_nombre_funcionalidad.py`
2. **Documentar su propósito** al inicio del archivo
3. **Eliminarlos antes de hacer commit** a la rama principal
4. **Añadirlos a `.gitignore`** si son solo locales:
   ```
   debug_*.py
   ```

## 5. Buenas Prácticas

### ✅ Hacer:
- Usar logging en lugar de print
- Configurar niveles apropiados (DEBUG vs INFO vs ERROR)
- Incluir contexto útil en los mensajes
- Usar f-strings para formatear mensajes de log
- Limpiar código de debug antes de merge a producción

### ❌ Evitar:
- Dejar `print()` en código de producción
- Loggear información sensible (contraseñas, tokens)
- Loggear en loops muy frecuentes sin control
- Dejar archivos `debug_*.py` en el repositorio

## 6. Ejemplo de Implementación Correcta

```python
import logging
import os

logger = logging.getLogger(__name__)

class MiServicio:
    def procesar_datos(self, datos):
        logger.debug(f"Iniciando procesamiento de {len(datos)} registros")
        
        try:
            resultado = self._transformar(datos)
            logger.info(f"Procesados {len(resultado)} registros exitosamente")
            return resultado
        except Exception as e:
            logger.error(f"Error procesando datos: {e}", exc_info=True)
            raise
```

## 7. Debugging en Streamlit

Para aplicaciones Streamlit, usa `st.write()` o `st.text()` para debug visual:

```python
import streamlit as st
import os

DEBUG = os.getenv("DEBUG", "false").lower() == "true"

if DEBUG:
    with st.expander("🔍 Debug Info"):
        st.json(data)
```

## 8. Herramientas Recomendadas

- **pdb/ipdb**: Debugger interactivo de Python
- **debugpy**: Para debugging remoto (VS Code)
- **rich**: Para logging con formato enriquecido en terminal
