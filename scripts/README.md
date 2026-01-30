# Scripts de Utilidades

Este directorio contiene scripts de utilidades organizados por categoría.

## 📁 Estructura Principal

### 📊 analisis/
Scripts para análisis de datos y procesos de negocio
- Análisis de automatizaciones y aprobaciones
- Análisis de defectos de calidad
- Comparaciones de OCs transportes vs calidad
- Análisis de ventas, insumos y valorización
- Análisis de rutas y campos de Odoo

### ✅ aprobaciones/
Scripts de gestión y configuración de aprobaciones
- Activación de aprobadores (Felipe, Francisco, Maximo)
- Auditorías de automatizaciones
- Búsqueda exhaustiva de reglas de aprobación
- Soluciones de problemas de aprobación
- Verificación de actividades de usuarios

### 🧹 limpieza_ocs/
Scripts de limpieza y mantenimiento de OCs
- Limpieza de actividades de transportes
- Limpieza de aprobadores de servicios
- Limpieza de OCs específicas (12332, 12393)
- Limpieza de RFQs y tier reviews

### 📦 ocs_especificas/
Scripts para troubleshooting de OCs específicas
- Asignaciones puntuales de aprobadores
- Correcciones de acciones específicas
- Confirmaciones directas de OCs
- Investigaciones de problemas
- Lectura de checks (check1, check2)

### 🚚 transportes/
Scripts de configuración de transportes y fletes
- Activación de automatizaciones de transportes
- Actualización masiva de OCs de transportes
- Creación de reglas y automatizaciones
- Configuración de aprobadores (Francisco, Maximo)
- Gestión de flujos completos
- Modificación de tiers y exclusiones

### ✔️ verificacion/
Scripts de verificación y monitoreo del sistema
- Verificación de actividades y aprobaciones
- Verificación de campos de modelos
- Verificación de conexiones (MO, MOCs)
- Verificación de facturas y cuentas
- Verificación de deduplic ación
- Visualización de estados

## 📁 Subcarpetas de Utilidades

### utilidades/busqueda/
Búsqueda y exploración de datos
- Búsqueda de campos de calidad
- Búsqueda de productos no estandarizados
- Búsqueda de quants en paquetes

### utilidades/configuracion_modelos/
Configuración y creación de modelos Odoo
- Completar modelos
- Configurar modelos de transferencias
- Recrear modelos completos

### utilidades/diagnosticos/
Diagnósticos del sistema y listados
- Diagnóstico de producción
- Listados de conceptos contables (110, 1103, 111)

### utilidades/exportadores/
Exportación de datos a Excel
- Exportar insumos de paletización
- Exportar insumos de servicios
- Exportar stock teórico
- Generar reportes de recepciones

### utilidades/fixes/
Correcciones y arreglos específicos
- Fix de reglas de aprobación de Maximo
- Fix de paquetes y quants negativos
- Fix de price_unit en OCs
- Corrección de menús y acciones

### utilidades/gestion_stock/
Gestión de stock y paquetes
- Mover pallets directamente
- Reasignar quants a paquetes

### utilidades/investigacion/
Investigación de problemas
- Investigar categorías FCXE
- Investigar facturas faltantes
- Investigar facturas de ventas

### utilidades/menus/
Gestión de menús de Odoo
- Actualizar menús de logs
- Crear menús de aplicación
- Limpiar menús duplicados
- Hacer menús visibles

### utilidades/varios/
Scripts varios y misceláneos
- Agregar campos faltantes
- Configurar permisos
- Ejemplo de conexión Odoo
- Reconciliaciones programadas
- Limpieza de campos de logs

## ⚠️ Nota Importante

Estos scripts son principalmente para:
- 🔧 Debugging y troubleshooting
- 📊 Análisis de datos puntuales
- ⚙️ Configuración y mantenimiento
- 🚑 Correcciones de emergencia

**El código de producción está en:**
- `pages/` - Dashboards de Streamlit
- `backend/` - API de FastAPI
- `shared/` - Código compartido
- `components/` - Componentes reutilizables

## 🚀 Uso

La mayoría de estos scripts se ejecutan directamente:

```bash
python scripts/analisis/analizar_automatizaciones_aprobacion.py
python scripts/transportes/actualizar_todas_ocs_transportes.py
python scripts/verificacion/visualizar_aprobaciones_maximo_completo.py
```

Algunos requieren credenciales de Odoo, que suelen estar hardcodeadas en el script.
