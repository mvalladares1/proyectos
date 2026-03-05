# PROMPT COMPLETO: Migración de "Automatización OF" a React

## CONTEXTO GENERAL

Este documento describe **toda la lógica** del tab "Automatización OF" dentro del dashboard de Producción. El sistema está construido actualmente con **Streamlit** (Python) en el frontend y **FastAPI** (Python) + **Odoo ERP** (XML-RPC) en el backend. El objetivo es replicar esta funcionalidad en **React + TypeScript**.

El tab permite a operarios de planta **agregar pallets a una orden de fabricación (MO) o transferencia (stock.picking) existente**, ya sea como **componentes** (materia prima de entrada) o como **subproductos** (producto terminado de salida).

---

## ARQUITECTURA DEL SISTEMA

```
┌─────────────────────────────────────────┐
│         FRONTEND (React)                │
│  AutomatizacionOfTab component          │
│  - Buscar orden por nombre              │
│  - Seleccionar tipo (comp/subprod)      │
│  - Escanear/pegar códigos de pallets    │
│  - Validar pallets                      │
│  - Confirmar y agregar                  │
└──────────────┬──────────────────────────┘
               │ HTTP (REST API)
┌──────────────▼──────────────────────────┐
│      BACKEND (FastAPI)                  │
│  Router: /api/v1/automatizaciones/      │
│  - GET  /procesos/buscar-orden          │
│  - POST /procesos/validar-pallets       │
│  - POST /procesos/agregar-pallets       │
└──────────────┬──────────────────────────┘
               │ XML-RPC
┌──────────────▼──────────────────────────┐
│         ODOO ERP (v16)                  │
│  Modelos:                               │
│  - mrp.production                       │
│  - stock.picking                        │
│  - stock.move                           │
│  - stock.move.line                      │
│  - stock.quant.package                  │
│  - stock.quant                          │
│  - stock.lot                            │
│  - product.product                      │
└─────────────────────────────────────────┘
```

---

## FLUJO DE USUARIO (4 PASOS)

### Paso 1: Buscar Orden de Fabricación
- El usuario ingresa un nombre de orden (ej: `MO/RF/00123`, `WH/Transf/00936`, o solo `123`).
- El input se convierte a **MAYÚSCULAS** automáticamente.
- Se llama al endpoint `GET /procesos/buscar-orden?orden=XXX`.
- Se muestra la info de la orden encontrada: nombre, producto, estado, conteo de componentes, conteo de subproductos, cantidad total.
- Si la orden es un `stock.picking` (transferencia), se muestra como "Transferencia".

### Paso 2: Seleccionar Tipo de Movimiento
- Si la orden es **mrp.production** → el usuario elige entre:
  - **Componentes** (🔵): Materia prima de entrada → se agregan a `move_raw_ids`
  - **Subproductos** (🟢): Producto terminado de salida → se agregan a `move_finished_ids`
- Si la orden es **stock.picking** → automáticamente es "componentes" (movimientos directos). Se muestra un mensaje info.

### Paso 3: Escanear/Pegar Pallets
- Textarea donde el usuario puede:
  - Escanear con pistola de código de barras (un pallet por línea)
  - Pegar múltiples códigos separados por saltos de línea
- Los códigos se convierten a **MAYÚSCULAS** automáticamente.
- **Normalización**: Si empieza con `PAC` pero NO con `PACK`, se convierte a `PACK` + resto (ej: `PAC0009900` → `PACK0009900`).
- Se eliminan **duplicados** contra pallets ya validados en la lista.
- Al hacer clic en "Validar y Agregar", se llama al endpoint `POST /procesos/validar-pallets`.
- Los pallets válidos se agregan a una lista visual.
- Los inválidos muestran errores individuales.

### Paso 4: Confirmar y Agregar
- Se muestra resumen: total pallets, total kg.
- Cada pallet muestra: código, kg, lote, producto.
- Se puede eliminar pallets individuales de la lista.
- Se puede limpiar toda la lista.
- Al confirmar, se llama a `POST /procesos/agregar-pallets`.
- Se muestra resultado: pallets agregados, kg totales, errores si los hay.
- El resultado persiste en pantalla hasta que el usuario lo cierre.

---

## ENDPOINTS DEL BACKEND (DETALLE COMPLETO)

### 1. `GET /api/v1/automatizaciones/procesos/buscar-orden`

**Parámetros query:**
- `orden` (string): Nombre o número de la orden
- `username` (string): Usuario Odoo
- `password` (string): API Key Odoo

**Lógica:**
1. Buscar primero en `mrp.production` con `('name', 'ilike', orden)`, limit=1, order='create_date desc'
2. Si se encuentra, devolver:
   ```json
   {
     "success": true,
     "orden": {
       "id": 123,
       "nombre": "MO/RF/00123",
       "producto": "Salmón Fresco 10kg",
       "producto_id": 456,
       "cantidad": 1000.0,
       "estado": "progress",
       "componentes_count": 5,
       "subproductos_count": 2,
       "modelo": "mrp.production"
     }
   }
   ```
3. Si no se encontró en mrp.production, buscar en `stock.picking` con el mismo dominio
4. Si se encuentra picking, devolver con `modelo: "stock.picking"`:
   ```json
   {
     "success": true,
     "orden": {
       "id": 789,
       "nombre": "WH/Transf/00936",
       "producto": "Transferencia Interna",
       "producto_id": null,
       "cantidad": 3,
       "estado": "assigned",
       "componentes_count": 3,
       "subproductos_count": 0,
       "modelo": "stock.picking"
     }
   }
   ```
5. Si no se encontró nada: `{"success": false, "error": "Orden \"XXX\" no encontrada..."}`

**Campos leídos de Odoo:**
- `mrp.production`: `['name', 'product_id', 'product_qty', 'state', 'move_raw_ids', 'move_finished_ids', 'create_date']`
- `stock.picking`: `['name', 'state', 'location_id', 'location_dest_id', 'move_ids', 'picking_type_id', 'create_date']`

---

### 2. `POST /api/v1/automatizaciones/procesos/validar-pallets`

**Parámetros query:**
- `username`, `password`

**Body JSON:**
```json
{
  "pallets": ["PACK0009900", "PACK0009901"],
  "tipo": "componentes",
  "orden_id": 123
}
```

**Lógica detallada:**

1. **Obtener pallets ya existentes en la orden** para evitar duplicados:
   - Si `mrp.production`: buscar move_lines de `move_raw_ids` (componentes) o `move_finished_ids` (subproductos) → extraer `package_id` y `result_package_id`
   - Si `stock.picking`: buscar move_lines de `move_ids` → extraer `package_id` y `result_package_id`
   - Guardarlos en un set `pallets_ya_en_orden`

2. **Para cada código de pallet:**
   a. Normalizar: mayúsculas, `PAC→PACK`
   b. Buscar en `stock.quant.package` por `('name', '=', codigo_normalizado)`
   c. Si no existe → error "Package no encontrado"
   d. Verificar si `package_id` ya está en la orden → error "Ya está ingresado en esta orden"
   e. Buscar `stock.quant` con `('package_id', '=', package_id)` y `('quantity', '>', 0)` → limit=1
   f. Si no hay quant con stock → error "Sin stock disponible (0 KG)"
   g. Si `quantity <= 0` → error "Pallet con 0 KG - no se puede agregar"
   h. Si todo OK, devolver:
   ```json
   {
     "codigo": "PACK0009900",
     "valido": true,
     "kg": 850.5,
     "producto_id": 456,
     "producto_nombre": "Salmón AT Fresco 10kg",
     "lote_id": 789,
     "lote_nombre": "20260301-001",
     "ubicacion_id": 100,
     "package_id": 1234
   }
   ```

**Respuesta:**
```json
{
  "pallets": [
    { "codigo": "PACK0009900", "valido": true, "kg": 850.5, ... },
    { "codigo": "PACK0009901", "valido": false, "error": "Sin stock disponible (0 KG)" }
  ]
}
```

---

### 3. `POST /api/v1/automatizaciones/procesos/agregar-pallets`

**Parámetros query:**
- `username`, `password`

**Body JSON:**
```json
{
  "orden_id": 123,
  "tipo": "componentes",
  "modelo": "mrp.production",
  "pallets": [
    {
      "codigo": "PACK0009900",
      "kg": 850.5,
      "lote_id": 789,
      "lote_nombre": "20260301-001",
      "producto_id": 456,
      "ubicacion_id": 100,
      "package_id": 1234
    }
  ]
}
```

**Lógica detallada según caso:**

#### Constantes importantes:
```python
UBICACION_VIRTUAL_CONGELADO_ID = 8485  # Para órdenes con "RF" en el nombre
UBICACION_VIRTUAL_PROCESOS_ID = 15     # Para el resto
UOM_KG_ID = 12  # product_uom para kilogramos
```

#### Determinación de ubicación virtual:
```
Si "RF" está en el nombre de la orden → UBICACION_VIRTUAL_CONGELADO_ID (8485)
Sino → UBICACION_VIRTUAL_PROCESOS_ID (15)
```

---

#### CASO A: stock.picking (Transferencias)

Para cada pallet:
1. **Buscar/crear lote** (`stock.lot`):
   - Buscar `('name', '=', lote_nombre)` AND `('product_id', '=', producto_id)`
   - Si no existe → crear `stock.lot` con `{name, product_id, company_id: 1}`

2. **Buscar/crear package** (`stock.quant.package`):
   - Buscar `('name', '=', codigo)`
   - Si no existe → crear `stock.quant.package` con `{name: codigo, company_id: 1}`

3. **Buscar/crear stock.move**:
   - Buscar move existente: `('picking_id', '=', orden_id)` AND `('product_id', '=', producto_id)` AND `('state', '!=', 'cancel')`
   - Si existe → reutilizar `move_id`
   - Si no existe → crear:
     ```python
     {
       'name': mo_name,
       'product_id': producto_id,
       'product_uom_qty': kg,
       'product_uom': 12,  # kg
       'location_id': orden['location_id'][0],
       'location_dest_id': orden['location_dest_id'][0],
       'state': 'draft',
       'picking_id': orden_id,
       'company_id': 1,
       'reference': mo_name
     }
     ```

4. **Crear stock.move.line** (sin reservar):
   ```python
   {
     'move_id': move_id,
     'product_id': producto_id,
     'qty_done': kg,
     'product_uom_id': 12,
     'location_id': orden['location_id'][0],
     'location_dest_id': orden['location_dest_id'][0],
     'state': 'draft',
     'reference': mo_name,
     'company_id': 1,
     'lot_id': lote_id,          # si existe
     'package_id': package_id     # si existe
   }
   ```

---

#### CASO B: Componentes (move_raw_ids) - mrp.production

Para cada pallet:
1. **Buscar/crear lote** (igual que caso A)
2. **Buscar/crear package** (igual que caso A)
3. **Buscar/crear stock.move**:
   - Buscar existente: `('raw_material_production_id', '=', orden_id)` AND `('product_id', '=', producto_id)` AND `('state', '!=', 'cancel')`
   - Si no existe → crear:
     ```python
     {
       'name': mo_name,
       'product_id': producto_id,
       'product_uom_qty': kg,
       'product_uom': 12,
       'location_id': ubicacion_id or orden['location_src_id'][0],
       'location_dest_id': ubicacion_virtual,  # 8485 o 15
       'state': 'draft',
       'raw_material_production_id': orden_id,
       'company_id': 1,
       'reference': mo_name
     }
     ```
   - NOTA: `raw_material_production_id` es la clave que lo vincula como componente

4. **Crear stock.move.line** (sin reservar):
   ```python
   {
     'move_id': move_id,
     'product_id': producto_id,
     'qty_done': kg,
     'product_uom_id': 12,
     'location_id': ubicacion_id or orden['location_src_id'][0],
     'location_dest_id': ubicacion_virtual,
     'state': 'draft',
     'reference': mo_name,
     'company_id': 1,
     'lot_id': lote_id,       # si existe
     'package_id': package_id  # si existe
   }
   ```

---

#### CASO C: Subproductos (move_finished_ids) - mrp.production

**Este caso es el más complejo.** Para cada pallet:

1. **Buscar producto congelado** (transformación de código):
   - Leer `default_code` del producto original
   - Si el código empieza con `'1'` → reemplazar por `'2'` (ej: `1234567` → `2234567`)
   - Buscar `product.product` con `('default_code', '=', codigo_congelado)`
   - Si se encuentra → usar ese producto como `producto_output_id`
   - Si no → usar el producto original

2. **Generar lote con sufijo `-C`**:
   - `lote_output_name = f"{lote_nombre}-C"`
   - Buscar `stock.lot` con `('name', '=', lote_output_name)` AND `('product_id', '=', producto_output_id)`
   - Si no existe → crear

3. **Generar package con sufijo `-C`**:
   - Extraer el número del código: si empieza con `PACK` → `numero = codigo[4:]`, si `PAC` → `numero = codigo[3:]`, sino `numero = codigo`
   - `package_output_name = f"PACK{numero}-C"`
   - Buscar `stock.quant.package` con `('name', '=', package_output_name)`
   - Si no existe → crear

4. **Buscar/crear stock.move**:
   - Buscar existente: `('production_id', '=', orden_id)` AND `('product_id', '=', producto_output_id)` AND `('state', '!=', 'cancel')`
   - Si no existe → crear:
     ```python
     {
       'name': mo_name,
       'product_id': producto_output_id,
       'product_uom_qty': kg,
       'product_uom': 12,
       'location_id': ubicacion_virtual,
       'location_dest_id': orden['location_dest_id'][0],
       'state': 'draft',
       'production_id': orden_id,  # NOTA: production_id (no raw_material_production_id)
       'company_id': 1,
       'reference': mo_name
     }
     ```
   - NOTA: `production_id` es la clave que lo vincula como subproducto/producto terminado

5. **Crear stock.move.line** con `result_package_id`:
   ```python
   {
     'move_id': move_id,
     'product_id': producto_output_id,
     'qty_done': kg,
     'product_uom_id': 12,
     'location_id': ubicacion_virtual,
     'location_dest_id': orden['location_dest_id'][0],
     'state': 'draft',
     'reference': mo_name,
     'company_id': 1,
     'lot_id': lote_output_id,
     'result_package_id': package_output_id  # NOTA: result_package_id, no package_id
   }
   ```

---

**Respuesta del endpoint:**
```json
{
  "success": true,
  "mensaje": "3 pallets agregados a componentes",
  "pallets_agregados": 3,
  "kg_total": 2500.5,
  "errores": null
}
```

Si hubo errores parciales:
```json
{
  "success": true,
  "mensaje": "2 pallets agregados a subproductos",
  "pallets_agregados": 2,
  "kg_total": 1700.0,
  "errores": ["PACK0009903: Sin producto_id"]
}
```

Si todo falló:
```json
{
  "success": false,
  "error": "Orden 999 no encontrada",
  "pallets_agregados": 0,
  "kg_total": 0,
  "errores": ["..."]
}
```

---

## ESTADOS DE ODOO (MAPA)

```typescript
const ESTADOS_LABELS: Record<string, string> = {
  'draft':     '📝 Borrador',
  'confirmed': '✅ Confirmado',
  'progress':  '🔄 En Proceso',
  'done':      '✔️ Terminado',
  'cancel':    '❌ Cancelado',
  'assigned':  '📦 Reservado',
  'waiting':   '⏳ Esperando',
}
```

---

## TIPOS TypeScript NECESARIOS

```typescript
// Orden encontrada por buscar-orden
interface OrdenProceso {
  id: number
  nombre: string
  producto: string
  producto_id: number | null
  cantidad: number
  estado: string
  componentes_count: number
  subproductos_count: number
  modelo: 'mrp.production' | 'stock.picking'
}

// Pallet individual tras validación
interface PalletValidado {
  codigo: string
  valido: boolean
  kg: number
  producto_id: number | null
  producto_nombre: string
  lote_id: number | null
  lote_nombre: string
  ubicacion_id: number | null
  package_id: number | null
  error?: string
}

// Pallet listo para enviar al agregar
interface PalletParaAgregar {
  codigo: string
  kg: number
  lote_id: number | null
  lote_nombre: string
  producto_id: number | null
  ubicacion_id: number | null
  package_id: number | null
}

// Request para validar pallets
interface ValidarPalletsRequest {
  pallets: string[]
  tipo: 'componentes' | 'subproductos'
  orden_id: number
}

// Request para agregar pallets
interface AgregarPalletsRequest {
  orden_id: number
  tipo: 'componentes' | 'subproductos'
  pallets: PalletParaAgregar[]
  modelo: 'mrp.production' | 'stock.picking'
}

// Resultado de agregar
interface ResultadoAgregar {
  success: boolean
  mensaje?: string
  pallets_agregados: number
  kg_total: number
  errores: string[] | null
  error?: string // Solo cuando success=false
}
```

---

## AUTENTICACIÓN

- El backend utiliza **username + password (API Key)** de Odoo que se pasan como **query params** en cada request.
- En el frontend React actual se tienen inputs para `odooUser` y `odooKey`.
- El `apiClient` es una instancia de axios configurada con base URL del backend.

---

## NORMALIZACIÓN DE CÓDIGOS DE PALLET

```typescript
function normalizarCodigoPallet(code: string): string {
  let c = code.trim().toUpperCase()
  // PAC0009900 → PACK0009900
  if (c.startsWith('PAC') && !c.startsWith('PACK')) {
    c = 'PACK' + c.substring(3)
  }
  return c
}
```

---

## DEDUPLICACIÓN

- **En el frontend**: antes de enviar a validar, se eliminan códigos que ya estén en la lista de pallets validados.
- **En el backend**: antes de validar cada pallet, se verifica contra pallets ya existentes en la orden en Odoo.

---

## COMPORTAMIENTO DEL UI

### Resultado persistente
- Tras agregar pallets exitosamente, el resultado (success + pallets_agregados + kg_total) se guarda en el estado.
- Se muestra en un banner persistente en la parte superior del tab con un botón "Cerrar mensaje".
- Se usa un color verde para éxito y rojo para error.

### Limpieza automática
- Al buscar una nueva orden, se limpia la lista de pallets.
- Al agregar exitosamente, se limpia la lista de pallets y se refresca la info de la orden.

### Feedback visual
- Cada pallet validado muestra: icono de tipo (🔵 componentes / 🟢 subproductos), código, kg, lote, producto.
- Los errores se muestran inline por cada pallet.
- Spinners durante búsqueda, validación y envío.
- Métricas (KPI cards): total pallets y total kg.

---

## COMPONENTES UI SUGERIDOS (React + shadcn/ui)

```
- Card, CardHeader, CardContent, CardTitle
- Input (búsqueda de orden)
- Button (buscar, validar, agregar, limpiar, eliminar)
- Select (tipo de movimiento: componentes/subproductos)
- Textarea (códigos de pallets)
- Badge (estados, validación OK/error/ya en orden)
- Alert (resultado éxito/error)
- Skeleton / Spinner (loading states)
- DataTable con columnas: pallet, producto, lote, kg, estado (badge)
```

---

## ESTRUCTURA DE ARCHIVOS RECOMENDADA

```
src/
  features/
    automatizacion-of/
      AutomatizacionOfPage.tsx        # Componente principal
      components/
        OrdenSearch.tsx               # Paso 1 - Búsqueda de orden
        OrdenInfo.tsx                 # Display info de orden encontrada
        MovimientoSelector.tsx        # Paso 2 - Selector componentes/subproductos
        PalletScanner.tsx             # Paso 3 - Textarea + validar
        PalletsValidados.tsx          # Paso 4 - Lista de pallets + acciones
        ResultadoBanner.tsx           # Banner de resultado persistente
      hooks/
        useAutomatizacionOf.ts        # Hook con toda la lógica de estado
      types.ts                        # Interfaces TypeScript
  api/
    automatizacion-of.ts              # Hooks de TanStack Query
```

---

## HOOKS DE API (TanStack Query)

```typescript
// GET buscar orden (useQuery, enabled cuando hay input)
useBuscarOrdenProcesos(orden, odooUser, odooKey, enabled)

// POST validar pallets (useMutation)
useValidarPalletsProcesos()

// POST agregar pallets (useMutation)
useAgregarPalletsProcesos()
```

---

## EDGE CASES Y REGLAS DE NEGOCIO

1. **Pallets con 0 KG**: se rechazan en validación.
2. **Pallets sin stock (quant vacío)**: se rechazan.
3. **Pallets ya en la orden**: se rechazan con mensaje "Ya está ingresado en esta orden".
4. **Package no encontrado**: se rechaza en validación.
5. **Subproductos**: el código de producto se transforma (1xxxxx → 2xxxxx), el lote se sufija con `-C`, el package se sufija con `-C`.
6. **Reutilización de stock.move**: si ya existe un move para el mismo producto en la misma orden, se reutiliza (solo se crea un nuevo move.line).
7. **Ubicación virtual**: depende de si la orden tiene "RF" en el nombre (congelado=8485 vs procesos=15).
8. **UoM fija**: siempre ID=12 (kilogramos).
9. **company_id fija**: siempre 1.
10. **Sin reserva**: los move_lines se crean con `state='draft'`, sin reservar stock.

---

## CÓDIGO FUENTE ORIGINAL COMPLETO

Los archivos fuente originales están incluidos en esta carpeta:

### Streamlit (Frontend original):
- `streamlit_original/tab_automatizacion_of.py` — Tab completo (378 líneas)
- `streamlit_original/shared_produccion.py` — Constantes y utilidades compartidas
- `streamlit_original/2_Produccion.py` — Orquestador de tabs (cómo se integra)

### Backend (API):
- `backend_original/automatizaciones_router.py` — Router FastAPI completo (1151 líneas)
  - La sección relevante va de la línea 532 a la 1151
  - Incluye los 3 endpoints + modelos Pydantic

### React existente (referencia parcial):
- `react_existente/produccion_api.ts` — Hooks de TanStack Query (ya implementados)
- `react_existente/ProduccionPage.tsx` — Componente React existente (líneas 446-636 son AutomatizacionOfTab)

---

## RESUMEN DE MODELOS ODOO USADOS

| Modelo | Uso |
|--------|-----|
| `mrp.production` | Órdenes de fabricación. Campos: `name`, `product_id`, `product_qty`, `state`, `move_raw_ids`, `move_finished_ids`, `location_src_id`, `location_dest_id` |
| `stock.picking` | Transferencias internas. Campos: `name`, `state`, `location_id`, `location_dest_id`, `move_ids`, `picking_type_id` |
| `stock.move` | Movimientos de stock. Se crean con `picking_id`, `raw_material_production_id` o `production_id` según el caso |
| `stock.move.line` | Detalle de movimiento. Se crea con `move_id`, `product_id`, `qty_done`, `lot_id`, `package_id` o `result_package_id` |
| `stock.quant.package` | Pallets/embalajes. Se buscan por `name` |
| `stock.quant` | Stock actual por pallet/lote/ubicación |
| `stock.lot` | Lotes de producción |
| `product.product` | Productos. Campo `default_code` usado para transformación 1→2 en subproductos |

---

## DIFERENCIAS CLAVE ENTRE COMPONENTES Y SUBPRODUCTOS

| Aspecto | Componentes | Subproductos |
|---------|-------------|--------------|
| Vinculación en stock.move | `raw_material_production_id` | `production_id` |
| Dirección | Entrada (materia prima) | Salida (producto terminado) |
| Ubicación origen | `ubicacion_id` o `location_src_id` | `ubicacion_virtual` |
| Ubicación destino | `ubicacion_virtual` | `location_dest_id` |
| Producto | El mismo del pallet | Puede cambiar (1→2 congelado) |
| Lote | El mismo | Se crea uno nuevo con sufijo `-C` |
| Package | `package_id` en move_line | `result_package_id` en move_line |
| Package name | El mismo | Se crea uno nuevo con sufijo `-C` |

---

## NOTAS ADICIONALES

1. El backend NO es el que necesitas migrar — solo la UI. El backend (FastAPI) sigue siendo el mismo y los endpoints no cambian.
2. Los 3 endpoints ya están implementados y funcionando.
3. Ya existe una implementación parcial en React (`react_existente/ProduccionPage.tsx`) que puede servir como base, pero necesita ser extraída como componente independiente y mejorada.
4. Los hooks de API (`react_existente/produccion_api.ts`) ya están implementados con TanStack Query.
5. La autenticación Odoo (username + API key) se pasa como query params en cada request.
