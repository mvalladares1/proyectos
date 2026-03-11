# PLAN DE REGULARIZACIÓN: BODEGA DE INSUMOS
## Alcance Estricto - Solo RF/Insumos

**Fecha:** 2026-03-10  
**Versión:** 1.0  
**Alcance:** Exclusivo RF/Insumos, empaque, EPP, químicos operativos  
**Excluye:** Fruta, MP, producto en proceso, producto terminado

---

# ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Clasificación de Alcance](#2-clasificación-de-alcance)
3. [Diagnóstico de RF INSUMOS](#3-diagnóstico-de-rf-insumos)
4. [Productos Críticos con Stock Negativo](#4-productos-críticos-con-stock-negativo)
5. [Movimientos y Pickings Problemáticos](#5-movimientos-y-pickings-problemáticos)
6. [Usuarios y Tipo de Operación](#6-usuarios-y-tipo-de-operación)
7. [Recomendación sobre Tipo CONSUMO (ID 177)](#7-recomendación-sobre-tipo-consumo-id-177)
8. [Flujo Futuro para Bodega de Insumos](#8-flujo-futuro-para-bodega-de-insumos)
9. [Plan de Regularización Paso a Paso](#9-plan-de-regularización-paso-a-paso)
10. [Riesgos y Controles](#10-riesgos-y-controles)
11. [Cambios de Permisos y Configuración](#11-cambios-de-permisos-y-configuración)
12. [Scripts de Monitoreo](#12-scripts-de-monitoreo)

---

# 1. RESUMEN EJECUTIVO

## 1.1 Problema Identificado

La bodega de insumos (RF/Insumos) presenta desorden operativo causado principalmente por:

1. **Uso del tipo de operación CONSUMO (ID 177)** sin trazabilidad
2. **Usuario genérico "Bodega Insumos"** que impide identificar responsables
3. **Movimientos manuales sin documento origen** (418 detectados)
4. **46 productos de insumos con stock negativo**

## 1.2 Cifras Clave

| Métrica | Valor | Observación |
|---------|-------|-------------|
| Productos de insumos en alcance | **270** | Empaque, EPP, químicos, auxiliares |
| Productos FUERA de alcance | **31** | No tocar - fruta, MP, etc. |
| Productos con stock negativo | **46** | Prioridad de regularización |
| Movimientos tipo CONSUMO | **423** | Principal fuente del problema |
| Pickings CONSUMO pendientes | **6** | Deben cerrarse primero |
| Ajustes negativos | **423** (475,765 uds) | Mermas registradas |
| Usuario genérico responsable | "Bodega Insumos" | **82% de movimientos CONSUMO** |

## 1.3 Decisión Recomendada

| Acción | Prioridad | Plazo |
|--------|-----------|-------|
| Cerrar 6 pickings CONSUMO pendientes | 🔴 CRÍTICA | Día 1 |
| Desactivar tipo CONSUMO (ID 177) | 🔴 CRÍTICA | Día 2 |
| Desactivar usuario "Bodega Insumos" | 🔴 CRÍTICA | Día 2 |
| Conteo físico de insumos críticos | 🟠 ALTA | Semana 1 |
| Regularización por lotes | 🟠 ALTA | Semana 2 |
| Implementar nuevo flujo | 🟡 MEDIA | Semana 3+ |

---

# 2. CLASIFICACIÓN DE ALCANCE

## 2.1 Ubicaciones DENTRO de Alcance

| ID | Ubicación | Uso |
|----|-----------|-----|
| 5474 | RF/Insumos | Ubicación padre |
| 24 | RF/Insumos/Bodega Insumos | **Principal** - almacenamiento |
| 8293-8312 | RF/Insumos/Bodega Insumos/BINA* | Sub-ubicaciones de almacén |

**Total ubicaciones:** 169 (todas bajo RF/Insumos)

## 2.2 Productos DENTRO de Alcance (270)

| Categoría | Cantidad | Ejemplos |
|-----------|----------|----------|
| **EMPAQUE** | 86 | Bolsas, cajas, etiquetas, film, cintas |
| **CÓDIGO 500** | 55 | Productos con código iniciando en 500* |
| **UBICACIÓN_INSUMOS** | 82 | Otros en RF/Insumos sin clasificar específica |
| **EPP** | 22 | Guantes, cofias, overoles, botas |
| **MATERIALES_AUXILIARES** | 15 | Pallets, cartón, papel |
| **QUÍMICOS_OPERATIVOS** | 10 | Cloro, detergente, sanitizantes |

### Ejemplos de Productos en Alcance:
```
✅ [500081-24] ETIQUETA 50x100 BLANCA
✅ [500003-24] ETIQUETAS 10x15 BLANCA
✅ [500062-24] MASCARILLAS 3 PLIEGUES
✅ [500000-24] CAJA EXPORTACIÓN 47x24.5x24.2
✅ [500011-24] BOLSA AZUL 31X57X0.045
✅ GUANTES DE NITRILO
✅ PALLET DE MADERA 1X1.20 MT
✅ [500106] JABON ANTIBACTERIAL
```

## 2.3 Productos FUERA de Alcance (31) - NO TOCAR

| Producto | Motivo de Exclusión |
|----------|---------------------|
| [5000018] Bandeja IQF 60x40 | Bandeja productiva |
| [500079] BOLSA CREATIVE GOURMET BLUEBERRY | Empaque de producto terminado |
| [500080-24] CAJA CREATIVE GOURMET BLUEBERRY | Empaque de producto terminado |
| BOLSA DE BINS 240x220 | Empaque de fruta |
| DOY PACK IMPRESO TRIPLE BERRIES | Empaque de producto terminado |
| [500323] CAJA REUTILIZADA PARA CONGELADO | Producto proceso |
| DESPALILLADOR DE ARANDANOS | Maquinaria |

**REGLA:** Si el producto está vinculado a empaque de producto terminado, fruta o proceso productivo, queda FUERA del alcance de esta regularización.

---

# 3. DIAGNÓSTICO DE RF INSUMOS

## 3.1 Estado Actual del Inventario

| Métrica | Valor |
|---------|-------|
| Total quants en RF/Insumos | 708 |
| Productos únicos | 270 (en alcance) |
| Productos con stock positivo | 224 |
| Productos con stock negativo | **46** |
| Productos con stock cero | - |

## 3.2 Flujo de Movimientos

| Dirección | Cantidad | Observación |
|-----------|----------|-------------|
| Entradas a RF/Insumos | 4,609 | Recepciones + devoluciones |
| Salidas de RF/Insumos | 11,240 | Consumos + entregas |
| **Diferencia** | **-6,631** | Más salidas que entradas |

## 3.3 Tipos de Operación Usados en RF/Insumos

| Tipo de Operación | Movimientos | Uso |
|-------------------|-------------|-----|
| Rio Futuro: Manufactura Vaciado PSP | 1,070 | Consumo desde producción |
| Rio Futuro: Manufactura Congelado S/L | 302 | Consumo desde producción |
| Rio Futuro: Recepciones Insumos | 200 | **Correcto** - entrada de insumos |
| Rio Futuro: Manufactura Vaciado MP S/P | 203 | Consumo desde producción |
| Rio Futuro: Manufactura Congelado C/L T2 | 142 | Consumo desde producción |
| Rio Futuro: CONSUMO (ID 177) | ~500 | **⚠️ PROBLEMÁTICO** |

## 3.4 Problema Principal Identificado

```
┌──────────────────────────────────────────────────────────────┐
│  DIAGNÓSTICO: El tipo CONSUMO (ID 177) se usa para sacar    │
│  insumos de bodega SIN vincular a una OF ni documento.      │
│                                                              │
│  Usuario "Bodega Insumos" ejecuta 82% de estos movimientos  │
│  → No hay trazabilidad de quién realmente tomó el insumo    │
│  → No hay vínculo con producción                            │
│  → No hay documento que justifique el consumo               │
└──────────────────────────────────────────────────────────────┘
```

---

# 4. PRODUCTOS CRÍTICOS CON STOCK NEGATIVO

## 4.1 Top 20 Productos de Insumos con Stock Negativo

| # | Código | Producto | Stock | Categoría | Prioridad |
|---|--------|----------|-------|-----------|-----------|
| 1 | 500000-24 | CAJA EXPORTACIÓN 47x24.5x24.2 | **-41,754.50** | EMPAQUE | 🔴 |
| 2 | 500340 | BOLSA BD TRANSPARENTE GENÉRICA 25X30 | **-30,559.00** | EMPAQUE | 🔴 |
| 3 | 500058 | COFIAS (UN) | **-17,941.00** | EPP | 🔴 |
| 4 | 500287-24 | ETIQUETA AMARILLA 100X50 MM | **-14,432.72** | EMPAQUE | 🔴 |
| 5 | 500000 | CAJA EXPORTACIÓN 47x24.5x24.2 (viejo) | **-4,809.00** | EMPAQUE | 🟠 |
| 6 | 500304 | ESQUINEROS BLANCOS 2.25 MTS | **-4,000.00** | EMPAQUE | 🟠 |
| 7 | 500066 | FILM MANUAL | **-3,621.00** | EMPAQUE | 🟠 |
| 8 | 500029 | FILM STRETCH AUTOMÁTICO | **-881.73** | EMPAQUE | 🟠 |
| 9 | 500070 | BOLSA BASURA NEGRA 50X70 | **-780.00** | EMPAQUE | 🟡 |
| 10 | 500066-A | FILM MANUAL (dup) | **-324.00** | EMPAQUE | 🟡 |
| 11 | 500026 | GUANTES DE NITRILO CAJA | **-300.00** | EPP | 🟡 |
| 12 | 500212-24 | Foamchlor (ARCHIVAR) | **-240.00** | QUÍMICO | 🟡 |
| 13 | 500009-23 | Bandeja 1/8 50x30 | **-200.00** | EMPAQUE | 🟡 |
| 14 | 12 | BOLSA NEGRA 50X70 | **-200.00** | EMPAQUE | 🟡 |
| 15 | - | PALLET DE MADERA 1X1.20 MT(A PRODUCTOR) | **-143.00** | AUXILIAR | 🟡 |
| 16 | 500032-A | CINTA TERMOTRANSFERENCIA 110x450 | **-74.00** | EMPAQUE | 🟢 |
| 17 | 500061 | OVEROL DESECHABLE | **-50.00** | EPP | 🟢 |
| 18 | 500023 | TRAJE DE AGUA | **-45.00** | EPP | 🟢 |
| 19 | 500015 | ZAPATOS DE SEGURIDAD (PAR) | **-39.00** | EPP | 🟢 |
| 20 | 500025 | BOTAS DE AGUA BLANCAS | **-30.00** | EPP | 🟢 |

## 4.2 Análisis de Productos Más Críticos

### 500000-24 CAJA EXPORTACIÓN (-41,754.50)
- **Causa probable:** Consumos manuales excesivos sin recepción correspondiente
- **Verificar:** ¿Se recibieron cajas y no se registraron?
- **Acción:** Conteo físico urgente

### 500340 BOLSA BD TRANSPARENTE (-30,559.00)
- **Movido por CONSUMO:** 223,191 unidades (TOP 1 en tipo CONSUMO)
- **Causa:** Usuario "Bodega Insumos" ejecutó múltiples consumos
- **Acción:** Verificar existencia física y ajustar

### 500058 COFIAS (-17,941.00)
- **Movido por CONSUMO:** 92,773 unidades
- **EPP de alto rotación**
- **Acción:** Verificar stock real, posible faltante de recepciones

---

# 5. MOVIMIENTOS Y PICKINGS PROBLEMÁTICOS

## 5.1 Pickings CONSUMO Pendientes (Cerrar Antes de Bloquear)

| Picking | Estado | Acción Requerida |
|---------|--------|------------------|
| CONS1198 | draft | **Cancelar** - borrador antiguo |
| CONS1221 | draft | **Cancelar** - borrador antiguo |
| CONS1338 | draft | **Cancelar** - borrador antiguo |
| CONS1299 | assigned | **Evaluar** - tiene reservas |
| CONS1361 | assigned | **Evaluar** - tiene reservas |
| CONS1378 | assigned | **Evaluar** - tiene reservas |

### Procedimiento para Pickings Pendientes:

```
1. Para pickings en DRAFT:
   → Abrir picking
   → Verificar si tiene sentido completar
   → Si no: Cancelar (Botón "Cancelar")
   
2. Para pickings en ASSIGNED:
   → Abrir picking
   → Verificar productos y cantidades reservadas
   → Si válido: Completar y documentar
   → Si inválido: Liberar reservas y cancelar
```

## 5.2 Movimientos Sin Documento Origen

| Métrica | Valor |
|---------|-------|
| Movimientos analizados | 500 |
| Sin picking o sin origen | **418 (83.6%)** |

**Consecuencia:** 83.6% de los movimientos de insumos problemáticos no tienen trazabilidad documental.

## 5.3 Movimientos por Tipo de Operación

| Tipo | Movimientos | Problemático |
|------|-------------|--------------|
| Manufacturing | 151 | ✅ OK - vinculado a OF |
| Consumo de Inventario | 150 | ⚠️ Evaluar |
| Manufactura Vaciado PSP | 65 | ✅ OK - producción |
| Recepciones Insumos | 59 | ✅ OK |
| **CONSUMO (ID 177)** | 13 (muestra) | ❌ **PROBLEMÁTICO** |

---

# 6. USUARIOS Y TIPO DE OPERACIÓN

## 6.1 Usuarios que Operan en RF/Insumos

| Usuario | Movimientos | Rol Probable |
|---------|-------------|--------------|
| MARCELO JARAMILLO CADEGAN | 262 | Producción |
| JUAN ROLANDO BRANDT MARTINEZ | 63 | Producción |
| FRANCISCA BARRIGA | 33 | Producción |
| **Bodega Insumos** | 29 | **⚠️ USUARIO GENÉRICO** |
| JORDANA ALVAREZ | 31 | Producción |
| NICOLE MONTES | 21 | Producción |
| BELEN MONTES | 19 | Producción |

## 6.2 Usuarios que Usan Tipo CONSUMO para Insumos

| Usuario | Movimientos CONSUMO | % del Total |
|---------|---------------------|-------------|
| **Bodega Insumos** | **346** | **82%** |
| ALVARO ALONSO SANCHEZ GALAZ | 59 | 14% |
| DIEGO EUDALDO SAAVEDRA ALBARRACÍN | 12 | 3% |
| MARCELO JARAMILLO CADEGAN | 4 | 1% |
| FELIPE TOMÁS HORST SCHENCKE | 1 | <1% |
| JUAN ROLANDO BRANDT MARTINEZ | 1 | <1% |

## 6.3 Usuarios que Hacen Ajustes de Inventario

| Usuario | Ajustes + | Uds + | Ajustes - | Uds - |
|---------|-----------|-------|-----------|-------|
| **Bodega Insumos** | 9 | 128,983 | **337** | **401,648** |
| ALVARO ALONSO SANCHEZ GALAZ | 0 | 0 | 59 | 9,516 |
| ASISTENCIA NUBISTALIA | 45 | 113,454 | 0 | 0 |
| DIEGO EUDALDO SAAVEDRA | 10 | 19 | 21 | 61,787 |
| LEONARDO SELÍN ALVAREZ | 12 | 3,729 | 0 | 0 |

**HALLAZGO CRÍTICO:** El usuario "Bodega Insumos" realizó **337 ajustes negativos** totalizando **-401,648 unidades**. Esto representa la mayor fuente de descuento de inventario de insumos.

---

# 7. RECOMENDACIÓN SOBRE TIPO CONSUMO (ID 177)

## 7.1 Análisis del Tipo CONSUMO

| Atributo | Valor | Observación |
|----------|-------|-------------|
| ID | 177 | |
| Nombre | CONSUMO | |
| Código | internal | Transferencia interna |
| Origen | RF/Insumos (5474) | Bodega de insumos |
| Destino | Virtual Locations/Consumo-CentroCosto (5478) | **Ubicación virtual** |
| Pickings completados | 365 | |
| Movimientos insumos | 423 | |
| Usuario principal | Bodega Insumos (82%) | |

## 7.2 Problema con el Tipo CONSUMO

```
┌─────────────────────────────────────────────────────────────────────────┐
│  El tipo CONSUMO envía insumos a una UBICACIÓN VIRTUAL llamada         │
│  "Consumo-CentroCosto", que NO es una ubicación física.                │
│                                                                         │
│  Esto significa:                                                        │
│  ❌ No hay destino real verificable                                     │
│  ❌ No hay vínculo con orden de fabricación                              │
│  ❌ No hay trazabilidad de quién consumió realmente                      │
│  ❌ No hay forma de devolver sobrantes                                   │
│  ❌ Usuario genérico "Bodega Insumos" ejecuta sin responsable real       │
│                                                                         │
│  CONCLUSIÓN: Este tipo de operación rompe completamente la              │
│  trazabilidad y control de la bodega de insumos.                        │
└─────────────────────────────────────────────────────────────────────────┘
```

## 7.3 Decisión Recomendada

### ✅ **BLOQUEAR TIPO CONSUMO (ID 177)**

**Justificación:**
1. 423 movimientos de insumos sin trazabilidad
2. 82% ejecutados por usuario genérico
3. Destino es ubicación virtual sin control
4. No hay vínculo con producción
5. Imposible auditar o corregir retroactivamente

### Alternativas a Implementar:

| Escenario | Solución |
|-----------|----------|
| Producción necesita insumos | Solicitar por OF (consumo automático de BOM) |
| Transferencia a línea de producción | Crear tipo "Transferencia Insumos → Producción" |
| Merma de insumos | Usar Ajuste de Inventario con aprobación |
| Devolución de sobrantes | Crear tipo "Devolución Producción → Insumos" |

## 7.4 Pasos para Bloquear

```python
# Paso 1: Verificar pickings pendientes
picking_type = self.env['stock.picking.type'].browse(177)
pending = self.env['stock.picking'].search([
    ('picking_type_id', '=', 177),
    ('state', 'not in', ['done', 'cancel'])
])
# Resultado: 6 pickings pendientes

# Paso 2: Cerrar o cancelar pendientes (ver sección 5.1)

# Paso 3: Desactivar tipo de operación
picking_type.write({'active': False})

# Paso 4: Alternativa - Restringir usuarios
picking_type.write({
    'group_id': [(6, 0, [])]  # Ningún grupo tiene acceso
})
```

---

# 8. FLUJO FUTURO PARA BODEGA DE INSUMOS

## 8.1 Principios del Nuevo Flujo

1. **Toda entrada debe tener documento:** Orden de compra + recepción
2. **Toda salida debe tener destino real:** OF, transferencia documentada o ajuste aprobado
3. **Usuarios nominados:** Prohibir usuarios genéricos
4. **Segregación de funciones:** Quien recibe ≠ quien entrega ≠ quien ajusta

## 8.2 Flujo de Recepción de Insumos

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   COMPRA (PO)   │────▶│   RECEPCIÓN     │────▶│  ALMACENAMIENTO │
│   (Compras)     │     │   INSUMOS       │     │  RF/Insumos/    │
│                 │     │   (Bodega)      │     │  Bodega Insumos │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        Tipo: "Recepciones Insumos"
                        Origen: Partners/Vendors
                        Destino: RF/Insumos/Bodega Insumos
```

## 8.3 Flujo de Entrega a Producción

### Opción A: Consumo vía Orden de Fabricación (RECOMENDADO)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PRODUCCIÓN     │────▶│  ORDEN DE       │────▶│  CONSUMO AUTO   │
│  (Solicita)     │     │  FABRICACIÓN    │     │  DE BOM         │
│                 │     │  (MO)           │     │  (Sistema)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        Los insumos se consumen automáticamente
                        cuando se confirma/cierra la OF
```

**Ventajas:**
- Trazabilidad completa
- Vinculado a producción
- Sin intervención manual

### Opción B: Transferencia a Línea de Producción (Para casos especiales)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PRODUCCIÓN     │────▶│  SOLICITUD      │────▶│  TRANSFERENCIA  │
│  (Solicita      │     │  INTERNA        │     │  INSUMOS →      │
│   insumos)      │     │  (Supervisor)   │     │  PRODUCCIÓN     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        Tipo: "Transferencia Insumos" (CREAR)
                        Origen: RF/Insumos/Bodega Insumos
                        Destino: RF/Stock/Línea Producción (CREAR)
```

**Usar solo para:**
- Insumos no incluidos en BOM
- Entregas a áreas de servicio (limpieza, mantenimiento)
- EPP

## 8.4 Flujo de Devolución de Sobrantes

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  PRODUCCIÓN     │────▶│  PICKING        │────▶│  RF/Insumos/    │
│  (Devuelve      │     │  DEVOLUCIÓN     │     │  Bodega Insumos │
│   sobrante)     │     │                 │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        Tipo: "Devolución a Insumos" (CREAR)
                        Origen: RF/Stock/Línea Producción
                        Destino: RF/Insumos/Bodega Insumos
```

## 8.5 Flujo de Mermas y Ajustes

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  DETECCIÓN      │────▶│  SOLICITUD      │────▶│  AJUSTE DE      │
│  MERMA          │     │  CON MOTIVO     │     │  INVENTARIO     │
│  (Bodega)       │     │  (Supervisor)   │     │  (Aprobado)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        Ubicación destino: Inventory Loss
                        Requiere: Motivo + Aprobación
```

## 8.6 Tabla de Roles y Permisos

| Rol | Recibir | Almacenar | Transferir | Ajustar | Aprobar Ajuste |
|-----|---------|-----------|------------|---------|----------------|
| Bodeguero Insumos | ✅ | ✅ | ✅ | ❌ | ❌ |
| Supervisor Bodega | ✅ | ✅ | ✅ | ✅ (< umbral) | ✅ (< umbral) |
| Jefe Bodega | ✅ | ✅ | ✅ | ✅ | ✅ |
| Operador Producción | ❌ | ❌ | ❌* | ❌ | ❌ |
| Supervisor Producción | ❌ | ❌ | ✅* | ❌ | ❌ |

*Solo solicitar mediante documento

---

# 9. PLAN DE REGULARIZACIÓN PASO A PASO

## SEMANA 1: CONTENCIÓN

### Día 1-2: Cierre de Pendientes

**Objetivo:** Eliminar pickings CONSUMO pendientes

| Paso | Acción | Responsable |
|------|--------|-------------|
| 1 | Listar los 6 pickings CONSUMO pendientes | TI |
| 2 | Evaluar CONS1299, CONS1361, CONS1378 (assigned) | Bodega |
| 3 | Completar si son válidos, cancelar si no | Bodega |
| 4 | Cancelar CONS1198, CONS1221, CONS1338 (draft) | Bodega |
| 5 | Confirmar 0 pickings pendientes de tipo CONSUMO | TI |

### Día 3: Bloqueo de Tipo CONSUMO

**Acción en Odoo:**
```
Inventario > Configuración > Tipos de Operación > CONSUMO (ID 177)
→ Marcar: Activo = False

O alternativamente:
→ Restringir grupos de usuario a ninguno
```

### Día 4: Desactivación de Usuario Genérico

**Acción en Odoo:**
```
Ajustes > Usuarios y Compañías > Usuarios > "Bodega Insumos"
→ Marcar: Activo = False

Crear usuarios nominados:
→ [Nombre_Apellido]_Bodega
→ Asignar permisos de Bodega / Usuario
```

### Día 5: Comunicación

- Email a usuarios afectados
- Capacitación sobre nuevo flujo
- Documento de referencia rápida

## SEMANA 2: CONTEO FÍSICO

### Preparación

**Plantilla de Conteo para Insumos:**

| Código | Producto | Ubicación | Stock Sistema | Stock Físico | Diferencia |
|--------|----------|-----------|---------------|--------------|------------|
| [auto] | [auto] | RF/Insumos/Bodega Insumos | [auto] | [manual] | [calc] |

### Priorización de Conteo

**Grupo 1 - CRÍTICO (Día 1-2):**
| Código | Producto | Stock Sistema |
|--------|----------|---------------|
| 500000-24 | CAJA EXPORTACIÓN | -41,754.50 |
| 500340 | BOLSA BD TRANSPARENTE | -30,559.00 |
| 500058 | COFIAS | -17,941.00 |
| 500287-24 | ETIQUETA AMARILLA | -14,432.72 |

**Grupo 2 - ALTO (Día 3-4):**
| Código | Producto | Stock Sistema |
|--------|----------|---------------|
| 500000 | CAJA EXPORTACIÓN (viejo) | -4,809.00 |
| 500304 | ESQUINEROS BLANCOS 2.25 MTS | -4,000.00 |
| 500066 | FILM MANUAL | -3,621.00 |
| 500029 | FILM STRETCH AUTOMÁTICO | -881.73 |

**Grupo 3 - MEDIO (Día 5):**
- Resto de productos con stock negativo (30+)

### Metodología de Conteo

1. **Equipo:** 2 personas (contador + verificador)
2. **Herramienta:** Planilla impresa o tablet
3. **Regla:** Conteo ciego (sin ver stock sistema primero)
4. **Reconteo:** Obligatorio si diferencia > 5%
5. **Fotografía:** Para diferencias > 10%

## SEMANA 3: REGULARIZACIÓN

### Proceso de Ajuste

**Crear Ajuste de Inventario:**
```
Inventario > Operaciones > Ajustes de Inventario > Crear
- Nombre: REGULARIZACIÓN INSUMOS 2026-03
- Ubicación: RF/Insumos/Bodega Insumos
- Incluir productos agotados: ✅
- Fecha contable: [Fecha de corte]
```

### Ejecución por Lotes

| Lote | Productos | Criterio | Día |
|------|-----------|----------|-----|
| 1 | 500000-24, 500340, 500058, 500287-24 | Stock < -10,000 | 1 |
| 2 | 500000, 500304, 500066, 500029 | Stock < -1,000 | 2 |
| 3 | Resto de negativos | Stock > -1,000 | 3-4 |

### Validación Post-Ajuste

- [ ] Verificar que quants negativos = 0 en RF/Insumos
- [ ] Validar asiento contable generado
- [ ] Conciliar con libro mayor
- [ ] Aprobar por Contabilidad

## SEMANA 4+: MONITOREO

### Controles Diarios (Primera Semana Post-Regularización)

| Control | Frecuencia | Responsable |
|---------|------------|-------------|
| Verificar nuevos negativos | Diario | TI |
| Revisar uso de tipos de operación | Diario | TI |
| Validar recepciones vs. PO | Diario | Bodega |

### Controles Semanales (Siguientes 4 Semanas)

| Control | Frecuencia | Responsable |
|---------|------------|-------------|
| Reporte de movimientos RF/Insumos | Semanal | TI |
| Auditoría de usuarios | Semanal | TI |
| Conciliación con Contabilidad | Semanal | Contabilidad |

---

# 10. RIESGOS Y CONTROLES

## 10.1 Riesgos de la Regularización

| ID | Riesgo | Probabilidad | Impacto | Mitigación |
|----|--------|--------------|---------|------------|
| R1 | Resistencia de usuarios al nuevo flujo | ALTA | MEDIO | Capacitación, comunicación |
| R2 | Productos físicamente inexistentes | MEDIA | ALTO | Conteo físico antes de ajuste |
| R3 | Error en carga de ajustes | MEDIA | ALTO | Validación previa, lotes pequeños |
| R4 | Descuadre contable | BAJA | ALTO | Aprobación Contabilidad |
| R5 | Uso de flujo antiguo post-bloqueo | MEDIA | MEDIO | Monitoreo, alertas |

## 10.2 Riesgos de NO Actuar

| ID | Riesgo | Probabilidad | Impacto | Consecuencia |
|----|--------|--------------|---------|--------------|
| RN1 | Crecimiento de negativos | ALTA | ALTO | Más difícil regularizar después |
| RN2 | Pérdida de control de inventario | ALTA | ALTO | Decisiones basadas en datos erróneos |
| RN3 | Imposibilidad de auditar | ALTA | MEDIO | Riesgo de auditoría |
| RN4 | Conflictos con producción | MEDIA | MEDIO | Faltantes no detectados |

## 10.3 Controles Propuestos

| Control | Implementación | Responsable |
|---------|----------------|-------------|
| Alerta de stock negativo | Script automático diario | TI |
| Bloqueo de movimiento manual | Desactivar tipo CONSUMO | TI |
| Validación de documento origen | Obligatorio en transferencias | Sistema |
| Auditoría de usuarios | Reporte semanal | TI |
| Aprobación de ajustes | Workflow de aprobación | Contabilidad |

---

# 11. CAMBIOS DE PERMISOS Y CONFIGURACIÓN

## 11.1 Tipos de Operación

### Desactivar:

| ID | Nombre | Acción |
|----|--------|--------|
| 177 | CONSUMO | **DESACTIVAR** |

### Crear (Opcionales):

| Nombre | Código | Origen | Destino | Uso |
|--------|--------|--------|---------|-----|
| Transferencia Insumos a Producción | INT_INS_PROD | RF/Insumos/Bodega Insumos | RF/Stock/Línea Producción | Entrega documentada |
| Devolución Producción a Insumos | INT_PROD_INS | RF/Stock/Línea Producción | RF/Insumos/Bodega Insumos | Retorno sobrantes |

## 11.2 Usuarios

### Desactivar:

| Usuario | Motivo |
|---------|--------|
| Bodega Insumos | Usuario genérico sin trazabilidad |

### Crear:

| Usuario | Formato | Grupo |
|---------|---------|-------|
| [Por cada persona real] | Nombre_Apellido_Bodega | Bodega / Usuario |

### Modificar Permisos:

| Grupo | Permiso Actual | Permiso Nuevo |
|-------|----------------|---------------|
| Bodega / Usuario | Ajuste inventario | **Sin ajuste** |
| Bodega / Responsable | Ajuste libre | Ajuste < umbral |
| Bodega / Manager | Todo | Mantener |

## 11.3 Ubicaciones

### Revisar:

| Ubicación | Acción |
|-----------|--------|
| Virtual Locations/Consumo-CentroCosto (5478) | Evaluar desactivar o restringir |

### Crear (Opcional):

| Ubicación | Padre | Uso |
|-----------|-------|-----|
| RF/Stock/Línea Producción | RF/Stock | Destino temporal para entrega de insumos |

## 11.4 Configuración MRP

```
Fabricación > Configuración > Ajustes:
✅ Consumo automático de componentes
✅ Reserva automática en confirmación

En cada BOM:
- Agregar insumos como componentes si aplica
- O usar tipo "Consumible" para EPP y materiales auxiliares
```

---

# 12. SCRIPTS DE MONITOREO

## 12.1 Script: Monitoreo Diario de RF INSUMOS

```python
#!/usr/bin/env python3
"""
MONITOREO DIARIO: RF INSUMOS
Detecta nuevos negativos y uso de tipos bloqueados
"""

import xmlrpc.client
from datetime import datetime

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"  # Usuario de monitoreo
PASSWORD = "xxxxx"

# IDs de ubicaciones RF/Insumos (principales)
RF_INSUMOS_IDS = [5474, 24]

# ID del tipo CONSUMO (bloqueado)
CONSUMO_TYPE_ID = 177

def check_rf_insumos():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # 1. Verificar quants negativos en RF/Insumos
    locations = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.location', 'search',
        [[('complete_name', 'ilike', 'RF/Insumos')]]
    )
    
    negative_quants = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_read',
        [[('location_id', 'in', locations), ('quantity', '<', 0)]],
        {'fields': ['product_id', 'location_id', 'quantity']}
    )
    
    print(f"[{datetime.now()}] Quants negativos en RF/Insumos: {len(negative_quants)}")
    
    if negative_quants:
        print("⚠️ ALERTA: Productos con stock negativo en RF/Insumos:")
        for q in negative_quants[:10]:
            print(f"  - {q['product_id'][1]}: {q['quantity']}")
    
    # 2. Verificar uso del tipo CONSUMO
    today = datetime.now().strftime('%Y-%m-%d')
    new_consumo = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.picking', 'search_count',
        [[
            ('picking_type_id', '=', CONSUMO_TYPE_ID),
            ('create_date', '>=', today)
        ]]
    )
    
    if new_consumo > 0:
        print(f"🔴 ALERTA: {new_consumo} pickings de tipo CONSUMO creados hoy!")
    else:
        print("✅ Sin uso de tipo CONSUMO hoy")
    
    return {
        'negative_count': len(negative_quants),
        'consumo_usage': new_consumo
    }

if __name__ == "__main__":
    check_rf_insumos()
```

## 12.2 Script: Reporte Semanal de RF INSUMOS

```python
#!/usr/bin/env python3
"""
REPORTE SEMANAL: RF INSUMOS
Resumen de movimientos, usuarios y estado del inventario
"""

import xmlrpc.client
from datetime import datetime, timedelta
import json

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"
PASSWORD = "xxxxx"

def weekly_report_rf_insumos():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    # Ubicaciones RF/Insumos
    locations = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.location', 'search',
        [[('complete_name', 'ilike', 'RF/Insumos')]]
    )
    
    # 1. Estado actual del inventario
    quants = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_read',
        [[('location_id', 'in', locations)]],
        {'fields': ['product_id', 'quantity']}
    )
    
    total_products = len(set([q['product_id'][0] for q in quants]))
    negative_count = len([q for q in quants if q['quantity'] < 0])
    total_negative_qty = sum([q['quantity'] for q in quants if q['quantity'] < 0])
    
    # 2. Movimientos de la semana
    moves = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.move', 'search_count',
        [[
            ('date', '>=', week_ago),
            ('state', '=', 'done'),
            '|',
            ('location_id', 'in', locations),
            ('location_dest_id', 'in', locations)
        ]]
    )
    
    # 3. Recepciones
    recepciones = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.picking', 'search_count',
        [[
            ('date_done', '>=', week_ago),
            ('picking_type_id.name', 'ilike', 'Recepciones Insumos'),
            ('state', '=', 'done')
        ]]
    )
    
    report = {
        'fecha': datetime.now().isoformat(),
        'periodo': f"{week_ago} a hoy",
        'productos_en_rf_insumos': total_products,
        'productos_negativos': negative_count,
        'stock_negativo_total': total_negative_qty,
        'movimientos_semana': moves,
        'recepciones_semana': recepciones
    }
    
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # Guardar reporte
    filename = f"reporte_rf_insumos_{datetime.now().strftime('%Y%m%d')}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report

if __name__ == "__main__":
    weekly_report_rf_insumos()
```

## 12.3 Script: Verificación de Integridad RF INSUMOS

```python
#!/usr/bin/env python3
"""
VERIFICACIÓN DE INTEGRIDAD: RF INSUMOS
Compara stock calculado vs quants
"""

import xmlrpc.client
from collections import defaultdict

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"
PASSWORD = "xxxxx"

# IDs principales de RF/Insumos
RF_INSUMOS_LOCATIONS = [24]  # RF/Insumos/Bodega Insumos

def verify_integrity():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Stock según quants
    quants = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_read',
        [[('location_id', 'in', RF_INSUMOS_LOCATIONS)]],
        {'fields': ['product_id', 'quantity']}
    )
    
    quant_stock = defaultdict(float)
    for q in quants:
        quant_stock[q['product_id'][0]] += q['quantity']
    
    # Stock según movimientos (entradas - salidas)
    moves_in = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.move', 'search_read',
        [[('location_dest_id', 'in', RF_INSUMOS_LOCATIONS), ('state', '=', 'done')]],
        {'fields': ['product_id', 'quantity_done']}
    )
    
    moves_out = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.move', 'search_read',
        [[('location_id', 'in', RF_INSUMOS_LOCATIONS), ('state', '=', 'done')]],
        {'fields': ['product_id', 'quantity_done']}
    )
    
    move_stock = defaultdict(float)
    for m in moves_in:
        move_stock[m['product_id'][0]] += m['quantity_done']
    for m in moves_out:
        move_stock[m['product_id'][0]] -= m['quantity_done']
    
    # Comparar
    all_products = set(quant_stock.keys()) | set(move_stock.keys())
    discrepancies = []
    
    for pid in all_products:
        qs = quant_stock.get(pid, 0)
        ms = move_stock.get(pid, 0)
        diff = abs(qs - ms)
        
        if diff > 0.01:
            discrepancies.append({
                'product_id': pid,
                'quant_stock': qs,
                'move_stock': ms,
                'difference': diff
            })
    
    if discrepancies:
        print(f"⚠️ {len(discrepancies)} discrepancias detectadas en RF/Insumos")
        for d in sorted(discrepancies, key=lambda x: -x['difference'])[:10]:
            print(f"  Producto {d['product_id']}: Quant={d['quant_stock']:.2f}, Moves={d['move_stock']:.2f}")
    else:
        print("✅ Sin discrepancias de integridad en RF/Insumos")
    
    return discrepancies

if __name__ == "__main__":
    verify_integrity()
```

## 12.4 Configuración de Ejecución Automática (Windows Task Scheduler)

```xml
<!-- Tarea programada: Monitoreo Diario RF INSUMOS -->
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-03-10T06:00:00</StartBoundary>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>python</Command>
      <Arguments>C:\scripts\monitor_rf_insumos_daily.py</Arguments>
    </Exec>
  </Actions>
</Task>
```

---

# ANEXOS

## Anexo A: Checklist de Implementación

### Semana 1: Contención
- [ ] Cerrar pickings CONSUMO pendientes (6)
- [ ] Desactivar tipo CONSUMO (ID 177)
- [ ] Desactivar usuario "Bodega Insumos"
- [ ] Crear usuarios nominados
- [ ] Comunicar a equipo

### Semana 2: Conteo Físico
- [ ] Preparar plantillas de conteo
- [ ] Contar productos críticos (4)
- [ ] Contar productos alto (4)
- [ ] Contar resto de negativos (38+)
- [ ] Consolidar diferencias

### Semana 3: Regularización
- [ ] Crear ajuste de inventario
- [ ] Cargar Lote 1 (críticos)
- [ ] Cargar Lote 2 (altos)
- [ ] Cargar Lote 3 (resto)
- [ ] Validar contabilidad

### Semana 4+: Monitoreo
- [ ] Instalar scripts de monitoreo
- [ ] Configurar alertas
- [ ] Ejecutar primer reporte semanal
- [ ] Capacitar usuarios en nuevo flujo

## Anexo B: Observaciones Fuera de Alcance

Los siguientes temas fueron detectados pero quedan **FUERA DEL ALCANCE** de este plan:

| Tema | Observación | Acción Futura |
|------|-------------|---------------|
| Stock negativo en MATERIAS_PRIMAS | 497 quants negativos | Fase 2 de regularización |
| Stock negativo en PRODUCTO_PROCESO | 806 quants negativos | Fase 2 de regularización |
| Stock negativo en Partners/Vendors | 500+ quants negativos | Fase 2 de regularización |
| Valorización de inventario | Capas negativas detectadas | Análisis contable posterior |
| Bandejas productivas | En ubicaciones de insumos | Reclasificar ubicación |

---

**FIN DEL DOCUMENTO**

*Este plan es específico para la bodega de insumos (RF/Insumos) y no debe aplicarse a fruta, materias primas ni productos elaborados.*
