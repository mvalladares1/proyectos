# PLAN EJECUTABLE DE REGULARIZACIÓN RF INSUMOS
## ODOO 16 - RIO FUTURO PROCESOS SPA

**Fecha:** 2026-03-10  
**Versión:** 1.0  
**Tipo:** Plan Ejecutable con Validaciones Técnicas  
**Estado:** LISTO PARA REVISIÓN Y APROBACIÓN

---

# ÍNDICE

1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Validaciones Técnicas Realizadas](#2-validaciones-técnicas-realizadas)
3. [Hallazgos Confirmados vs Probables](#3-hallazgos-confirmados-vs-probables)
4. [Flujo Oficial Recomendado](#4-flujo-oficial-recomendado)
5. [Plan Exacto de Regularización RF INSUMOS](#5-plan-exacto-de-regularización-rf-insumos)
6. [Criterios para Restricción de Consumo Manual](#6-criterios-para-restricción-de-consumo-manual)
7. [Impacto Contable por Prioridad](#7-impacto-contable-por-prioridad)
8. [Matriz de Riesgos](#8-matriz-de-riesgos)
9. [Propuesta Técnica de Cambios](#9-propuesta-técnica-de-cambios)
10. [Scripts de Monitoreo Post-Corrección](#10-scripts-de-monitoreo-post-corrección)

---

# 1. RESUMEN EJECUTIVO

## 1.1 Contexto
Se realizó una auditoría técnica profunda del sistema de inventarios de Odoo 16, específicamente enfocada en RF INSUMOS, detectándose problemas graves de stock negativo, consumos manuales descontrolados y discrepancias entre movimientos físicos y contables.

## 1.2 Magnitud del Problema

| Métrica | Valor | Criticidad |
|---------|-------|------------|
| **Impacto monetario total estimado** | **$5,983,149,937 CLP** | 🔴 CRÍTICO |
| Productos con stock negativo | 937 | 🔴 CRÍTICO |
| Quants negativos total | 2,000+ | 🔴 CRÍTICO |
| Quants negativos en RF/Insumos | 249 | 🟠 ALTO |
| Stock negativo total RF/Insumos | -1,836,045 uds | 🟠 ALTO |
| Pickings pendientes tipo CONSUMO | 9 | 🟡 MEDIO |
| Capas de valoración negativas | 100+ | 🔴 CRÍTICO |

## 1.3 Validaciones Completadas ✅

| Fase | Estado | Hallazgos Confirmados |
|------|--------|----------------------|
| A1: Operación CONSUMO | ✅ Completada | 5 |
| A2: Flujo MRP | ✅ Completada | 1 |
| A3: Clasificación Familias | ✅ Completada | 6 |
| A4: Negativos Vendor | ✅ Completada | 3 |
| D: Impacto Contable | ✅ Completada | 21 |

## 1.4 Decisión Recomendada

**SOLUCIÓN HÍBRIDA EN 4 FASES:**
1. **Semana 1:** Contención - Bloquear consumo manual (ID 177)
2. **Semana 2:** Conteo físico RF INSUMOS
3. **Semana 3-4:** Regularización por lotes
4. **Semana 5+:** Rediseño de flujo y monitoreo

---

# 2. VALIDACIONES TÉCNICAS REALIZADAS

## 2.1 FASE A1: Tipo de Operación CONSUMO

### 2.1.1 Tipos Identificados

Se encontraron **3 tipos de operación** con nombre "Consumo":

| ID | Nombre | Código | Origen | Destino | Pickings Done | Estado |
|----|--------|--------|--------|---------|---------------|--------|
| 165 | Consumo de Inventario | mrp_operation | RF/Insumos/Bodega Insumos | RF/Insumos/Bodega Insumos | 0 | Sin uso |
| 150 | Consumo de Inventario | mrp_operation | RF | RF/Stock/Consumo Interno | 2 | Bajo uso |
| **177** | **CONSUMO** | **internal** | **RF/Insumos** | **Virtual Locations/Consumo-CentroCosto** | **365** | **⚠️ CRÍTICO** |

### 2.1.2 Tipo CONSUMO (ID 177) - Análisis Detallado

**HALLAZGO CONFIRMADO:** Este es el tipo de operación problemático.

| Atributo | Valor |
|----------|-------|
| ID | 177 |
| Nombre | CONSUMO |
| Código | internal |
| Secuencia | RFP/CONS |
| Activo | ✅ Sí |
| Ubicación Origen | RF/Insumos (ID: 5474) |
| Ubicación Destino | Virtual Locations/Consumo-CentroCosto (ID: 5478) |
| Total Pickings | 379 |
| Pickings Completados | 365 |
| Pickings Pendientes | 9 (3 draft, 3 draft, 3 assigned) |

**HALLAZGO CONFIRMADO:** No hay correlación con órdenes de fabricación.
- De la muestra de 100 pickings, **0** tienen origen tipo MO
- Confirma uso como **consumo manual independiente**

### 2.1.3 Usuarios que Usan Tipo CONSUMO (ID 177)

| Usuario | Pickings | % del Total |
|---------|----------|-------------|
| **Bodega Insumos** | 99 | 99% |
| DIEGO EUDALDO SAAVEDRA ALBARRACÍN | 1 | 1% |

**⚠️ ALERTA:** El usuario "Bodega Insumos" es un **usuario genérico compartido**. Esto impide trazabilidad individual.

### 2.1.4 Top 10 Productos Consumidos por Tipo CONSUMO (ID 177)

| Código | Producto | Cantidad Consumida |
|--------|----------|-------------------|
| 500341 | BOLSA DP BLUEBERRIES ALDI 24 OZ 680 GR | 371,066 |
| 500340 | BOLSA BD TRANSPARENTE GENÉRICA 25X30 60 M | 223,191 |
| 500058 | COFIAS (UN) | 91,973 |
| 500338 | CAJA TAPA ALDI 12X32 oz | 85,317 |
| 500064 | ETIQUETA 3x5 BLANCA | 71,220 |
| 500345 | BOLSA 230X320X100 ZIP ARANDANOS ATO | 60,200 |
| 500342 | ETIQUETA 100X100 BLUEBERRY | 48,000 |
| 500058-24 | Bandeja Negra 50x30 (copia) | 27,702 |
| 500069 | BOLSA BASURA NEGRA 110X120 | 21,832 |
| 500303 | ESQUINEROS BLANCOS 1.8 MTS. (UN) | 20,030 |

### 2.1.5 Pickings Pendientes (Requieren Acción)

| Picking | Estado | Acción Requerida |
|---------|--------|------------------|
| WH/Cons/00001 | draft | Cancelar o Completar antes de bloqueo |
| WH/Cons/00003 | draft | Cancelar o Completar antes de bloqueo |
| WH/Cons/00005 | draft | Cancelar o Completar antes de bloqueo |
| CONS1198 | draft | Cancelar o Completar antes de bloqueo |
| CONS1221 | draft | Cancelar o Completar antes de bloqueo |
| CONS1299 | assigned | **Requiere revisión - tiene reservas** |
| CONS1338 | draft | Cancelar o Completar antes de bloqueo |
| CONS1361 | assigned | **Requiere revisión - tiene reservas** |
| CONS1378 | assigned | **Requiere revisión - tiene reservas** |

**VALIDACIÓN:** Bloquear tipo CONSUMO (ID 177) afectará 6 pickings draft + 3 asignados = **9 documentos requieren cierre previo**.

---

## 2.2 FASE A2: Flujo de Consumo MRP

### 2.2.1 Configuración de BOMs

| Modo de Consumo | Cantidad BOMs | Significado |
|-----------------|---------------|-------------|
| **warning** | 48 | Advierte si se consume más/menos de lo esperado |
| flexible | 2 | Permite consumir cualquier cantidad |

**HALLAZGO CONFIRMADO:** El 96% de BOMs usa modo `warning`, lo cual es correcto para control.

### 2.2.2 Análisis de Órdenes de Fabricación

De 100 órdenes de fabricación analizadas:

| Tipo de Consumo | Cantidad | Observación |
|-----------------|----------|-------------|
| Consumo automático | 0 | ⚠️ No detectado |
| Consumo separado | 29 | Consumo en momento diferente a cierre |

**HALLAZGO PROBABLE:** El consumo en MRP no es completamente automático. Requiere verificación de configuración.

### 2.2.3 Ubicaciones de Consumo en Producciones

| Ubicación Origen | Producciones | Observación |
|------------------|--------------|-------------|
| RF/Stock/Inventario Real | 15 | ✅ Correcto |
| RF/Stock/Camara 0°C REAL | 6 | ✅ Correcto |
| RF/Insumos/Bodega Insumos | 3 | ✅ Correcto |
| VLK/Camara 2 -25°C/A4 | 2 | ✅ Correcto |
| Tránsito/Salida Túneles Estáticos | 2 | ⚠️ Revisar |
| RF | 1 | ⚠️ Ubicación padre |
| VLK/Stock | 1 | ✅ Correcto |

**HALLAZGO CONFIRMADO:** Las producciones consumen desde ubicaciones correctas en su mayoría.

---

## 2.3 FASE A3: Clasificación por Familias de Productos

### 2.3.1 Resumen por Familia

| Familia | Quants Negativos | Cantidad Total Negativa | Valor Afectado | Prioridad |
|---------|------------------|------------------------|----------------|-----------|
| **MATERIAS_PRIMAS** | 497 | -5,527,790 | **$3,752,712,377** | 🔴 CRÍTICA |
| **INSUMOS_EMPAQUE** | 497 | -7,246,321 | **$1,486,725,071** | 🔴 CRÍTICA |
| **PRODUCTO_PROCESO** | 806 | -1,145,325 | **$519,576,616** | 🟠 ALTA |
| OTROS | 188 | -229,877 | $205,970,889 | 🟠 ALTA |
| BANDEJAS_RETORNABLES | 7 | -19,506 | $17,619,271 | 🟡 MEDIA |
| QUIMICOS | 5 | -1,219 | $545,713 | 🟢 BAJA |

### 2.3.2 Top 5 Productos por Familia

#### MATERIAS_PRIMAS (Prioridad CRÍTICA)
| Código | Producto | Cantidad Negativa |
|--------|----------|-------------------|
| 300002-24 | AR S/V Conv. S/C Block Bins en Bins | -2,969,637.76 |
| 300004-24 | AR S/V Org. S/C Block Bins en Bins | -2,170,885.29 |
| 300001-24 | AR S/V Conv. S/C Block 13.61 kg en Caja | -169,266.80 |
| 400025-24 | FB WF Org. IQF en Bandeja | -63,610.15 |
| 300003-24 | AR S/V Org. S/C Block 13.61 kg en Caja | -47,024.63 |

#### INSUMOS_EMPAQUE (Prioridad CRÍTICA)
| Código | Producto | Cantidad Negativa |
|--------|----------|-------------------|
| 500007 | Bandeja Verde 45x34 (A PRODUCTOR) - Sucia | -1,329,332 |
| 500008 | Bandejón IQF 60x40 (A PRODUCTOR) - Sucia | -765,002 |
| 500001-24 | BOLSA AZUL 73X58X0.060 | -750,896 |
| 500002-24 | ETIQUETAS 10x10 BLANCA | -576,165.90 |
| 500000-24 | CAJA EXPORTACIÓN 47x24.5x24.2 | -518,209 |

---

## 2.4 FASE A4: Origen de Negativos en Partners/Vendors

### 2.4.1 Hallazgos Principales

| Métrica | Valor |
|---------|-------|
| Quants negativos en vendor (ubicación ID 4) | 500+ |
| Productos afectados | 191 |

### 2.4.2 Causas Detectadas

| Causa | Productos Afectados | Estado |
|-------|---------------------|--------|
| Recepciones incompletas/fantasma | 1+ | **PROBABLE** |
| Cancelaciones posteriores | 5 | **CONFIRMADO** |
| Devoluciones mal ejecutadas | 4 | **PROBABLE** |

### 2.4.3 Top 10 Productos con Stock Negativo en Vendor

| Código | Producto | Stock Negativo | Recepciones | Devoluciones | Cancelados |
|--------|----------|----------------|-------------|--------------|------------|
| 500001-24 | BOLSA AZUL 73X58X0.060 | -596,530 | 660,630 | 0 | 2 |
| 500002-24 | ETIQUETAS 10x10 BLANCA | -547,712 | 547,712 | 0 | 0 |
| 500007-25 | Bandeja verde 45x34 | -444,805 | 54,614 | 5,438 | 45 |
| 5000018 | Bandeja IQF 60x40 | -375,563 | 48,139 | 681 | 24 |
| 500000-24 | CAJA EXPORTACIÓN 47x24.5x24.2 | -357,457 | 369,882 | 12,425 | 4 |
| 500079 | BOLSA CREATIVE GOURMET BLUEBERRY 300g | -274,888 | 1,442,913 | 0 | ⚠️ |
| 500081-24 | ETIQUETA 50x100 BLANCA | -181,255 | 181,255 | 0 | 0 |
| 500003-24 | ETIQUETAS 10x15 BLANCA | -179,602 | 188,602 | 9,000 | 0 |
| 500005-24 | ETIQUETA 10x10 VERDE | -169,884 | 169,884 | 0 | 0 |
| 500009-23-24 | Bandeja 1/8 50x30 | -110,390 | 21,421 | 2 | 13 |

**HALLAZGO CONFIRMADO:** El problema principal es que se ejecutan recepciones que "sacan" stock de vendor sin tener stock positivo previo. Esto genera el negativo.

**CAUSA RAÍZ:** Odoo descuenta automáticamente de vendor al recibir, pero si hay múltiples recepciones o cancelaciones, el balance queda negativo.

---

# 3. HALLAZGOS CONFIRMADOS VS PROBABLES

## 3.1 Hallazgos CONFIRMADOS (Validados con Evidencia)

| # | Hallazgo | Evidencia | Impacto |
|---|----------|-----------|---------|
| 1 | Tipo CONSUMO (ID 177) usado 365 veces | Query directa | 🔴 CRÍTICO |
| 2 | 99% de consumos hechos por usuario genérico "Bodega Insumos" | Query usuarios | 🔴 CRÍTICO |
| 3 | 0 pickings CONSUMO tienen correlación con OFs | Análisis origen | 🔴 CRÍTICO |
| 4 | 9 pickings CONSUMO pendientes | Query estado | 🟠 ALTO |
| 5 | 96% de BOMs usan modo warning | Query BOMs | 🟢 OK |
| 6 | RF/Insumos tiene 249 quants negativos (-1,836,045 uds) | Query quants | 🔴 CRÍTICO |
| 7 | 191 productos con negativo en Partners/Vendors | Query quants | 🔴 CRÍTICO |
| 8 | Impacto monetario total: $5,983,149,937 | Cálculo valoración | 🔴 CRÍTICO |
| 9 | 100+ capas de valoración con remaining_qty < 0 | Query layers | 🔴 CRÍTICO |
| 10 | MATERIAS_PRIMAS familia más afectada ($3.7B) | Clasificación | 🔴 CRÍTICO |

## 3.2 Hallazgos PROBABLES (Requieren Confirmación Adicional)

| # | Hallazgo | Evidencia Parcial | Validación Requerida |
|---|----------|-------------------|---------------------|
| 1 | Consumo MRP no es automático | 0 consumos automáticos detectados | Revisar config mrp.production |
| 2 | Recepciones fantasma causan negativo vendor | Exceso de recepciones vs stock | Auditar purchase.order |
| 3 | Devoluciones mal ejecutadas | 4 productos con devoluciones | Revisar stock.return.picking |
| 4 | Backdating de movimientos | No validado directamente | Comparar create_date vs date |

## 3.3 Hallazgos PENDIENTES DE VALIDACIÓN

| # | Hallazgo | Método de Validación |
|---|----------|---------------------|
| 1 | Duplicidad consumo manual + MRP | Cruzar moves por producto y fecha |
| 2 | Costeo promedio distorsionado | Revisar price_unit en svl por producto |
| 3 | Inventarios físicos discrepantes | Requiere conteo físico |

---

# 4. FLUJO OFICIAL RECOMENDADO

## 4.1 Principios del Modelo Futuro

1. **Un solo punto de consumo:** Los insumos SOLO se consumen desde órdenes de fabricación
2. **Trazabilidad completa:** Cada movimiento debe tener documento origen
3. **Usuarios nominados:** Prohibir usuarios genéricos para operaciones de stock
4. **Ajustes controlados:** Solo para regularización aprobada o conteo físico
5. **Segregación de funciones:** Quien recibe ≠ quien consume ≠ quien ajusta

## 4.2 Flujo de Recepción de Insumos

```
┌─────────────────┐
│  COMPRA (PO)    │
│  (Compras)      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  RECEPCIÓN      │
│  (Bodega)       │
│  Vendor → RF/   │
│  Insumos/Bodega │
│  Insumos        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  VALIDACIÓN     │
│  (Bodega + QC)  │
└─────────────────┘
```

**Responsables:**
- **Compras:** Crea orden de compra
- **Bodega:** Recibe con referencia a PO, valida cantidades
- **Control Calidad:** Libera producto si aplica

## 4.3 Flujo de Consumo de Insumos

```
┌─────────────────┐
│  SOLICITUD      │
│  (Producción)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  ORDEN DE       │
│  FABRICACIÓN    │
│  (MO)           │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌───────┐ ┌───────┐
│RESERVA│ │CONSUMO│
│(auto) │ │(al    │
│       │ │marcar │
│       │ │hecho) │
└───────┘ └───────┘
```

**Responsables:**
- **Producción:** Crea orden de fabricación
- **Sistema:** Reserva automática de componentes de BOM
- **Operador:** Marca componentes consumidos al procesar
- **Supervisor:** Valida y cierra MO

## 4.4 Flujo de Transferencia Interna

```
┌─────────────────┐
│  SOLICITUD      │
│  TRANSFERENCIA  │
│  (Producción)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  PICKING INT    │
│  (Bodega)       │
│  Bodega Insumos │
│  → Línea Prod   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CONFIRMACIÓN   │
│  RECEPCIÓN      │
│  (Producción)   │
└─────────────────┘
```

**Responsables:**
- **Producción:** Solicita insumos
- **Bodega:** Prepara y transfiere
- **Producción:** Confirma recepción

## 4.5 Flujo de Mermas y Ajustes

```
┌─────────────────────┐
│  DETECCIÓN MERMA    │
│  (Bodega/Producción)│
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  REGISTRO MOTIVO    │
│  (Obligatorio)      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  APROBACIÓN         │
│  (Supervisor/Jefe)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  AJUSTE INVENTARIO  │
│  (Location:         │
│  Inventory Loss)    │
└─────────────────────┘
```

**Responsables:**
- **Operador:** Detecta y reporta
- **Supervisor:** Valida causa
- **Jefe Bodega:** Aprueba ajuste
- **Sistema:** Registra con trazabilidad

## 4.6 Flujo de Devolución de Sobrantes

```
┌─────────────────────┐
│  SOBRANTE EN        │
│  PRODUCCIÓN         │
│  (Operador)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  PICKING DEVOLUCIÓN │
│  (Producción)       │
│  Línea → Bodega     │
│  Insumos            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  RECEPCIÓN          │
│  (Bodega)           │
└─────────────────────┘
```

## 4.7 Tabla Resumen de Roles y Permisos

| Rol | Recibe | Transfiere | Consume | Ajusta | Aprueba |
|-----|--------|------------|---------|--------|---------|
| Compras | ❌ | ❌ | ❌ | ❌ | ❌ |
| Bodega Recepción | ✅ | ❌ | ❌ | ❌ | ❌ |
| Bodega Despacho | ❌ | ✅ | ❌ | ❌ | ❌ |
| Operador Producción | ❌ | ❌ | ✅* | ❌ | ❌ |
| Supervisor Producción | ❌ | ❌ | ✅ | ✅** | ✅** |
| Jefe Bodega | ✅ | ✅ | ❌ | ✅ | ✅ |
| Contabilidad | ❌ | ❌ | ❌ | ❌ | ✅*** |

*Solo mediante OF  
**Solo ajustes < umbral  
***Ajustes mayores o cierre contable  

---

# 5. PLAN EXACTO DE REGULARIZACIÓN RF INSUMOS

## 5.1 PRECONDICIONES (Antes de Iniciar)

| # | Precondición | Responsable | Validación |
|---|--------------|-------------|------------|
| 1 | Backup completo de BD | TI | Confirmar restore funcional |
| 2 | Cerrar pickings CONSUMO pendientes | Bodega | 0 pickings draft/assigned |
| 3 | Congelar recepciones no urgentes | Compras | Sin POs en tránsito |
| 4 | Pausar órdenes de fabricación | Producción | MOs pausadas |
| 5 | Comunicar a usuarios | RRHH/TI | Confirmación por escrito |
| 6 | Definir fecha de corte | Gerencia | Fecha acordada |
| 7 | Preparar plantilla de conteo | Bodega | Template Excel/CSV |

## 5.2 FASE 1: CONTENCIÓN (Semana 1)

### 5.2.1 Día 1-2: Cierre de Pendientes

**Objetivo:** Eliminar pickings pendientes de tipo CONSUMO

```
ACCIONES:
1. Listar pickings CONSUMO en draft/assigned
2. Evaluar cada uno:
   - Si es válido: Completar inmediatamente
   - Si es inválido/duplicado: Cancelar
3. Documentar decisión por cada picking
```

**Pickings a Procesar:**

| Picking | Estado | Acción Sugerida | Responsable |
|---------|--------|-----------------|-------------|
| CONS1299 | assigned | Revisar y completar o cancelar | Bodega |
| CONS1361 | assigned | Revisar y completar o cancelar | Bodega |
| CONS1378 | assigned | Revisar y completar o cancelar | Bodega |
| CONS1198 | draft | Cancelar (evaluación) | Bodega |
| CONS1221 | draft | Cancelar (evaluación) | Bodega |
| CONS1338 | draft | Cancelar (evaluación) | Bodega |
| WH/Cons/* | draft | Cancelar todos | TI |

### 5.2.2 Día 3: Bloqueo de Tipo CONSUMO

**Acción en Odoo:**
```
Inventario > Configuración > Tipos de Operación > CONSUMO (ID 177)
- Marcar como: Activo = False
O
- Restringir grupos de usuarios autorizados a ninguno
```

**Advertencia:** Verificar que no hay procesos automatizados que dependan de este tipo.

### 5.2.3 Día 4-5: Restricción de Usuario Genérico

**Acción:**
```
1. Usuario "Bodega Insumos":
   - Desactivar o limitar permisos a solo lectura
   - Crear usuarios nominados para cada persona

2. Nuevos usuarios:
   - Nombre_Apellido_Bodega (ej: Juan_Perez_Bodega)
   - Asignar grupo: Bodega / Usuario
   - Sin permisos de ajuste de inventario
```

## 5.3 FASE 2: CONTEO FÍSICO (Semana 2)

### 5.3.1 Preparación

**Plantilla de Conteo:**

| Código | Producto | Ubicación | Stock Sistema | Stock Físico | Diferencia | Observaciones |
|--------|----------|-----------|---------------|--------------|------------|---------------|
| [auto] | [auto] | RF/Insumos/Bodega Insumos | [auto] | [manual] | [calc] | [manual] |

**Productos Prioritarios para Conteo:**

```
CRÍTICOS (Conteo obligatorio):
- 500007: Bandeja Verde 45x34 (-1,329,332)
- 500008: Bandejón IQF 60x40 (-765,002)
- 500001-24: BOLSA AZUL 73X58X0.060 (-750,896)
- 500002-24: ETIQUETAS 10x10 BLANCA (-576,166)
- 500000-24: CAJA EXPORTACIÓN 47x24.5x24.2 (-518,209)

ALTOS (Conteo recomendado):
- Todos los códigos 500xxx con negativo
- Todos los códigos 300xxx y 400xxx con negativo
```

### 5.3.2 Ejecución del Conteo

**Metodología:**
1. **Día 1:** Imprimir listado, organizar equipos
2. **Día 2-3:** Conteo principal (sin movimientos)
3. **Día 4:** Reconteo de diferencias significativas (>5%)
4. **Día 5:** Consolidación y validación cruzada

**Equipos de Conteo:**
- Equipo 1: Zona A (Estanterías 1-10)
- Equipo 2: Zona B (Estanterías 11-20)
- Equipo 3: Zona C (Piso y otros)

**Reglas:**
- Conteo ciego (sin ver stock sistema inicialmente)
- Doble conteo para items críticos
- Fotografía de discrepancias mayores

### 5.3.3 Validación de Resultados

**Criterios de Aceptación:**

| Rango Diferencia | Acción |
|------------------|--------|
| < 1% | Ajustar automáticamente |
| 1% - 5% | Verificar con supervisor, ajustar |
| 5% - 10% | Reconteo obligatorio |
| > 10% | Investigación antes de ajustar |

## 5.4 FASE 3: REGULARIZACIÓN (Semana 3-4)

### 5.4.1 Preparación de Ajustes

**Crear Ajuste de Inventario en Odoo:**
```
Inventario > Operaciones > Ajustes de Inventario > Crear
- Nombre: REGULARIZACIÓN RF INSUMOS 2026-03
- Ubicación: RF/Insumos/Bodega Insumos
- Incluir productos: Agotados ✅
- Fecha contable: [Fecha de corte acordada]
```

### 5.4.2 Carga de Diferencias

**Método 1: Manual (< 50 productos)**
```
1. Abrir ajuste de inventario
2. Agregar línea por línea
3. Ingresar cantidad física real
4. Validar diferencia calculada
```

**Método 2: Importación CSV (> 50 productos)**
```csv
product_id,location_id,inventory_quantity
[ID_PRODUCTO1],[ID_UBICACION],150
[ID_PRODUCTO2],[ID_UBICACION],2000
...
```

### 5.4.3 Ejecución por Lotes

**Lote 1: Productos con negativo extremo (Día 1-2)**
- Stock inicial < -100,000 unidades
- Productos: 500007, 500008, 500001-24, etc.

**Lote 2: Productos con negativo moderado (Día 3-4)**
- Stock inicial entre -10,000 y -100,000
- Verificación individual

**Lote 3: Productos con negativo menor (Día 5-7)**
- Stock inicial > -10,000
- Carga masiva

### 5.4.4 Validación Contable

**Después de cada lote:**
```
1. Verificar asiento contable generado
2. Confirmar cuentas afectadas:
   - Debe: Pérdida por ajuste inventario
   - Haber: Stock de inventario
3. Conciliar con libro mayor
4. Aprobar por Contabilidad
```

## 5.5 FASE 4: CONTROLES POSTERIORES (Semana 5+)

### 5.5.1 Validaciones Inmediatas

| Validación | Criterio Éxito | Responsable |
|------------|----------------|-------------|
| Quants negativos RF/Insumos | = 0 | TI |
| Productos con stock negativo total | Reducido >80% | TI |
| Ajuste contable cuadrado | Diferencia 0 | Contabilidad |
| Usuarios nominados operando | 100% | RRHH |

### 5.5.2 Monitoreo Semanal

```
REPORTE SEMANAL:
1. Top 10 productos con mayor movimiento
2. Lista de ajustes realizados
3. Detección de nuevos negativos (alerta inmediata)
4. Uso de tipos de operación (no debe aparecer CONSUMO)
```

## 5.6 ROLLBACK (Si Algo Sale Mal)

### 5.6.1 Criterios de Rollback

| Situación | Acción |
|-----------|--------|
| Error en ajuste masivo | Cancelar ajuste, restaurar backup |
| Discrepancia contable grave | Pausar, investigar, corregir |
| Sistema inestable | Restaurar backup, reintentar |

### 5.6.2 Procedimiento de Rollback

```
1. DETENER toda operación
2. Evaluar impacto:
   - ¿Cuántos ajustes se aplicaron?
   - ¿Hay asientos contables confirmados?
3. Si ajustes no validados:
   - Cancelar ajuste de inventario
   - Volver a estado anterior
4. Si ajustes validados:
   - Crear ajuste inverso (con aprobación)
   - Documentar motivo
5. Restaurar backup solo como último recurso
```

---

# 6. CRITERIOS PARA RESTRICCIÓN DE CONSUMO MANUAL

## 6.1 Decisión: Bloquear Tipo CONSUMO (ID 177)

**RECOMENDACIÓN: ✅ SÍ BLOQUEAR**

### 6.1.1 Justificación

| Factor | Análisis |
|--------|----------|
| **Uso actual** | 365 pickings completados |
| **Correlación MRP** | 0% - No vinculado a OFs |
| **Usuario principal** | Genérico (Bodega Insumos) - sin trazabilidad |
| **Alternativa existente** | Consumo vía MRP funcional |
| **Riesgo de bloqueo** | 9 pickings pendientes (manejables) |
| **Impacto operativo** | BAJO si se migra a flujo MRP |

### 6.1.2 Criterios Técnicos de Bloqueo

```python
# Pseudocódigo de validación pre-bloqueo

def puede_bloquear_tipo_operacion(tipo_id):
    pickings_pendientes = count(stock.picking where 
        picking_type_id = tipo_id AND 
        state in ['draft', 'waiting', 'confirmed', 'assigned'])
    
    if pickings_pendientes > 0:
        return False, f"Hay {pickings_pendientes} pickings pendientes"
    
    procesos_automaticos = check_automations(tipo_id)
    if procesos_automaticos:
        return False, f"Hay {procesos_automaticos} automatizaciones"
    
    return True, "Puede bloquearse"
```

### 6.1.3 Acciones Post-Bloqueo

1. **Comunicar a usuarios:** Email + capacitación
2. **Alternativa:** Crear solicitud de transferencia a producción
3. **Monitoreo:** Alertar si alguien intenta usar

## 6.2 Excepciones Permitidas

| Escenario | Solución | Aprobación |
|-----------|----------|------------|
| Emergencia producción | Transferencia interna expedita | Supervisor |
| Muestra a cliente | Picking tipo "Muestra" (crear) | Jefe Bodega |
| Consumo laboratorio | Picking tipo "Laboratorio" (crear) | QC Manager |
| Merma detectada | Ajuste de inventario | Jefe Bodega |

---

# 7. IMPACTO CONTABLE POR PRIORIDAD

## 7.1 Resumen de Impacto Total

| Categoría | Valor Afectado | % del Total | Prioridad |
|-----------|----------------|-------------|-----------|
| PRODUCTOS / PTT | ~$3,500,000,000 | 58.5% | 🔴 CRÍTICA |
| INSUMOS PRODUCCIÓN | ~$1,500,000,000 | 25.1% | 🔴 CRÍTICA |
| PRODUCTOS / PSP | ~$700,000,000 | 11.7% | 🟠 ALTA |
| OTROS | ~$280,000,000 | 4.7% | 🟡 MEDIA |
| **TOTAL** | **~$5,983,149,937** | 100% | - |

## 7.2 Top 20 Productos por Impacto Monetario

| # | Código | Producto | Categoría | Stock Neg. | Precio | Impacto |
|---|--------|----------|-----------|------------|--------|---------|
| 1 | 300002-24 | AR S/V Conv. S/C Block Bins | PRODUCTOS/PTT | -2,969,638 | $849 | **$2,522,401,404** |
| 2 | 300004-24 | AR S/V Org. S/C Block Bins | PRODUCTOS/PTT | -2,170,885 | $392 | **$850,987,034** |
| 3 | 200029-24 | FB MK Conv. S/C IQF Bandeja | PRODUCTOS/MP IQF | -110,119 | $3,229 | **$355,586,527** |
| 4 | 500000-24 | CAJA EXPORTACIÓN | INV/INSUMOS PROD | -518,209 | $599 | $310,407,191 |
| 5 | 200017-24 | FB MK Conv. S/C PSP 10 kg | PRODUCTOS/PSP | -86,687 | $3,380 | $292,974,414 |
| 6 | 200012-24 | AR HB Org. >12 mm PSP | PRODUCTOS/PSP | -160,918 | $1,562 | $251,402,009 |
| 7 | 400025-24 | FB WF Org. IQF en Bandeja | PRODUCTOS/MP IQF | -63,610 | $2,361 | $150,214,988 |
| 8 | - | GUANTES NITRILO (ARCHIVAR) | INV/EPP | -47,610 | $2,749 | $130,865,131 |
| 9 | 200023-24 | FB MK Conv. S/C IQF A 10 kg | PRODUCTOS/PTT | -26,640 | $3,739 | $99,595,158 |
| 10 | 400027-24 | FB WF Conv. IQF en Bandeja | PRODUCTOS/MP IQF | -38,100 | $1,917 | $73,031,798 |
| 11 | 300001-24 | AR S/V Conv. S/C Block 13.61 kg | PRODUCTOS/PTT | -169,267 | $413 | $69,848,961 |
| 12 | 500001-24 | BOLSA AZUL 73X58X0.060 | INV/INSUMOS PROD | -750,896 | $89 | $66,829,744 |
| 13 | 200035-24 | AR HB Org. S/C IQF Bandeja | PRODUCTOS/MP IQF | -33,373 | $1,705 | $56,884,549 |
| 14 | 200031-24 | AR HB Conv. S/C IQF Bandeja | PRODUCTOS/MP IQF | -35,429 | $1,572 | $55,684,850 |
| 15 | 500062-24 | MASCARILLAS 3 PLIEGUES | INV/EPP | -51,770 | $975 | $50,451,004 |
| 16 | 200004-24 | AR HB Conv. >11 mm PSP | PRODUCTOS/PSP | -6,934 | $7,000 | $48,540,819 |
| 17 | 5000018 | Bandeja IQF 60x40 | BANDEJAS | -375,563 | $120 | $45,235,437 |
| 18 | 200011-24 | AR HB Org. <11 mm PSP | PRODUCTOS/PSP | -30,486 | $1,409 | $42,946,161 |
| 19 | 200026-24 | FB WF Org. S/C IQF A 10 kg | PRODUCTOS/PTT | -8,800 | $3,570 | $31,416,000 |
| 20 | 200020-24 | FB WF Org. S/C PSP 10 kg | PRODUCTOS/PSP | -11,560 | $2,538 | $29,340,378 |

## 7.3 Cuentas Contables Afectadas

| Cuenta | Nombre | Tipo | Riesgo |
|--------|--------|------|--------|
| 11040101 | MATERIAS PRIMAS | Activo | 🔴 Alto |
| 11040104 | PRODUCTOS EN PROCESOS | Activo | 🔴 Alto |
| 11040107 | EPP Y OTROS INSUMOS | Activo | 🟠 Medio |
| 11040108 | EXISTENCIAS EN TRÁNSITO | Activo | 🟡 Bajo |
| 110610 | Mercaderías | Activo | 🟠 Medio |
| 210230 | Facturas por Recibir | Pasivo | 🟡 Bajo |
| 21020107 | FACTURAS POR RECIBIR PRODUCTORES | Pasivo | 🟡 Bajo |
| 52020111 | OTROS MATERIALES INSUMOS PRODUCCIÓN | Gasto | 🟠 Medio |
| 52020113 | INSUMOS DE LIMPIEZA PROCESOS | Gasto | 🟢 Bajo |
| 52060204 | ROPA DE TRABAJO EPP | Gasto | 🟢 Bajo |

## 7.4 Riesgos para Cierre Contable

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Descuadre de inventarios | ALTA | CRÍTICO | Regularizar antes de cierre |
| Costo promedio distorsionado | ALTA | ALTO | Revisar SVL antes de cierre |
| Asientos no cuadrados | MEDIA | ALTO | Validación por Contabilidad |
| Informes históricos afectados | BAJA | MEDIO | Documentar ajustes con fecha de corte |

## 7.5 Recomendación de Priorización

**ORDEN DE REGULARIZACIÓN POR IMPACTO:**

| Prioridad | Familia | Productos | Valor | Plazo Sugerido |
|-----------|---------|-----------|-------|----------------|
| 1 | PRODUCTOS / PTT | 300002-24, 300004-24, 200023-24 | $3.5B | Semana 1 |
| 2 | INSUMOS PRODUCCIÓN | 500000-24, 500001-24 | $1.5B | Semana 1-2 |
| 3 | PRODUCTOS / PSP | 200012-24, 200017-24 | $0.7B | Semana 2 |
| 4 | OTROS | EPP, Bandejas | $0.3B | Semana 3-4 |

---

# 8. MATRIZ DE RIESGOS

## 8.1 Riesgos del Proyecto de Regularización

| ID | Riesgo | Probabilidad | Impacto | Nivel | Mitigación |
|----|--------|--------------|---------|-------|------------|
| R1 | Resistencia al cambio de usuarios | ALTA | MEDIO | 🟠 | Capacitación, comunicación clara |
| R2 | Discrepancias en conteo físico | ALTA | ALTO | 🔴 | Doble conteo, supervisor |
| R3 | Error en carga masiva de ajustes | MEDIA | CRÍTICO | 🔴 | Validación previa, lotes pequeños |
| R4 | Interrupción de operaciones | MEDIA | ALTO | 🟠 | Ejecutar en horario bajo |
| R5 | Impacto contable inesperado | MEDIA | CRÍTICO | 🔴 | Validación Contabilidad antes |
| R6 | Usuarios usan flujo antiguo | MEDIA | MEDIO | 🟠 | Monitoreo, alertas |
| R7 | Falla de backup/restore | BAJA | CRÍTICO | 🟠 | Probar restore antes |
| R8 | Stock negativo nuevo post-regularización | MEDIA | ALTO | 🟠 | Monitoreo diario |

## 8.2 Riesgos de NO Actuar

| ID | Riesgo | Probabilidad | Impacto | Nivel | Consecuencia |
|----|--------|--------------|---------|-------|--------------|
| RN1 | Cierre contable incorrecto | ALTA | CRÍTICO | 🔴 | Auditoría externa negativa |
| RN2 | Costeo de productos erróneo | ALTA | ALTO | 🔴 | Precios mal calculados |
| RN3 | Pérdida de trazabilidad | ALTA | ALTO | 🔴 | Imposible auditar |
| RN4 | Crecimiento exponencial del problema | ALTA | CRÍTICO | 🔴 | Cada día más difícil corregir |
| RN5 | Decisiones basadas en datos erróneos | ALTA | ALTO | 🔴 | Mala gestión de compras |

## 8.3 Plan de Respuesta a Riesgos

| Riesgo | Trigger | Respuesta | Responsable | Escalamiento |
|--------|---------|-----------|-------------|--------------|
| R1 | Quejas de usuarios | Reunión explicativa | RRHH | Gerencia |
| R2 | Diferencia >10% | Reconteo inmediato | Supervisor | Jefe Bodega |
| R3 | Error en validación | Cancelar ajuste, revisar | TI | Gerencia TI |
| R4 | Operación detenida >2h | Rollback parcial | TI | Gerencia |
| R5 | Descuadre >$1M | Pausar, investigar | Contabilidad | CFO |
| R6 | Detección uso CONSUMO | Bloqueo inmediato + comunicación | TI | RRHH |
| R7 | Backup corrupto | Contactar proveedor Odoo | TI | Gerencia TI |
| R8 | Nuevo negativo detectado | Investigar causa raíz | Bodega | Jefe Bodega |

---

# 9. PROPUESTA TÉCNICA DE CAMBIOS

## 9.1 Cambios en Configuración de Odoo

### 9.1.1 Tipos de Operación

| Acción | Tipo | ID | Configuración |
|--------|------|-----|---------------|
| **DESACTIVAR** | CONSUMO | 177 | active = False |
| MANTENER | Consumo de Inventario | 150 | Evaluar uso, posible desactivar |
| MANTENER | Consumo de Inventario | 165 | Sin uso, desactivar |
| CREAR | Transferencia a Producción | (nuevo) | RF/Insumos → RF/Stock/Producción |
| CREAR | Devolución de Producción | (nuevo) | RF/Stock/Producción → RF/Insumos |

### 9.1.2 Ubicaciones

| Acción | Ubicación | Configuración |
|--------|-----------|---------------|
| REVISAR | Virtual Locations/Consumo-CentroCosto (5478) | Evaluar si eliminar o restringir |
| CREAR | RF/Stock/Producción | Nueva ubicación de consumo temporal |
| RESTRINGIR | RF/Insumos | Solo acceso Bodega |

### 9.1.3 Reglas de Abastecimiento

```
CONFIGURACIÓN MRP:
1. mrp.production:
   - location_src_id: RF/Insumos/Bodega Insumos
   - Consumo automático: Activar al marcar como hecho
   
2. mrp.bom:
   - consumption: 'warning' (mantener)
   - Añadir validación de componentes
```

## 9.2 Cambios en Permisos de Usuario

### 9.2.1 Grupos de Usuarios a Modificar

| Grupo | Permiso Actual | Permiso Nuevo |
|-------|----------------|---------------|
| Bodega / Usuario | Ajuste inventario | Solo lectura |
| Bodega / Responsable | Todos los ajustes | Ajustes < umbral |
| Bodega / Manager | Todos | Mantener |
| Producción / Usuario | Consumo manual | Solo vía MRP |
| Producción / Responsable | Consumo manual | Solo vía MRP + aprobación |

### 9.2.2 Usuarios a Modificar

| Usuario | Acción | Nuevo Estado |
|---------|--------|--------------|
| Bodega Insumos | DESACTIVAR | Archivado |
| [Crear usuarios nominados] | CREAR | Activo con permisos limitados |
| DIEGO EUDALDO SAAVEDRA | REVISAR | Validar permisos actuales |

### 9.2.3 Reglas de Registro (Record Rules)

```python
# Regla: Solo Bodega Manager puede ajustar inventario
<record id="rule_inventory_adjustment_manager" model="ir.rule">
    <field name="name">Solo Manager ajusta inventario</field>
    <field name="model_id" ref="stock.model_stock_inventory"/>
    <field name="domain_force">[('state','=','draft')]</field>
    <field name="groups" eval="[(4, ref('stock.group_stock_manager'))]"/>
    <field name="perm_write" eval="True"/>
    <field name="perm_create" eval="True"/>
</record>

# Regla: Bloquear tipo operación CONSUMO
<record id="rule_block_consumo_type" model="ir.rule">
    <field name="name">Bloquear Tipo CONSUMO</field>
    <field name="model_id" ref="stock.model_stock_picking"/>
    <field name="domain_force">[('picking_type_id','!=',177)]</field>
    <field name="groups" eval="[(4, ref('base.group_user'))]"/>
    <field name="perm_create" eval="True"/>
</record>
```

## 9.3 Cambios en MRP

### 9.3.1 Configuración de Consumo Automático

```
Fabricación > Configuración > Ajustes:
✅ Consumo automático
✅ Reserva automática (en confirmación)
✅ Registro de lotes/series
```

### 9.3.2 BOMs - Validaciones Requeridas

| Validación | Estado | Acción |
|------------|--------|--------|
| Componentes con ubicación definida | PENDIENTE | Revisar cada BOM |
| Rutas de consumo correctas | PENDIENTE | Validar rutas |
| Productos fantasma | REVISAR | Verificar no causan duplicidad |

## 9.4 Automatizaciones a Implementar

### 9.4.1 Alerta de Stock Negativo

```python
# Acción automatizada: Alerta stock negativo
<record id="action_alert_negative_stock" model="ir.actions.server">
    <field name="name">Alerta Stock Negativo</field>
    <field name="model_id" ref="stock.model_stock_quant"/>
    <field name="trigger">on_create_or_write</field>
    <field name="state">email</field>
    <field name="code">
        if record.quantity < 0:
            record.env['mail.mail'].create({
                'subject': f'ALERTA: Stock negativo - {record.product_id.name}',
                'body_html': f'''
                    <p>Se detectó stock negativo:</p>
                    <ul>
                        <li>Producto: {record.product_id.display_name}</li>
                        <li>Ubicación: {record.location_id.complete_name}</li>
                        <li>Cantidad: {record.quantity}</li>
                    </ul>
                ''',
                'email_to': 'bodega@riofuturo.cl,ti@riofuturo.cl',
            }).send()
    </field>
</record>
```

### 9.4.2 Bloqueo de Consumo Manual

```python
# Restricción en stock.move
@api.constrains('picking_type_id')
def _check_picking_type_consumo(self):
    consumo_type_ids = [177]  # IDs de tipos CONSUMO bloqueados
    for move in self:
        if move.picking_type_id.id in consumo_type_ids:
            raise ValidationError(
                'El tipo de operación CONSUMO está bloqueado. '
                'Use órdenes de fabricación para consumir insumos.'
            )
```

---

# 10. SCRIPTS DE MONITOREO POST-CORRECCIÓN

## 10.1 Script: Reporte Diario de Stock Negativo

```python
#!/usr/bin/env python3
"""
MONITOREO DIARIO: Stock Negativo
Ejecutar diariamente a las 6:00 AM
"""

import xmlrpc.client
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuración
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"  # Usuario de monitoreo
PASSWORD = "xxxxx"  # Usar secreto

def check_negative_stock():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Buscar quants negativos
    negative_quants = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_read',
        [[('quantity', '<', 0)]],
        {'fields': ['product_id', 'location_id', 'quantity'], 'limit': 100}
    )
    
    # Filtrar RF/Insumos
    rf_insumos_negatives = [
        q for q in negative_quants 
        if 'RF/Insumos' in str(q.get('location_id', ['', ''])[1])
    ]
    
    return {
        'total_negatives': len(negative_quants),
        'rf_insumos_negatives': len(rf_insumos_negatives),
        'details': negative_quants[:20]
    }

def send_alert(data):
    if data['rf_insumos_negatives'] > 0:
        # Enviar alerta
        msg = MIMEMultipart()
        msg['Subject'] = f"⚠️ ALERTA: {data['rf_insumos_negatives']} negativos en RF/Insumos"
        msg['From'] = 'sistema@riofuturo.cl'
        msg['To'] = 'bodega@riofuturo.cl,ti@riofuturo.cl'
        
        body = f"""
        REPORTE DE MONITOREO - {datetime.now().strftime('%Y-%m-%d %H:%M')}
        
        Total quants negativos: {data['total_negatives']}
        Negativos en RF/Insumos: {data['rf_insumos_negatives']}
        
        Detalle (primeros 20):
        """
        for q in data['details']:
            body += f"\n- {q['product_id'][1]}: {q['quantity']} en {q['location_id'][1]}"
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Enviar email (configurar SMTP)
        # smtp = smtplib.SMTP('smtp.riofuturo.cl')
        # smtp.send_message(msg)
        print(body)

if __name__ == "__main__":
    data = check_negative_stock()
    send_alert(data)
```

## 10.2 Script: Verificación de Uso de Tipo CONSUMO

```python
#!/usr/bin/env python3
"""
MONITOREO: Detección de uso de tipo CONSUMO bloqueado
Ejecutar cada hora
"""

import xmlrpc.client
from datetime import datetime, timedelta

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"
PASSWORD = "xxxxx"

BLOCKED_TYPES = [177]  # IDs de tipos bloqueados

def check_blocked_type_usage():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Buscar pickings de última hora
    one_hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    recent_blocked = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.picking', 'search_read',
        [[
            ('picking_type_id', 'in', BLOCKED_TYPES),
            ('create_date', '>=', one_hour_ago)
        ]],
        {'fields': ['name', 'create_uid', 'state', 'create_date']}
    )
    
    if recent_blocked:
        print("⚠️ ALERTA: Intento de uso de tipo CONSUMO bloqueado")
        for p in recent_blocked:
            print(f"  - {p['name']} por {p['create_uid'][1]} ({p['state']})")
        # Enviar alerta a TI
    else:
        print(f"✅ Sin uso de tipos bloqueados en última hora ({datetime.now()})")

if __name__ == "__main__":
    check_blocked_type_usage()
```

## 10.3 Script: Reporte Semanal de Regularización

```python
#!/usr/bin/env python3
"""
REPORTE SEMANAL: Estado de Regularización
Ejecutar domingos a las 20:00
"""

import xmlrpc.client
from datetime import datetime, timedelta
import json

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"
PASSWORD = "xxxxx"

def generate_weekly_report():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # 1. Conteo de negativos por ubicación
    negative_summary = {}
    locations = ['RF/Insumos', 'Partners/Vendors', 'Virtual Locations']
    
    for loc_name in locations:
        locs = models.execute_kw(
            DB, uid, PASSWORD,
            'stock.location', 'search',
            [[('complete_name', 'ilike', loc_name)]]
        )
        
        neg_count = models.execute_kw(
            DB, uid, PASSWORD,
            'stock.quant', 'search_count',
            [[('location_id', 'in', locs), ('quantity', '<', 0)]]
        )
        
        negative_summary[loc_name] = neg_count
    
    # 2. Ajustes de la semana
    one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    adjustments = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_count',
        [[
            ('inventory_quantity_set', '=', True),
            ('write_date', '>=', one_week_ago)
        ]]
    )
    
    # 3. Movimientos tipo CONSUMO (debería ser 0)
    consumo_moves = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.picking', 'search_count',
        [[
            ('picking_type_id', '=', 177),
            ('create_date', '>=', one_week_ago)
        ]]
    )
    
    report = {
        'fecha': datetime.now().isoformat(),
        'negativos_por_ubicacion': negative_summary,
        'ajustes_semana': adjustments,
        'uso_tipo_consumo': consumo_moves,
        'status': 'OK' if consumo_moves == 0 else 'ALERTA'
    }
    
    print(json.dumps(report, indent=2, ensure_ascii=False))
    
    # Guardar en archivo
    with open(f'reporte_semanal_{datetime.now().strftime("%Y%m%d")}.json', 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    return report

if __name__ == "__main__":
    generate_weekly_report()
```

## 10.4 Script: Validación de Integridad Stock

```python
#!/usr/bin/env python3
"""
VALIDACIÓN: Integridad de Stock
Compara stock calculado vs stock.quant
Ejecutar mensualmente
"""

import xmlrpc.client
from collections import defaultdict

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "monitor@riofuturo.cl"
PASSWORD = "xxxxx"

def validate_stock_integrity():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Obtener ubicación RF/Insumos/Bodega Insumos
    loc_id = 24  # RF/Insumos/Bodega Insumos
    
    # 1. Stock según quants
    quants = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_read',
        [[('location_id', '=', loc_id)]],
        {'fields': ['product_id', 'quantity']}
    )
    
    quant_stock = defaultdict(float)
    for q in quants:
        quant_stock[q['product_id'][0]] += q['quantity']
    
    # 2. Stock según movimientos
    moves_in = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.move', 'search_read',
        [[('location_dest_id', '=', loc_id), ('state', '=', 'done')]],
        {'fields': ['product_id', 'quantity_done']}
    )
    
    moves_out = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.move', 'search_read',
        [[('location_id', '=', loc_id), ('state', '=', 'done')]],
        {'fields': ['product_id', 'quantity_done']}
    )
    
    move_stock = defaultdict(float)
    for m in moves_in:
        move_stock[m['product_id'][0]] += m['quantity_done']
    for m in moves_out:
        move_stock[m['product_id'][0]] -= m['quantity_done']
    
    # 3. Comparar
    discrepancies = []
    all_products = set(quant_stock.keys()) | set(move_stock.keys())
    
    for prod_id in all_products:
        qs = quant_stock.get(prod_id, 0)
        ms = move_stock.get(prod_id, 0)
        diff = abs(qs - ms)
        
        if diff > 0.01:  # Tolerancia de 0.01
            discrepancies.append({
                'product_id': prod_id,
                'stock_quant': qs,
                'stock_moves': ms,
                'difference': diff
            })
    
    if discrepancies:
        print(f"⚠️ {len(discrepancies)} discrepancias encontradas:")
        for d in sorted(discrepancies, key=lambda x: -x['difference'])[:10]:
            print(f"  Producto {d['product_id']}: Quant={d['stock_quant']:.2f}, Moves={d['stock_moves']:.2f}, Diff={d['difference']:.2f}")
    else:
        print("✅ Sin discrepancias de integridad")
    
    return discrepancies

if __name__ == "__main__":
    validate_stock_integrity()
```

## 10.5 Configuración de Ejecución Automática (Cron)

```bash
# /etc/cron.d/odoo_monitoring

# Diario a las 6:00 - Stock negativo
0 6 * * * odoo_monitor /opt/scripts/check_negative_stock.py >> /var/log/odoo_monitor.log 2>&1

# Cada hora - Uso de tipo CONSUMO
0 * * * * odoo_monitor /opt/scripts/check_blocked_type_usage.py >> /var/log/odoo_monitor.log 2>&1

# Domingo 20:00 - Reporte semanal
0 20 * * 0 odoo_monitor /opt/scripts/generate_weekly_report.py >> /var/log/odoo_monitor.log 2>&1

# Día 1 de cada mes - Validación de integridad
0 3 1 * * odoo_monitor /opt/scripts/validate_stock_integrity.py >> /var/log/odoo_monitor.log 2>&1
```

---

# ANEXOS

## Anexo A: Checklist de Implementación

- [ ] **Semana 0: Preparación**
  - [ ] Backup de BD verificado
  - [ ] Comunicación a usuarios enviada
  - [ ] Plantillas de conteo preparadas
  - [ ] Equipos de conteo asignados

- [ ] **Semana 1: Contención**
  - [ ] Pickings CONSUMO pendientes cerrados
  - [ ] Tipo CONSUMO (177) desactivado
  - [ ] Usuario "Bodega Insumos" desactivado
  - [ ] Usuarios nominados creados

- [ ] **Semana 2: Conteo**
  - [ ] Conteo físico ejecutado
  - [ ] Diferencias documentadas
  - [ ] Reconteos realizados

- [ ] **Semana 3-4: Regularización**
  - [ ] Lote 1 (críticos) regularizado
  - [ ] Lote 2 (moderados) regularizado
  - [ ] Lote 3 (menores) regularizado
  - [ ] Validación contable aprobada

- [ ] **Semana 5+: Monitoreo**
  - [ ] Scripts de monitoreo instalados
  - [ ] Alertas configuradas
  - [ ] Primer reporte semanal generado

## Anexo B: Contactos Clave

| Rol | Nombre | Email | Teléfono |
|-----|--------|-------|----------|
| Jefe Proyecto | [Completar] | | |
| Jefe Bodega | [Completar] | | |
| Contador | [Completar] | | |
| TI Odoo | [Completar] | | |
| Soporte Odoo | oerpondemand | | |

## Anexo C: Historial de Versiones

| Versión | Fecha | Cambios | Autor |
|---------|-------|---------|-------|
| 1.0 | 2026-03-10 | Documento inicial | Consultoría AI |

---

**FIN DEL DOCUMENTO**

*Este plan debe ser revisado y aprobado por Gerencia, Contabilidad y TI antes de su ejecución.*
