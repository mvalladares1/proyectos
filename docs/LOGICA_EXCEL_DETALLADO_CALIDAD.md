# Lógica del Excel Detallado por Calidad

Este documento explica cómo el sistema genera el archivo **"Reporte de Calidad Detallado"** (Excel) en Recepciones.

## 1) Dónde se dispara en la UI

En la pestaña KPIs y Calidad, el botón **Generar Reporte de Calidad Detallado** llama al endpoint backend:

- [pages/recepciones/tab_kpis.py](pages/recepciones/tab_kpis.py#L858-L937)
- Endpoint llamado: `/api/v1/recepciones-mp/report-defectos.xlsx`

Parámetros enviados desde la UI:

- `username`, `password`
- `fecha_inicio`, `fecha_fin`
- `solo_hechas`
- `origen` (lista, por ejemplo: RFP, VILKUN, SAN JOSE)

## 2) Endpoint backend que genera el Excel

El endpoint está en:

- [backend/routers/recepcion.py](backend/routers/recepcion.py#L116-L156)

Este endpoint delega toda la lógica al servicio:

- `generar_reporte_defectos_excel(...)` en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L14-L415)

## 3) Flujo de datos (resumen)

1. Conecta a Odoo.
2. Detecta campos disponibles (por variaciones entre entornos Odoo/custom fields).
3. Busca recepciones (`stock.picking`) por origen y rango de fechas.
4. Busca movimientos realizados (`stock.move`) de esas recepciones.
5. Busca productos y templates para obtener variedad/manejo/categoría.
6. Busca controles de calidad (`quality.check`) de esas recepciones.
7. Cruza recepciones + QC + movimientos y construye filas del Excel.
8. Genera XLSX con formato y lo retorna al frontend.

## 4) Filtros y criterios de inclusión

### 4.1 Origen

Mapa de origen a `picking_type_id`:

- RFP -> 1
- VILKUN -> 217
- SAN JOSE -> 164

Implementado en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L183-L188).

### 4.2 Fecha

Para cada origen se consulta `stock.picking` con dominio sobre fechas:

- `date_done` **o** `scheduled_date` dentro de `[fecha_inicio, fecha_fin]`

Lógica en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L200-L207).

### 4.3 Estado

Si `solo_hechas=True`, se agrega:

- `state = done`

Lógica en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L210-L211).

### 4.4 Categoría de producto de recepción

Si existe el campo custom de categoría en picking, se filtra por:

- categoría de producto de la recepción = `MP`

Lógica en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L213-L215).

## 5) Cómo se obtiene la “calidad”

La calidad sale principalmente de `quality.check` (no de `stock.move`):

- Calificación final
- % IQF
- % BLOCK
- Temperatura
- Gramos de muestra
- Defectos (campos en gramos) según tipo de fruta

Lectura de campos en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L245-L259).

### Regla importante

Si una recepción **no tiene quality checks**, se excluye del reporte detallado de calidad:

- [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L300-L303)

## 6) Mapeo de defectos por tipo de fruta

El servicio tiene mapeos distintos por fruta porque Odoo guarda campos diferentes:

- Arándano
- Frambuesa
- Mora

Mapa en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L71-L138).

Esto determina qué campos leer para:

- Hongos/Pudrición
- Inmadura
- Sobremadura
- Daño mecánico
- Daño insecto
- Materias extrañas
- y defectos específicos (ej. pedicelos, golpe de sol, deterioro/rotura, etc.)

## 7) Cálculo de % Defectos

Para cada QC:

1. Toma `Total Defectos (g)`.
2. Si hay `Gramos Muestra > 0`:  
   `% Defectos = (Total Defectos (g) / Gramos Muestra) * 100`
3. Si no hay muestra, usa fallback con base 1000g.

Lógica en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L344-L350).

## 8) Cómo se construyen las filas del Excel

Por cada recepción y por cada `quality.check` asociado:

1. Toma todos los `stock.move` done del picking.
2. Por cada movimiento genera una fila de detalle de producto.
3. Excluye productos cuya categoría del template contiene `BANDEJA`.

Lógica en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L444-L462).

Campos clave por fila:

- Fecha, Proveedor, Guía, Origen, Albarán
- Producto, Variedad, Tipo Fruta, Manejo, Kg
- N° pallet, Calificación, % IQF, % BLOCK, Temperatura
- Gramos muestra, Total Defectos (g), % Defectos
- Defectos específicos (columnas en gramos)

Construcción del registro en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L470-L517).

## 9) Formato final del archivo

Se crea una hoja `Recepciones Defectos` con:

- Encabezado azul
- Bordes en todas las celdas
- Congelado de encabezado (`A2`)
- Ajuste automático de ancho por tipo de columna

Lógica en [backend/services/recepcion_defectos_service.py](backend/services/recepcion_defectos_service.py#L522-L598).

## 10) Consideraciones operativas

- El reporte está orientado a recepciones con QC (si no hay QC, no sale).
- El nivel de detalle es **por movimiento de producto** y **por quality check**.
- El mapeo de defectos depende del tipo de fruta reportado en QC.
- Existe código auxiliar para leer defectos desde líneas one2many, pero el flujo actual usa principalmente campos directos en `quality.check`.
