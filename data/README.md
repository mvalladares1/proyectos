# Data compartida para Presupuesto

Este directorio centraliza los archivos Excel con los presupuestos que alimentan el dashboard del **Estado de Resultado**.

## Archivos esperados
- `BD_PPTO_2025.xlsx`
- `BD_PPTO_2026.xlsx`

El backend (ver `backend/services/presupuesto_service.py`) lee estos archivos directamente de `rio-futuro-dashboards/data/`. Si necesitas reemplazar el archivo oficial, sobrescribe el nombre correspondiente y vuelve a ejecutar el endpoint de carga o reinicia el backend.

## Buenas prácticas
1. Mantén una copia del archivo original antes de reemplazarlo.
2. Si el archivo viene desde SharePoint/Power BI, descarga el `.xlsx` y colócalo con el nombre correcto.
3. Usa la ruta absoluta `data/BD_PPTO_<AÑO>.xlsx` para identificar rápidamente la versión cargada.
4. Para cargas temporales (habilitado desde el dashboard), el backend guarda el archivo subido con la misma convención y responde con las hojas disponibles.

## Permisos de dashboards

El archivo `permissions.json` en esta carpeta contiene los accesos restringidos por dashboard. Cada clave corresponde a un slug (por ejemplo `estado_resultado`) y su lista asociada define qué correos pueden ver esa página. Agrega o elimina correos desde el panel de administración en `pages/99_🛠️_Permisos.py`.
