# AUDITORÍA EXHAUSTIVA DE CONSUMO DE INSUMOS - ODOO 16
## Rio Futuro Procesos SPA - Marzo 2026

---

# ÍNDICE
1. [Resumen Ejecutivo](#1-resumen-ejecutivo)
2. [Diagnóstico Técnico-Funcional](#2-diagnóstico-técnico-funcional)
3. [Hallazgos con Evidencia](#3-hallazgos-con-evidencia)
4. [Productos Críticos con Stock Negativo](#4-productos-críticos-con-stock-negativo)
5. [Movimientos Sospechosos o Duplicados](#5-movimientos-sospechosos-o-duplicados)
6. [Usuarios y Operaciones Ejecutadas](#6-usuarios-y-operaciones-ejecutadas)
7. [Análisis de Impacto por Escenario](#7-análisis-de-impacto-por-escenario)
8. [Propuesta de Soluciones](#8-propuesta-de-soluciones)
9. [Recomendación Final](#9-recomendación-final)
10. [Plan de Regularización](#10-plan-de-regularización)
11. [Flujo Futuro Correcto](#11-flujo-futuro-correcto)
12. [Mejoras en Permisos y Procesos](#12-mejoras-en-permisos-y-procesos)
13. [Scripts de Validación](#13-scripts-de-validación)

---

# 1. RESUMEN EJECUTIVO

## Situación Crítica

El sistema Odoo 16 de Rio Futuro presenta un problema **SISTÉMICO Y GRAVE** de gestión de inventario que afecta principalmente a:

| Métrica | Valor | Severidad |
|---------|-------|-----------|
| Productos con stock negativo | **937** | 🔴 CRÍTICO |
| Quants negativos totales | **2,000+** | 🔴 CRÍTICO |
| Cantidad negativa en Partners/Vendors | **-20,235,331.65 kg** | 🔴 CRÍTICO |
| Cantidad negativa en Ubicación Procesos | **-8,098,888.22 kg** | 🔴 CRÍTICO |
| Movimientos manuales sin control | **500+** | 🟠 ALTO |
| Movimientos sospechosos detectados | **491** | 🟠 ALTO |
| Productos con duplicidad confirmada | **3+** | 🟡 MEDIO |

## Causa Raíz Principal

**El problema NO es únicamente duplicidad de consumos entre bodega y producción.** La causa raíz es **MÚLTIPLE**:

1. **Recepciones sin origen válido**: La ubicación `Partners/Vendors` tiene 733 quants negativos por valor de -20 millones. Esto indica que se han registrado salidas de producto desde proveedores sin las entradas correspondientes (recepciones fantasma o cancelaciones mal ejecutadas).

2. **Uso incorrecto de ajustes de inventario**: El usuario "Bodega Insumos" tiene 279 ajustes de salida con efecto neto de -733,628 unidades. Se están usando ajustes como parche operativo.

3. **Movimientos manuales masivos**: 500+ movimientos sin picking ni orden de producción asociada.

4. **Consumos desde múltiples ubicaciones**: Las órdenes de producción están consumiendo simultáneamente desde ubicaciones incompatibles.

5. **Configuración incorrecta de ubicaciones virtuales**: Se están acumulando stocks negativos en ubicaciones de proceso.

## Impacto Estimado

- **Operativo**: Stock no confiable, imposible planificar compras/producción
- **Contable**: Valorización distorsionada en millones de pesos
- **Regulatorio**: Posible impacto en trazabilidad SAG/HACCP
- **Económico**: Pérdidas no cuantificadas por falta de control

---

# 2. DIAGNÓSTICO TÉCNICO-FUNCIONAL

## 2.1 Entorno Analizado

| Parámetro | Valor |
|-----------|-------|
| Versión Odoo | 16.0+e (Enterprise) |
| Base de datos | riofuturo-master |
| Empresa principal | RIO FUTURO PROCESOS SPA |
| Almacenes | 7 (RF, VLK, San Jose, Puerto Varas, Linares, LVR, ISC) |
| Ubicaciones internas | 500+ |

## 2.2 Estructura de Almacenes

| Código | Almacén | Ubicación Stock Principal |
|--------|---------|---------------------------|
| RF | Rio Futuro | RF/Stock |
| VLK | VILKUN | VLK/Stock |
| Sjose | San Jose | Sjose/Stock |
| PtoVa | Puerto Varas | PtoVa/Stock |
| Lina | Linares | Lina/Stock |
| LVR | LVR | LVR/Stock |
| ISC | Ice Star Coronel | ISC/Stock |

## 2.3 RF INSUMOS - Estructura Identificada

La ubicación **RF INSUMOS** está configurada como:

```
RF/Insumos (ID: 5474)
├── Bodega Insumos (ID: 24)
│   ├── BINC0101 ... BINC0516 (sub-ubicaciones por rack)
├── Bodega Químicos (ID: 25)
```

**Problemas detectados en RF INSUMOS:**
- Stock negativo total: **-938,657.22 unidades**
- 46 quants con cantidad negativa
- Productos más afectados:
  - CAJA EXPORTACIÓN: -93,776 unidades
  - BOLSA CREATIVE GOURMET BLUEBERRY: -212,893 unidades (suma múltiples quants)
  - BOLSA AZUL 73X58X0.060: -58,610 unidades

## 2.4 Tipos de Operación Relevantes

| ID | Tipo | Código | Pickings Done | Problema |
|----|------|--------|---------------|----------|
| 24 | Recepciones Insumos | incoming | 1,432 | Origen desde Partners/Vendors |
| 177 | CONSUMO | internal | 365 | Destino a Virtual/Consumo-CentroCosto |
| 9 | Manufacturing | mrp_operation | 0 | No usado directamente |
| 165 | Consumo de Inventario | mrp_operation | 2 | Origen/Destino iguales |

## 2.5 Módulos Instalados Relevantes

- ✅ stock
- ✅ mrp
- ✅ purchase
- ✅ sale_stock
- ✅ stock_account (valoración automática activa)
- ✅ mrp_account

---

# 3. HALLAZGOS CON EVIDENCIA

## HALLAZGO 1: Stock Negativo en Partners/Vendors (CRÍTICO)

**Descripción**: La ubicación virtual `Partners/Vendors` (ID: 4) de tipo `supplier` tiene 733 quants con cantidad negativa totalizando **-20,235,331.65 unidades**.

**¿Por qué es crítico?**: Esta ubicación representa a los proveedores. NUNCA debería tener stock negativo. Un quant negativo aquí significa que se registraron salidas (entregas a cliente, consumos) de productos que nunca fueron recibidos formalmente.

**Evidencia**:
```
Ubicación: Partners/Vendors (usage: supplier)
Quants negativos: 733
Total cantidad negativa: -20,235,331.65

Ejemplos:
- Bandeja Verde 45x34: -1,329,332 unidades
- AR HB Conv. IQF en Bandeja: -1,321,760 unidades
- Bandejón IQF 60x40: -765,002 unidades
- BOLSA CREATIVE GOURMET BLUEBERRY: -477,600 unidades
```

**Causa probable**:
1. Recepciones de compra validadas sin procesar correctamente
2. Devoluciones a proveedor sin nota de crédito
3. Cancelaciones de recepciones después de movimientos internos

## HALLAZGO 2: Virtual Locations/Ubicación Procesos con Stock Negativo

**Descripción**: 847 quants negativos con total de **-8,098,888.22 unidades**.

**Evidencia**:
```
- MERMA PROCESO: -116,691.84 kg
- FB MK Conv. S/C PSP: -99,821 kg
- AR S/V ORG. S/C Calidad Jugo: -76,815.85 kg
- AR S/V Conv. S/C Calidad Jugo: -62,987.08 kg
- DESECHO VEGETAL: -51,330.23 kg
```

**Interpretación**: Los procesos de producción están "consumiendo" más producto del que entra a estas ubicaciones de tránsito. Esto indica:
- Órdenes de producción que consumen sin tener stock disponible
- Stock negativo permitido (configuración incorrecta)
- Falta de sincronización entre entrada y consumo

## HALLAZGO 3: Ajustes de Inventario Masivos por Usuario "Bodega Insumos"

**Evidencia**:
```
Usuario: Bodega Insumos
- Entradas: 10 movimientos, 172,311 unidades
- Salidas: 279 movimientos, 905,939 unidades
- Efecto neto: -733,628 unidades
```

**Interpretación**: Existe un usuario (posiblemente genérico) llamado "Bodega Insumos" que está ejecutando ajustes de inventario negativos masivos. Esto sugiere:
- Uso de ajustes como mecanismo de consumo manual
- Posible duplicidad: consumo por ajuste + consumo por producción
- Falta de trazabilidad (no hay documento origen)

## HALLAZGO 4: Consumos desde Múltiples Ubicaciones en Producción

**Evidencia** (23 de 30 producciones analizadas tienen este problema):
```
⚠️ WH/RF/MO/01062: [2.2] PROCESO PTT
   Consumo desde: {'RF/Stock/Inventario Real', 'RF/Insumos/Bodega Insumos'}

⚠️ WH/RF/MO/01059: [3] Proceso de Vaciado
   Consumo desde: {'Tránsito/Salida Túneles Estáticos', 'RF/Insumos/Bodega Insumos'}
```

**Interpretación**: Las órdenes de producción están configuradas para consumir simultáneamente desde ubicaciones de stock de producto (RF/Stock) Y ubicaciones de insumos (RF/Insumos). Esto es correcto conceptualmente, pero si además se hace un consumo manual adicional, se duplica.

## HALLAZGO 5: Movimientos Manuales Masivos sin Control

**Evidencia**:
```
Movimientos sin picking ni OP: 500+ (últimos analizados)
Movimientos sospechosos hacia ubicaciones virtuales/producción: 491

Usuarios con más movimientos manuales:
- FELIPE TOMÁS HORST SCHENCKE: 220 movimientos
- MARCELO JARAMILLO CADEGAN: 190 movimientos
- MIGUEL VALLADARES: 45 movimientos
- JOSÉ LUIS VIDAURRE WAEGER: 37 movimientos
```

**Patrones de flujo detectados**:
```
Virtual Locations/Inventory adjustment → RF/Stock/Camara -25°C PSP: 140 movs
Virtual Locations/Inventory adjustment → RF/Stock/Camara 0°C: 127 movs
RF/Stock/Camara 0°C → Virtual Locations/Inventory adjustment: 123 movs
```

## HALLAZGO 6: BOMs con Configuración Incorrecta

**Evidencia**:
```
3 BOMs con componentes con cantidad <= 0:
- [4-24] Proceso Retail-2024: Componente ETIQUETAS 10x15 BLANCA-2024 con qty <= 0
- [2] Proceso Congelado: Componente Mora Conv. En bandeja con qty <= 0
- [2] Proceso Congelado: Componente Mora Org. En bandeja con qty <= 0
```

---

# 4. PRODUCTOS CRÍTICOS CON STOCK NEGATIVO

## Top 20 Productos por Magnitud de Stock Negativo

| # | Producto | Stock Negativo | Ubicación Principal |
|---|----------|----------------|---------------------|
| 1 | [101222000] AR HB Org. IQF en Bandeja | -2,097,522 | VLK/Stock |
| 2 | [300002-24] AR S/V Conv. S/C Block Bins | -1,853,149 | RF/Stock/Camara 0°C pos lavado |
| 3 | [500007] Bandeja Verde 45x34 | -1,329,332 | Partners/Vendors |
| 4 | [101122000] AR HB Conv. IQF en Bandeja | -1,321,760 | Partners/Vendors |
| 5 | [300004-24] AR S/V Org. S/C Block Bins | -776,011 | RF/Stock/Camara 0°C pos lavado |
| 6 | [500008] Bandejón IQF 60x40 | -765,002 | Partners/Vendors |
| 7 | [500079] BOLSA CREATIVE GOURMET BLUEBERRY | -477,600 | Partners/Vendors |
| 8 | [500329] BOLSA CREATIVE GOURMET RASPBERRY | -453,600 | Partners/Vendors |
| 9 | [500007L] Bandeja Verde 45x34 Limpia | -420,092 | RF/Stock |
| 10 | [500008L] Bandejón IQF 60x40 Limpia | -383,949 | RF/Stock |

## Productos de Insumos con Stock Negativo (RF INSUMOS)

| Producto | Stock Negativo | Ubicación |
|----------|----------------|-----------|
| CAJA EXPORTACIÓN 47x24.5x24.2 | -93,776 | RF/Insumos/Bodega Insumos |
| BOLSA CREATIVE GOURMET BLUEBERRY | -212,893 (múltiples) | RF/Insumos/Bodega Insumos |
| BOLSA AZUL 73X58X0.060 | -58,610 | RF/Insumos/Bodega Insumos |
| BOLSA DP BLUEBERRIES ALDI | -371,066 | RF/Insumos |
| ETIQUETA 3x5 BLANCA | -71,220 | RF/Insumos |

---

# 5. MOVIMIENTOS SOSPECHOSOS O DUPLICADOS

## 5.1 Productos con Evidencia de Duplicidad

| Producto | Consumos MRP | Salidas Manuales | Total Entradas | Diagnóstico |
|----------|--------------|------------------|----------------|-------------|
| AR S/V Conv. S/C Block Bins-2024 | 3 | 14 | 149 | ⚠️ DUPLICIDAD |
| AR HB Conv. IQF en Bandeja | 331 | 1 | 458 | ⚠️ DUPLICIDAD MENOR |
| AR HB Org. IQF en Bandeja | 205 | 0 | 476 | Sin duplicidad |

## 5.2 Movimientos Sospechosos Detectados

**Total: 491 movimientos sospechosos**

Ejemplos representativos:
```
[170291] FB MK Conv. S/C PSP 12 kg
   VLK/Camara 2 -25°C → Virtual Locations/Inventory adjustment
   Qty: 840.0, User: MARCELO JARAMILLO CADEGAN
   
[168810] AR HB Conv. S/C PSP 13,61 kg
   RF/Stock/Inventario Real → Virtual Locations/Ubicación Procesos
   Qty: 1,483.49, User: DIEGO EUDALDO SAAVEDRA ALBARRACÍN
   
[168809] PROCESO PSP
   RF/Stock/Inventario Real → Virtual Locations/Ubicación Procesos
   Qty: 2,623.68, User: DIEGO EUDALDO SAAVEDRA ALBARRACÍN
```

---

# 6. USUARIOS Y OPERACIONES EJECUTADAS

## 6.1 Resumen de Actividad por Usuario

| Usuario | Total Movimientos | MRP | Picking | Manuales |
|---------|-------------------|-----|---------|----------|
| FELIPE TOMÁS HORST SCHENCKE | 220+ | - | - | 220 |
| MARCELO JARAMILLO CADEGAN | 190+ | - | - | 190 |
| MIGUEL VALLADARES | 45+ | - | - | 45 |
| JOSÉ LUIS VIDAURRE WAEGER | 37+ | - | - | 37 |
| Bodega Insumos (usuario genérico) | 289 | - | - | 289 |

## 6.2 Ajustes de Inventario por Usuario

| Usuario | Entradas | Qty Entrada | Salidas | Qty Salida | Neto |
|---------|----------|-------------|---------|------------|------|
| Bodega Insumos | 10 | 172,311 | 279 | 905,939 | **-733,628** |
| FELIPE TOMÁS HORST SCHENCKE | 241 | 75,705 | 160 | 57,012 | +18,692 |
| MARCELO JARAMILLO CADEGAN | 139 | 8,532,713 | 20 | 8,453,639 | +79,073 |
| DAMARIS VERÓNICA MONTECINOS | 61 | 108,058 | 0 | 0 | +108,058 |

## 6.3 Análisis por Tipo de Operación

**CONSUMO (ID: 177)**:
- Tipo: internal
- Origen: RF/Insumos
- Destino: Virtual Locations/Consumo-CentroCosto
- Pickings completados: 365
- **Este es el flujo de consumo manual desde bodega de insumos**

---

# 7. ANÁLISIS DE IMPACTO POR ESCENARIO

## 7.1 Escenario Actual (Sin Intervención)

| Área | Impacto | Severidad |
|------|---------|-----------|
| **Stock operativo** | Imposible determinar disponibilidad real | 🔴 CRÍTICO |
| **Planificación** | MRP genera demanda incorrecta | 🔴 CRÍTICO |
| **Compras** | Se compra de más o de menos | 🔴 CRÍTICO |
| **Valorización** | stock.valuation.layer inconsistente | 🔴 CRÍTICO |
| **Contabilidad** | Cuentas de inventario descuadradas | 🔴 CRÍTICO |
| **Trazabilidad** | Se pierde en movimientos manuales | 🟠 ALTO |
| **Reportes** | No confiables | 🟠 ALTO |

## 7.2 Si se Regulariza con Ajustes Masivos

| Área | Impacto | Severidad |
|------|---------|-----------|
| Stock operativo | Corrige stock actual | 🟢 POSITIVO |
| Planificación | Mejora inmediata | 🟢 POSITIVO |
| Compras | Normaliza | 🟢 POSITIVO |
| Valorización | Impacta costo promedio | 🟠 ALTO |
| Contabilidad | Requiere asiento de ajuste masivo | 🟠 ALTO |
| Trazabilidad | Se pierde aún más | 🔴 CRÍTICO |
| Reportes históricos | Quedan inconsistentes | 🟡 MEDIO |

## 7.3 Si se Corrige Historial (No Recomendado)

| Área | Impacto | Severidad |
|------|---------|-----------|
| Stock operativo | Corrección perfecta | 🟢 POSITIVO |
| Valorización | Requiere recálculo masivo | 🔴 CRÍTICO |
| Contabilidad | Requiere re-apertura períodos | 🔴 CRÍTICO |
| Tiempo | Semanas de trabajo | 🔴 CRÍTICO |
| Riesgo | Muy alto de introducir nuevos errores | 🔴 CRÍTICO |

## 7.4 Impacto sobre stock.valuation.layer

**Configuración detectada**: Valoración automática con costo promedio.

**Situación actual**:
- Existen capas de valoración con `remaining_qty` negativo
- El costo promedio está distorsionado
- Ejemplo: AR HB Org. IQF en Bandeja tiene capas con remaining_qty = -19,692.69

**Riesgo de corrección**:
- Ajustes de inventario generarán nuevas capas
- El costo promedio se recalculará
- Puede haber impacto en P&L si hay diferencia de valoración

---

# 8. PROPUESTA DE SOLUCIONES

## ALTERNATIVA A: Regularización mediante Ajustes de Inventario Controlados

### Descripción
Realizar un inventario físico completo y ajustar el stock de sistema al stock real mediante ajustes de inventario en Odoo.

### Pasos Concretos
1. Definir fecha de corte (ej: último día del mes)
2. Realizar inventario físico en todas las ubicaciones afectadas
3. Generar reporte de diferencias (stock sistema vs físico)
4. Crear ajustes de inventario en Odoo con una referencia común
5. Validar ajustes en una sola operación
6. Revisar impacto contable y registrar asiento de ajuste

### Ventajas
- ✅ Rápido de implementar (1-2 semanas)
- ✅ Stock corregido inmediatamente
- ✅ Método estándar de Odoo
- ✅ Trazabilidad de la corrección

### Desventajas
- ❌ Pierde trazabilidad histórica
- ❌ Impacto contable importante
- ❌ No corrige la causa raíz
- ❌ Puede generar desvíos en costo promedio

### Riesgos
- Asiento contable de alto monto
- Posibles preguntas de auditoría
- Si no se corrige el proceso, volverá a ocurrir

### Impacto Contable
- Ajustes positivos: Débito a Inventario, Crédito a Ajuste de Inventario
- Ajustes negativos: Débito a Gasto/Ajuste, Crédito a Inventario
- Estimación: Impacto en millones de pesos

### Complejidad
⭐⭐ Media

### Ventana de Corte Requerida
Sí, 2-3 días para conteo e ingreso

### Participación Requerida
- Bodega: Conteo físico
- Producción: Pausa o mínima actividad
- Contabilidad: Revisión asientos

---

## ALTERNATIVA B: Regularización Escalonada por Familia de Productos

### Descripción
Dividir la regularización por familias de productos (Insumos, Producto Terminado, Bandejas) y hacer ajustes progresivos.

### Pasos Concretos
1. Priorizar familia de INSUMOS (RF INSUMOS) - semana 1
2. Luego familia de BANDEJAS/ENVASES - semana 2
3. Finalmente PRODUCTO EN PROCESO - semana 3
4. Cada familia con su propio ciclo de conteo y ajuste

### Ventajas
- ✅ Menor disrupción operativa
- ✅ Permite validar proceso antes de escalar
- ✅ Más fácil de controlar

### Desventajas
- ❌ Toma más tiempo (3-4 semanas)
- ❌ Durante la transición hay inconsistencias
- ❌ Más complejo de coordinar

### Riesgos
- Cambios en stock durante el período de regularización
- Posible confusión operativa

### Complejidad
⭐⭐⭐ Alta

---

## ALTERNATIVA C: Congelamiento de Flujo Manual + Regularización

### Descripción
Primero eliminar la posibilidad de movimientos manuales incorrectos, luego regularizar.

### Pasos Concretos
1. Semana 1: Bloquear tipo de operación "CONSUMO" (ID: 177)
2. Semana 1: Configurar permisos para que solo MRP consuma
3. Semana 1: Capacitar a usuarios en nuevo flujo
4. Semana 2-3: Ejecutar regularización tipo A o B
5. Semana 4: Monitorear y ajustar

### Ventajas
- ✅ Evita que el problema siga creciendo
- ✅ Corrige causa raíz antes de regularizar
- ✅ Mayor probabilidad de éxito a largo plazo

### Desventajas
- ❌ Requiere cambio de proceso operativo
- ❌ Resistencia al cambio de usuarios
- ❌ Tiempo adicional de implementación

### Complejidad
⭐⭐⭐⭐ Alta

---

## ALTERNATIVA D: Solución Híbrida (RECOMENDADA)

### Descripción
Combinar las mejores prácticas de las alternativas anteriores con un enfoque pragmático.

### Pasos Concretos

**Fase Inmediata (Semana 1)**:
1. Crear nueva ubicación "AJUSTES_REGULARIZACIÓN_2026"
2. Documentar stock negativo actual con script
3. Bloquear temporalmente tipo operación "CONSUMO" (ID: 177)
4. Comunicar a toda la organización

**Fase Regularización RF INSUMOS (Semana 2)**:
1. Conteo físico de Bodega Insumos
2. Ajustar stock de insumos críticos
3. Validar con contabilidad

**Fase Regularización Productos (Semana 3-4)**:
1. Conteo por ubicación (Cámaras, Stock Real)
2. Ajustar productos con mayor desviación
3. Re-calcular costos si es necesario

**Fase Proceso Futuro (Semana 4-5)**:
1. Eliminar tipo operación CONSUMO manual
2. Configurar consumo automático desde MRP
3. Capacitar usuarios
4. Implementar controles

### Ventajas
- ✅ Aborda causa raíz + síntomas
- ✅ Escalonado y controlado
- ✅ Mantiene operación
- ✅ Permite aprendizaje

### Desventajas
- ❌ Requiere compromiso de la organización
- ❌ 4-5 semanas de implementación

### Complejidad
⭐⭐⭐ Media-Alta

---

## Matriz de Decisión

| Criterio (peso) | Alternativa A | Alternativa B | Alternativa C | Alternativa D |
|-----------------|---------------|---------------|---------------|---------------|
| Tiempo (20%) | 5 | 3 | 3 | 4 |
| Impacto operativo (20%) | 3 | 4 | 3 | 4 |
| Corrección causa raíz (25%) | 1 | 1 | 5 | 5 |
| Riesgo contable (15%) | 3 | 4 | 3 | 4 |
| Complejidad (10%) | 5 | 3 | 2 | 3 |
| Sostenibilidad (10%) | 2 | 2 | 5 | 5 |
| **TOTAL** | **2.85** | **2.65** | **3.55** | **4.25** |

**Recomendación: ALTERNATIVA D (Solución Híbrida)**

---

# 9. RECOMENDACIÓN FINAL

## Estrategia Principal: ALTERNATIVA D

### Justificación
1. Aborda tanto los síntomas (stock negativo) como la causa raíz (flujo incorrecto)
2. Permite operación continua con disrupciones controladas
3. Establece bases para sostenibilidad futura
4. Balance entre rapidez y completitud

### Estrategia de Contingencia
Si la Alternativa D no es viable por restricciones de tiempo o recursos:
- Ejecutar Alternativa A (ajustes masivos) como medida de emergencia
- Documentar deuda técnica para abordar causa raíz después

---

## Estrategia Específica para RF INSUMOS

### Diagnóstico Específico
- Stock negativo total: -938,657 unidades
- 46 quants negativos
- Consumos manuales masivos por usuario "Bodega Insumos"
- Tipo operación "CONSUMO" (ID: 177) genera salidas a ubicación virtual

### Plan de Acción RF INSUMOS

1. **Inmediato (Día 1-2)**:
   - Desactivar tipo operación "CONSUMO" (ID: 177)
   - Comunicar a jefa de bodega

2. **Conteo (Día 3-5)**:
   - Inventario físico de Bodega Insumos
   - Inventario físico de Bodega Químicos
   - Documentar en Excel

3. **Ajuste (Día 6-7)**:
   - Ingresar ajustes de inventario
   - Validar con código de referencia único
   - Revisión contabilidad

4. **Nuevo Flujo (Día 8+)**:
   - Insumos se consumen automáticamente desde OP
   - No hay consumo manual permitido
   - Transferencias internas para mover entre ubicaciones

---

## Estrategia para Evitar Reincidencia

### Controles Técnicos
1. **Eliminar** tipo operación "CONSUMO" manual (ID: 177)
2. **Restringir** creación de stock.move sin picking o producción
3. **Configurar** consumo automático en MRP
4. **Bloquear** ajustes de inventario a usuarios no autorizados

### Controles de Proceso
1. **Definir** flujo único de consumo: solo desde MRP
2. **Documentar** procedimientos de excepción
3. **Capacitar** a usuarios clave

### Controles de Monitoreo
1. **Reporte diario** de stocks negativos
2. **Alertas** cuando un producto llega a stock 0
3. **Auditoría semanal** de movimientos manuales

---

# 10. PLAN DE REGULARIZACIÓN PASO A PASO

## Semana 1: Preparación

| Día | Actividad | Responsable | Entregable |
|-----|-----------|-------------|------------|
| L | Reunión kick-off con gerencia | Consultor | Acta de compromiso |
| L | Ejecutar script de diagnóstico final | TI | Reporte línea base |
| M | Crear ubicación "AJUSTE_REG_2026" | TI | Ubicación en Odoo |
| M | Desactivar tipo op "CONSUMO" | TI | Configuración |
| X | Comunicación a usuarios | RRHH | Email/reunión |
| X | Capacitación flujo MRP | Consultor | Usuarios capacitados |
| J | Definir equipos de conteo | Bodega | Plan de conteo |
| V | Preparar formularios | Bodega | Plantillas Excel |

## Semana 2: Regularización RF INSUMOS

| Día | Actividad | Responsable | Entregable |
|-----|-----------|-------------|------------|
| L | Conteo Bodega Insumos (racks 1-2) | Equipo A | Planilla física |
| M | Conteo Bodega Insumos (racks 3-5) | Equipo A | Planilla física |
| X | Conteo Bodega Químicos | Equipo B | Planilla física |
| X | Consolidar conteos en Excel | Bodega | Excel maestro |
| J | Comparar con stock sistema | TI | Reporte diferencias |
| J | Validar diferencias críticas | Jefa Bodega | Aprobación |
| V | Ingresar ajustes lote 1 | TI | Ajustes validados |
| V | Revisión contable | Contador | OK contable |

## Semana 3: Regularización Productos (Cámaras)

| Día | Actividad | Responsable | Entregable |
|-----|-----------|-------------|------------|
| L | Conteo Cámara 0°C | Producción | Planilla física |
| M | Conteo Cámaras -25°C | Producción | Planilla física |
| X | Consolidar y comparar | TI | Reporte diferencias |
| J | Ingresar ajustes lote 2 | TI | Ajustes validados |
| V | Verificación cruzada | Contador | OK contable |

## Semana 4: Estabilización

| Día | Actividad | Responsable | Entregable |
|-----|-----------|-------------|------------|
| L | Conteo verificación aleatoria | Auditor | Muestreo OK |
| M | Ajustes finales si necesario | TI | Ajustes menores |
| X | Reporte final de regularización | Consultor | Informe ejecutivo |
| J | Implementar controles permanentes | TI | Reglas configuradas |
| V | Capacitación final usuarios | Consultor | Cierre |

---

# 11. FLUJO FUTURO CORRECTO

## 11.1 Flujo de Consumo de Insumos (Correcto)

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  COMPRA         │────▶│  BODEGA         │     │  PRODUCCIÓN     │
│  Orden Compra   │     │  INSUMOS        │     │  (MRP)          │
└─────────────────┘     │  RF/Insumos     │     └────────┬────────┘
                        └────────┬────────┘              │
                                 │                       │
                                 ▼                       │
                        ┌─────────────────┐              │
                        │  Orden          │◀─────────────┘
                        │  Fabricación    │   (Consumo automático
                        │  (OP)           │    al confirmar/producir)
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  COMPONENTES    │──▶ Virtual/Producción
                        │  CONSUMIDOS     │    (ubicación destino)
                        └─────────────────┘
```

## 11.2 Cuándo Usar Cada Tipo de Movimiento

### ✅ USAR: Transferencias Internas
- Mover producto entre ubicaciones del mismo almacén
- Ejemplo: de Cámara 0° a Cámara -25°
- Siempre con picking validado

### ✅ USAR: Consumo desde Fabricación (MRP)
- Todo consumo de componentes/insumos para producción
- Se ejecuta automáticamente al confirmar/producir OP
- Ubicación origen: configurada en OP o ruta

### ❌ NO USAR: Consumo Manual
- Prohibido crear movimientos sin picking ni OP
- El tipo operación "CONSUMO" (ID: 177) debe eliminarse
- Excepciones solo con aprobación de gerencia

### ⚠️ USAR CON CUIDADO: Ajustes de Inventario
- Solo para correcciones post-conteo físico
- Requiere aprobación de supervisor
- Siempre con referencia documental

## 11.3 Roles y Responsabilidades

### Bodega (Jefa de Bodega)
- Recibir insumos con picking validado
- NO ejecutar consumos manuales
- Informar faltantes/excesos
- Ejecutar transferencias internas si necesario

### Producción (Jefe de Producción)
- Crear órdenes de fabricación
- Verificar disponibilidad en OP
- Ejecutar producción (consumo automático)
- NO duplicar consumos manualmente

### TI/Sistema
- Mantener configuración de rutas
- Monitorear stocks negativos
- Generar reportes
- Gestionar permisos

## 11.4 Manejo de Situaciones Especiales

### Mermas
- Registrar mediante tipo operación "Scrap"
- Ubicación destino: Virtual Locations/Scrap
- Requiere motivo y aprobación

### Devoluciones de Producción
- Usar tipo operación de devolución interna
- Retorna componentes a ubicación origen
- Actualiza OP relacionada

### Sobrantes
- Si sobra material post-producción
- Opción 1: Ajustar BOM si es recurrente
- Opción 2: Transferir sobrante a ubicación correspondiente

### Transferencias entre Almacenes (RF ↔ VLK)
- Usar picking de transferencia entre almacenes
- Ubicación tránsito intermedia
- Registro completo de trazabilidad

## 11.5 Control de RF INSUMOS Específico

```
ENTRADA (único camino válido):
  Orden de Compra → Recepción → RF/Insumos/Bodega Insumos

SALIDA (único camino válido):
  Orden Fabricación (consume automático) → Virtual/Producción

MOVIMIENTOS INTERNOS (permitido):
  Bodega Insumos → Bodega Químicos (con transferencia)
  Rack A → Rack B (con transferencia)

PROHIBIDO:
  Cualquier salida directa a ubicación virtual
  Ajustes de salida sin aprobación
  Movimientos sin documento origen
```

---

# 12. MEJORAS EN PERMISOS Y PROCESOS

## 12.1 Cambios en Permisos de Usuario

### Grupo "Bodega Insumos"
```
QUITAR:
- stock.group_stock_user → stock.group_stock_internal_user
- Acceso a Ajustes de Inventario

MANTENER:
- Ver stock en ubicaciones
- Crear transferencias internas
- Validar recepciones

NUEVO:
- Solo lectura en reportes de inventario
```

### Grupo "Operarios Producción"
```
QUITAR:
- Crear stock.move directamente
- Ajustes de inventario

MANTENER:
- Crear/confirmar órdenes de fabricación
- Ver BOMs
- Registrar producción a través de OP

NUEVO:
- Puede marcar unidades producidas
- NO puede modificar componentes consumidos manualmente
```

### Grupo "Supervisores"
```
MANTENER:
- Todos los accesos actuales

NUEVO:
- Aprobar ajustes de inventario
- Ver reportes de movimientos manuales
- Configurar excepciones
```

## 12.2 Configuraciones en Odoo

### 1. Desactivar tipo operación CONSUMO
```python
# Ejecutar en shell de Odoo
picking_type = env['stock.picking.type'].browse(177)
picking_type.active = False
```

### 2. Configurar consumo automático en MRP
```
Configuración > Fabricación > 
  ☑ Consumir componentes automáticamente
  
En cada BOM:
  Tipo de BOM: Fabricar este producto
  Consumo: Flexible (o Estricto según necesidad)
```

### 3. Reglas de reabastecimiento
```
Para cada producto de insumos críticos:
- Configurar regla de abastecimiento
- Punto de pedido mínimo
- Cantidad a pedir sugerida
- Proveedor preferido
```

### 4. Alertas de stock negativo
```python
# Crear acción automatizada
Modelo: stock.quant
Condición: quantity < 0
Acción: Enviar email a supervisores
```

## 12.3 Validaciones Automáticas Recomendadas

### Validación 1: Bloquear Movimientos Sin Origen
```python
# Herencia en stock.move
@api.constrains('picking_id', 'raw_material_production_id', 'production_id')
def _check_origin(self):
    for move in self:
        if move.state == 'done' and not move.picking_id \
           and not move.raw_material_production_id \
           and not move.production_id \
           and move.location_id.usage == 'internal':
            raise ValidationError("Movimientos sin documento origen no permitidos")
```

### Validación 2: Alertar Stock Negativo
```python
# Cron job diario
def _check_negative_stock(self):
    negative = self.env['stock.quant'].search([
        ('quantity', '<', 0),
        ('location_id.usage', '=', 'internal')
    ])
    if negative:
        # Enviar reporte por email
        self._send_negative_stock_report(negative)
```

### Validación 3: Aprobar Ajustes Grandes
```xml
<!-- Workflow de aprobación para ajustes > 1000 unidades -->
<record id="stock_inventory_adjustment_approval" model="ir.rule">
    <!-- Configurar regla de aprobación -->
</record>
```

---

# 13. SCRIPTS DE VALIDACIÓN

## 13.1 Script de Diagnóstico Rápido

Este script ya fue creado y ejecutado: `audit_odoo_insumos.py`

Uso:
```bash
python audit_odoo_insumos.py
```

## 13.2 Script para Monitoreo Diario

```python
"""
Monitoreo diario de stocks negativos y movimientos sospechosos
Ejecutar diariamente como cron
"""

import xmlrpc.client
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "tu_usuario"
PASSWORD = "tu_password"

def check_negative_stock():
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Buscar quants negativos
    negative = models.execute_kw(
        DB, uid, PASSWORD,
        'stock.quant', 'search_read',
        [[('quantity', '<', 0), ('location_id.usage', '=', 'internal')]],
        {'fields': ['product_id', 'location_id', 'quantity']}
    )
    
    if negative:
        msg = f"ALERTA: {len(negative)} quants negativos detectados\n\n"
        for q in negative[:20]:
            msg += f"- {q['product_id'][1]}: {q['quantity']} en {q['location_id'][1]}\n"
        
        # Enviar alerta
        send_email("Alerta Stock Negativo", msg)
    
    return negative

def check_manual_moves():
    # Similar al diagnóstico, buscar movimientos sin origen
    pass

if __name__ == "__main__":
    check_negative_stock()
```

## 13.3 Script de Pre-Regularización

```python
"""
Genera reporte previo a regularización
Exporta todos los productos con stock negativo y su detalle
"""

import xmlrpc.client
import csv
from datetime import datetime

def generate_pre_regularization_report():
    # ... conexión ...
    
    # Exportar a CSV
    with open(f'pre_reg_{datetime.now().strftime("%Y%m%d")}.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Producto', 'Código', 'Ubicación', 'Stock Sistema', 'Stock Físico', 'Diferencia'])
        
        # Obtener datos
        negative_quants = # ... query ...
        
        for q in negative_quants:
            writer.writerow([
                q['product_id'][1],
                # ... más campos ...
                '',  # Stock físico (a llenar manualmente)
                ''   # Diferencia
            ])
```

## 13.4 Script Post-Regularización

```python
"""
Valida que la regularización se ejecutó correctamente
Compara línea base con estado actual
"""

import json

def validate_regularization(baseline_file, current_file):
    with open(baseline_file) as f:
        baseline = json.load(f)
    
    with open(current_file) as f:
        current = json.load(f)
    
    # Comparar productos con stock negativo
    baseline_neg = {p['product_id'] for p in baseline['products_negative_stock']}
    current_neg = {p['product_id'] for p in current['products_negative_stock']}
    
    fixed = baseline_neg - current_neg
    still_negative = baseline_neg & current_neg
    new_negative = current_neg - baseline_neg
    
    print(f"Productos corregidos: {len(fixed)}")
    print(f"Aún negativos: {len(still_negative)}")
    print(f"Nuevos negativos: {len(new_negative)}")
    
    return fixed, still_negative, new_negative
```

---

# ANEXOS

## Anexo A: Archivos Generados por la Auditoría

1. `audit_insumos_results.json` - Resultados completos del primer análisis
2. `audit_deep_results.json` - Resultados del análisis profundo
3. `audit_odoo_insumos.py` - Script de auditoría inicial
4. `audit_odoo_deep_analysis.py` - Script de análisis profundo

## Anexo B: Consultas SQL Útiles (Para Acceso Directo a BD)

```sql
-- Productos con stock negativo por ubicación
SELECT pp.default_code, pt.name, sl.complete_name, sq.quantity
FROM stock_quant sq
JOIN product_product pp ON sq.product_id = pp.id
JOIN product_template pt ON pp.product_tmpl_id = pt.id
JOIN stock_location sl ON sq.location_id = sl.id
WHERE sq.quantity < 0 AND sl.usage = 'internal'
ORDER BY sq.quantity;

-- Movimientos manuales (sin picking ni producción)
SELECT sm.id, sm.name, pp.default_code, sm.quantity_done, 
       sl_src.complete_name as origen, sl_dest.complete_name as destino,
       ru.login as usuario, sm.date
FROM stock_move sm
JOIN product_product pp ON sm.product_id = pp.id
JOIN stock_location sl_src ON sm.location_id = sl_src.id
JOIN stock_location sl_dest ON sm.location_dest_id = sl_dest.id
LEFT JOIN res_users ru ON sm.create_uid = ru.id
WHERE sm.state = 'done'
  AND sm.picking_id IS NULL
  AND sm.raw_material_production_id IS NULL
  AND sm.production_id IS NULL
ORDER BY sm.date DESC
LIMIT 100;
```

## Anexo C: Contactos Clave

| Rol | Nombre | Responsabilidad en Regularización |
|-----|--------|-----------------------------------|
| Jefa Bodega | [Por definir] | Conteo físico, validación diferencias |
| Jefe Producción | [Por definir] | Pausa operativa, validación BOM |
| Contador | [Por definir] | Revisión asientos, cierre contable |
| TI | [Por definir] | Configuración Odoo, scripts |
| Consultor | [Por definir] | Coordinación, reportes |

---

**Documento preparado por**: Consultor Odoo
**Fecha**: 10 de Marzo de 2026
**Versión**: 1.0
