# 📦 Trazabilidad por Pallets - Guía de Uso

## 🎯 ¿Qué hace este módulo?

El módulo de **Trazabilidad por Pallets** permite rastrear uno o varios pallets desde el producto terminado hasta el productor original, mostrando:

- ✅ Todas las etapas de producción (Packing → Congelado → Vaciado)
- ✅ Los lotes intermedios de cada proceso
- ✅ Las órdenes de manufactura (MO) de cada etapa
- ✅ Los kilos consumidos en cada paso
- ✅ El rendimiento total (kg PT / kg MP)
- ✅ El productor original que entregó la materia prima

---

## 📝 Cómo Usar

### **1. Acceder al Módulo**
- Navegar a: **Dashboards → 🔍 Rendimiento**
- Seleccionar el tab: **📦 Trazabilidad por Pallets**

---

### **2. Ingresar Pallets**

Tienes 2 opciones:

#### **Opción A: Ingresar uno por uno**
1. Escribe el nombre del pallet (ej: `PALLET-RF-2024-0156`)
2. Haz clic en **"➕ Agregar"**
3. Repite para agregar más pallets
4. Puedes eliminar pallets con el botón 🗑️

#### **Opción B: Pegar lista múltiple**
1. Selecciona **"📋 Pegar lista"**
2. Pega los nombres de pallets separados por:
   - Comas: `PALLET-001, PALLET-002, PALLET-003`
   - Líneas nuevas:
     ```
     PALLET-001
     PALLET-002
     PALLET-003
     ```

---

### **3. Rastrear**
- Haz clic en **"🔍 Rastrear Trazabilidad"**
- Espera a que el sistema busque la información en Odoo
- Los resultados aparecerán automáticamente

---

## 📊 Interpretando los Resultados

### **KPIs del Pallet**
Cada pallet muestra:
- **Kg PT**: Kilogramos de producto terminado
- **Kg MP Total**: Total de kilogramos de materia prima utilizada
- **Rendimiento**: % de aprovechamiento (kg PT / kg MP × 100)
- **Merma**: Kilogramos perdidos en el proceso

### **Información del Pallet**
- **Lote PT**: Número de lote del producto terminado
- **Total Procesos**: Número de etapas de producción
- **Productores Origen**: Lista de proveedores que entregaron la materia prima

### **Cadena de Trazabilidad**
Se muestra nivel por nivel:

#### **PROCESO** 🏭
- **Sala**: Dónde se realizó el proceso (ej: "Línea Retail", "Sala 3", "Túnel Estático")
- **MO**: Orden de Manufactura (ej: "MO/PACK/2024/0892")
- **Lote**: Lote generado en este proceso
- **Fecha**: Cuándo se realizó
- **Total consumido**: Kg de materia prima/intermedia usada
- **Consumió**: Lista de lotes que se usaron (con cantidades)

#### **MATERIA PRIMA** 🌾
- **Lote MP**: Número de lote de la materia prima original
- **Producto**: Descripción del producto (ej: "Frambuesa Fresca Orgánica")
- **Productor**: Nombre del proveedor/agricultor
- **Fecha recepción**: Cuándo llegó al almacén

---

## 🔍 Ejemplo Práctico

### **Entrada**
```
PALLET-RF-2024-0156
```

### **Resultado**
```
✅ PALLET-RF-2024-0156 - Frambuesa IQF A - Retail 1kg

KPIs:
- Kg PT: 500 kg
- Kg MP Total: 1,000 kg
- Rendimiento: 50%
- Merma: 500 kg

Lote PT: LOTE-PT-2024-0892
Total Procesos: 3

👨‍🌾 Productores Origen:
- Agrícola San José S.A.

CADENA DE TRAZABILIDAD:

🏭 PROCESO - Nivel 0
- Sala: Línea Retail
- MO: MO/PACK/2024/0892
- Lote: LOTE-PT-2024-0892
- Fecha: 2024-12-15
- Total consumido: 520 kg
  📥 Consumió:
    - LOTE-CONG-2024-0445: 520 kg ([1.12001] Frambuesa IQF Proceso Congelado)

🏭 PROCESO - Nivel 1
- Sala: Túnel Estático
- MO: MO/TUNEL/2024/0156
- Lote: LOTE-CONG-2024-0445
- Fecha: 2024-12-14
- Total consumido: 800 kg
  📥 Consumió:
    - LOTE-VAC-2024-0223: 800 kg ([3] Frambuesa Proceso Vaciado)

🏭 PROCESO - Nivel 2
- Sala: Sala 3
- MO: MO/SALA3/2024/0223
- Lote: LOTE-VAC-2024-0223
- Fecha: 2024-12-14
- Total consumido: 1,000 kg
  📥 Consumió:
    - MP-2024-1892: 1,000 kg ([3000012] Frambuesa Fresca Orgánica)

🌾 MATERIA PRIMA - Nivel 3 (ORIGEN)
- Lote MP: MP-2024-1892
- Producto: [3000012] Frambuesa Fresca Orgánica
- 👨‍🌾 Productor: Agrícola San José S.A.
- Fecha recepción: 2024-12-10
```

---

## ✅ Casos de Uso

### **1. Reclamo de Cliente**
**Situación**: Cliente reporta problema en PALLET-001

**Acción**:
1. Rastrear `PALLET-001`
2. Identificar al productor original
3. Contactar al proveedor para investigar
4. Revisar si otros pallets del mismo lote MP tienen problemas

---

### **2. Auditoría de Calidad**
**Situación**: Necesitas documentar el origen de pallets para certificación

**Acción**:
1. Ingresar lista de pallets a certificar
2. Rastrear trazabilidad completa
3. Exportar resultados (captura de pantalla)
4. Adjuntar a documentación de auditoría

---

### **3. Análisis de Rendimiento**
**Situación**: Quieres saber por qué un pallet tiene bajo rendimiento

**Acción**:
1. Rastrear el pallet
2. Ver el rendimiento de cada etapa:
   - Vaciado: 80% (normal)
   - Congelado: 100% (bueno)
   - Packing: 96% (normal)
3. Identificar si hay oportunidad de mejora

---

### **4. Múltiples Productores**
**Situación**: Un pallet podría tener fruta de varios proveedores

**Resultado**:
```
👨‍🌾 Productores Origen:
- Agrícola San José S.A. (60%, 600 kg)
- Cooperativa Los Andes (40%, 400 kg)
```

---

## 🔧 Solución de Problemas

### **Error: "Pallet no encontrado"**
**Causas posibles**:
- Nombre de pallet incorrecto (verifica mayúsculas/minúsculas)
- Pallet no existe en Odoo
- Pallet aún no tiene movimientos registrados

**Solución**:
- Verifica el nombre exacto en Odoo
- Confirma que el pallet tiene lote asignado

---

### **Error: "No se encontraron movimientos"**
**Causa**: El pallet existe pero no tiene `result_package_id` asociado en movimientos

**Solución**:
- Contactar a TI para revisar configuración en Odoo
- Verificar que el pallet se creó correctamente

---

### **Resultados vacíos**
**Causa**: El lote PT no tiene `production_id` (no pasó por manufactura)

**Solución**:
- Verificar si el producto fue comprado en lugar de producido
- Revisar que las órdenes de manufactura estén confirmadas

---

## 📚 Información Técnica

### **Modelos de Odoo Consultados**
- `stock.quant.package` - Pallets físicos
- `stock.lot` - Lotes de productos
- `stock.move.line` - Movimientos detallados
- `stock.move` - Movimientos generales
- `mrp.production` - Órdenes de manufactura
- `stock.picking` - Recepciones/Entregas
- `res.partner` - Proveedores/Clientes

### **Tiempo Estimado**
- 1 pallet: ~3-5 segundos
- 5 pallets: ~15-20 segundos
- 10+ pallets: ~30-45 segundos

### **Límites**
- Máximo recomendado: 20 pallets simultáneos
- Si necesitas más, divide en grupos

---

## 💡 Consejos y Buenas Prácticas

1. **Nombrar pallets consistentemente**
   - Usa prefijos claros: `PALLET-RF-` (frambuesa), `PALLET-AR-` (arándano)
   - Incluye año: `PALLET-RF-2024-XXXX`

2. **Revisar regularmente**
   - Haz pruebas semanales para verificar que la trazabilidad funciona
   - Identifica gaps en la cadena antes de que sean un problema

3. **Documentar hallazgos**
   - Captura pantallas de resultados importantes
   - Mantén registro de pallets problemáticos

4. **Combinar con otros reportes**
   - Usa los datos de rendimiento para mejorar procesos
   - Compara con reportes de calidad

---

## 🚀 Actualizaciones Futuras (Roadmap)

- [ ] Exportar resultados a Excel/PDF
- [ ] Gráfico visual de la cadena (árbol)
- [ ] Búsqueda por rango de fechas
- [ ] Filtro por productor
- [ ] Alertas automáticas de bajo rendimiento

---

**📅 Última actualización**: 07 de Enero 2026  
**👨‍💻 Soporte**: Equipo de TI - Rio Futuro
