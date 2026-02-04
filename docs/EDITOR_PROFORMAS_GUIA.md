# 🎯 Guía de Uso - Editor de Proformas con Datos Faltantes

## 📋 Problema que Resuelve

Muchas OCs antiguas no tienen datos completos en el sistema de logística (rutas, kms, kilos, tipo de camión). El nuevo **Editor Completo** permite:

✅ **Detectar automáticamente** OCs con datos faltantes  
✅ **Editar en tiempo real** todos los campos necesarios  
✅ **Vista previa** de cómo quedará el PDF  
✅ **Validación** antes de generar/enviar  

---

## 🚀 Cómo Usar el Sistema

### 1️⃣ Detección Automática

Al cargar OCs, el sistema detecta automáticamente cuáles tienen datos incompletos:

```
⚠️ Se detectaron 5 OCs con datos incompletos

🔍 Ver detalles de 5 OCs con datos faltantes
  • PO00123 (TRANSPORTES RODRIGUEZ): Faltan datos de Ruta, Kms, Kilos
  • PO00145 (TRANSPORTES PEREZ): Faltan datos de Tipo Camión
  • PO00167 (TRANSPORTES GOMEZ): Faltan datos de Kms, Costo
```

**Campos que se validan:**
- ✓ Ruta (no puede estar vacía o "Sin ruta")
- ✓ Kilómetros (no puede ser 0)
- ✓ Kilos (no puede ser 0)
- ✓ Costo (no puede ser 0)
- ✓ Tipo de Camión (no puede ser "N/A")

---

### 2️⃣ Dos Modos de Trabajo

#### Modo: ✓ Selección Rápida
**Cuándo usarlo**: Cuando todas las OCs tienen datos completos

- Solo puedes seleccionar OCs (checkbox)
- Todos los demás campos están bloqueados
- Rápido y simple para casos normales

#### Modo: ✏️ Editor Completo
**Cuándo usarlo**: Cuando hay datos faltantes que necesitas completar

- Columna de **Estado** muestra ⚠️ Incompleto o ✅ Completo
- Puedes **editar** todos estos campos:
  - Ruta (texto libre)
  - Kms (número)
  - Kilos (número decimal)
  - Costo (número)
  - Tipo Camión (dropdown con opciones)
- Cálculo automático de $/km
- Botón para restaurar datos originales

---

### 3️⃣ Editar Datos Paso a Paso

1. **Identifica OCs con problemas**
   - Busca filas con Estado: ⚠️ Incompleto
   - O expande "Ver detalles de OCs con datos faltantes"

2. **Edita los campos necesarios**
   - Click en la celda que quieres editar
   - Ingresa el valor correcto
   - Para "Tipo Camión": selecciona del dropdown
     - 🚚 Camión 8 Ton
     - 🚛 Camión 12-14 Ton
     - 🚛 Camión 18 Ton
     - 🚛 Camión 24 Ton

3. **Marca las OCs a incluir**
   - Click en checkbox "☑️ Incluir"
   - Solo las marcadas se incluirán en la proforma

4. **Verifica el estado**
   - Mensaje inferior muestra:
     - ⚠️ Aún quedan X OCs incompletas (si faltan datos)
     - ✅ Todas las OCs tienen datos completos (si está OK)

---

### 4️⃣ Vista Previa del PDF

Antes de generar, usa el expander **👁️ Vista Previa**:

```
👁️ Vista Previa - Cómo se verá en el PDF

🚛 TRANSPORTES RODRIGUEZ LIMITADA
3 OCs | 1,380 km | 39,500.0 kg | $690,000

┌────────┬────────────┬─────────────────┬──────┬─────────┬──────────┬───────┬────────────┐
│ OC     │ Fecha      │ Ruta            │ Kms  │ Kilos   │ Costo    │ $/km  │ Tipo       │
├────────┼────────────┼─────────────────┼──────┼─────────┼──────────┼───────┼────────────┤
│ PO00123│ 2026-01-15 │ San José - LG   │ 450  │ 12500.0 │ $225,000 │ $500  │ 🚛 12-14 T │
│ PO00145│ 2026-01-20 │ Temuco - LG     │ 680  │ 18000.0 │ $340,000 │ $500  │ 🚛 12-14 T │
│ PO00167│ 2026-01-28 │ Curicó - LG     │ 250  │  9000.0 │ $125,000 │ $500  │ 🚚 8 Ton   │
└────────┴────────────┴─────────────────┴──────┴─────────┴──────────┴───────┴────────────┘
```

**Verifica**:
- ✓ Todos los datos están presentes
- ✓ Los números son correctos
- ✓ Las rutas tienen sentido
- ✓ Los totales cuadran

---

### 5️⃣ Validación Antes de Enviar

Si intentas generar con datos incompletos:

```
❌ 2 OCs seleccionadas tienen datos incompletos. 
   Ve al Editor Completo para corregirlas.

   Ver OCs con problemas
   • PO00145: Faltan Kms, Tipo Camión
   • PO00167: Faltan Ruta
```

**Advertencia final**:
```
⚠️ ADVERTENCIA: Algunas OCs tienen datos incompletos. 
   El PDF se generará con los datos disponibles, 
   pero puede verse incompleto.
```

Puedes proceder de todas formas, pero el documento tendrá valores en 0 o "Sin ruta".

---

## 💡 Casos de Uso Comunes

### Caso 1: OC sin ruta asignada
```
Problema: Ruta = "Sin ruta"
Solución:
1. Ve al Editor Completo
2. Click en columna "Ruta"
3. Escribe: "San José - La Granja"
4. Enter para confirmar
```

### Caso 2: OC sin kilómetros ni costo
```
Problema: Kms = 0, Costo = 0
Solución:
1. Busca en registros físicos/emails los datos reales
2. En Editor Completo, ingresa:
   - Kms: 450
   - Costo: 225000
3. El $/km se calcula automáticamente: $500
```

### Caso 3: OC sin tipo de camión
```
Problema: Tipo Camión = "N/A"
Solución:
1. Pregunta al transportista qué tipo de camión usó
2. En columna "Tipo Camión", selecciona del dropdown
3. Por ejemplo: 🚛 Camión 12-14 Ton
```

### Caso 4: Necesito editar varias OCs
```
Flujo eficiente:
1. Abre "Ver detalles de OCs con datos faltantes"
2. Anota qué falta en cada una
3. Ve preparando los datos (kms, rutas, costos)
4. Edita todas en secuencia en el Editor Completo
5. Verifica estado: ✅ Todas las OCs tienen datos completos
6. Revisa Vista Previa
7. Genera y envía
```

---

## 🎨 Estados Visuales

| Icono/Color | Significado |
|-------------|-------------|
| ⚠️ Incompleto | OC tiene datos faltantes |
| ✅ Completo | OC tiene todos los datos |
| 🔄 Restaurar | Volver a datos originales |
| 👁️ Vista Previa | Ver cómo quedará el PDF |
| ☑️ Incluir | Checkbox de selección |

---

## 🔧 Funciones Especiales

### Restaurar Datos Originales
Si editaste algo por error:
1. Click en "🔄 Restaurar datos originales"
2. Vuelve a los datos de Odoo/Logística
3. Todas las ediciones se pierden

### Cálculo Automático $/km
```
Fórmula: $/km = Costo Total / Kilómetros
Ejemplo: $225,000 / 450 km = $500/km
```
Se actualiza automáticamente al editar Costo o Kms.

---

## 📊 Ejemplo Completo

**Situación inicial**:
```
OC: PO00123
Transportista: TRANSPORTES RODRIGUEZ LTDA
Fecha: 2026-01-15
Ruta: Sin ruta ❌
Kms: 0 ❌
Kilos: 0 ❌
Costo: 225000 ✅
Tipo Camión: N/A ❌
```

**Pasos de corrección**:
1. Abrir Editor Completo
2. Editar campos:
   - Ruta: "San José - La Granja"
   - Kms: 450
   - Kilos: 12500
   - Tipo Camión: "🚛 Camión 12-14 Ton"
3. $/km se calcula solo: $500

**Resultado final**:
```
OC: PO00123
Transportista: TRANSPORTES RODRIGUEZ LTDA
Fecha: 2026-01-15
Ruta: San José - La Granja ✅
Kms: 450 ✅
Kilos: 12500 ✅
Costo: 225000 ✅
Tipo Camión: 🚛 Camión 12-14 Ton ✅
$/km: $500 (auto)
Estado: ✅ Completo
```

---

## ⚡ Tips y Mejores Prácticas

1. **Antes de empezar**: Ten a mano los datos que necesitas (guías de despacho, emails, registros)

2. **Ordena por estado**: Las OCs incompletas se destacan visualmente

3. **Edita de a poco**: No intentes corregir 20 OCs de golpe, ve de a 2-3

4. **Usa Vista Previa**: Siempre revisa cómo quedará antes de enviar

5. **Guarda capturas**: Si completas muchos datos, toma screenshot por si acaso

6. **Tipos de camión estándar**:
   - 8 Ton: Viajes cortos, carga ligera
   - 12-14 Ton: Más común para frutas
   - 18-24 Ton: Cargas pesadas, larga distancia

7. **Costos típicos**: 
   - Verifica que el $/km sea razonable ($400-$600/km es normal)
   - Si sale $50/km o $5000/km, revisa los datos

---

## 🆘 Troubleshooting

**P: No puedo editar algunos campos**
R: Estás en "Selección Rápida". Cambia a "Editor Completo"

**P: Edité un campo pero no se guardó**
R: Presiona Enter o click fuera de la celda para confirmar

**P: ¿Se guardan las ediciones en Odoo?**
R: NO. Las ediciones son temporales, solo para esta proforma. Los datos originales en Odoo no cambian.

**P: Quiero volver atrás con mis ediciones**
R: Click en "🔄 Restaurar datos originales"

**P: ¿Puedo editar la fecha o el transportista?**
R: No, esos campos son de solo lectura porque vienen de Odoo

**P: El PDF se ve raro con mis ediciones**
R: Usa "Vista Previa" antes de generar para verificar

---

**🎯 Con este sistema puedes generar proformas profesionales incluso con datos históricos incompletos**

---

*Última actualización: 02/02/2026*
