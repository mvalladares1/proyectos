# 🍓 TRAZABILIDAD EN ODOO: EXPLICACIÓN SIMPLE

## 📖 LA HISTORIA DE UN PALLET DE FRAMBUESA

Imagina que eres un detective y necesitas descubrir de dónde vino exactamente un pallet de frambuesa congelada que le vendiste a un cliente.

---

## 🎬 EL VIAJE DE LA FRAMBUESA (De atrás hacia adelante)

### **ACTO 1: LA VENTA** 🚚
**Lo que pasó:**
- Un cliente (Camerican) te compró 500 kg de frambuesa IQF en cajas retail
- Le enviaste el pallet **"PALLET-RF-2024-0156"**
- Fecha: 22 de diciembre

**¿Dónde está registrado en Odoo?**
- En la **orden de venta** (como cuando vendes algo en MercadoLibre)
- En el **albarán de entrega** (el papelito que dice "entregado")
- En el **pallet físico** que el camión se llevó

---

### **ACTO 2: EL EMPAQUE (PACKING)** 📦
**Lo que pasó:**
- El 15 de diciembre, en la Línea Retail, se empacó la frambuesa en cajitas de 1 kg
- Se generó el pallet con 500 cajas
- Se usaron 520 kg de frambuesa congelada (porque hay un poco de merma al empacar)

**¿Dónde está registrado?**
- En una **Orden de Manufactura** llamada "MO/PACK/2024/0892"
- Esta orden dice: "Usé 520 kg de frambuesa congelada y produje 500 kg de frambuesa empacada"

**La conexión:**
- El pallet que se vendió → tiene un "lote" (como un número de serie) → ese lote fue creado por esta orden de empaque

---

### **ACTO 3: EL CONGELADO** ❄️
**Lo que pasó:**
- El 14 de diciembre (un día antes), se metió frambuesa al túnel de congelación
- Entraron 800 kg de frambuesa procesada → salieron 800 kg de frambuesa congelada
- De esos 800 kg, se usaron 520 kg para el empaque del día siguiente

**¿Dónde está registrado?**
- En otra **Orden de Manufactura**: "MO/TUNEL/2024/0156"
- Esta orden dice: "Recibí 800 kg de fruta procesada y la congelé"

**La conexión:**
- La frambuesa congelada que se usó en el empaque → tiene su propio "lote" → ese lote fue creado por la orden de congelado

---

### **ACTO 4: EL VACIADO (PROCESO)** 🏭
**Lo que pasó:**
- El 14 de diciembre (mismo día, pero horas antes), en la Sala 3, se procesó frambuesa fresca
- Entraron 1000 kg de frambuesa fresca → salieron 800 kg de frambuesa procesada
- Se perdieron 200 kg por descarte, hojas, ramitas, etc.

**¿Dónde está registrado?**
- En otra **Orden de Manufactura**: "MO/SALA3/2024/0223"
- Esta orden dice: "Procesé 1000 kg de frambuesa fresca y obtuve 800 kg limpia"

**La conexión:**
- La frambuesa procesada que se congeló → tiene su "lote" → ese lote fue creado por la orden de vaciado

---

### **ACTO 5: LA RECEPCIÓN (MATERIA PRIMA)** 🚛
**Lo que pasó:**
- El 10 de diciembre llegó un camión con frambuesa fresca del campo
- El productor **"Agrícola San José S.A."** entregó 1000 kg
- Se registró todo: fecha, hora, peso, quién entregó

**¿Dónde está registrado?**
- En un **albarán de entrada** llamado "WH/IN/2024/0445"
- Este dice: "Recibimos 1000 kg del proveedor Agrícola San José"
- Se le asignó un "lote" a esa fruta: "MP-2024-1892"

**La conexión:**
- La frambuesa fresca que se procesó → tiene su "lote" → ese lote está vinculado al camión que llegó del productor

---

## 🔗 CÓMO ODOO CONECTA TODO

### **Imagina que cada cosa tiene un "número de serie":**

1. **El Pallet** tiene un código QR → "PALLET-RF-2024-0156"
2. Ese pallet contiene **cajas** con un lote → "LOTE-PT-2024-0892"
3. Ese lote fue creado por una **orden de empaque** → "MO/PACK/2024/0892"
4. Esa orden consumió **frambuesa congelada** con lote → "LOTE-CONG-2024-0445"
5. Ese lote congelado fue creado por una **orden de congelado** → "MO/TUNEL/2024/0156"
6. Esa orden consumió **frambuesa procesada** con lote → "LOTE-VAC-2024-0223"
7. Ese lote procesado fue creado por una **orden de vaciado** → "MO/SALA3/2024/0223"
8. Esa orden consumió **frambuesa fresca** con lote → "MP-2024-1892"
9. Ese lote de MP fue recibido del **productor** → "Agrícola San José S.A."

**Es como una cadena de WhatsApp:** cada mensaje referencia al anterior con "responder a..."

---

## 🎯 EL DETECTIVE EN ACCIÓN

**Pregunta:** ¿De qué productor vino el PALLET-RF-2024-0156?

**El detective hace esto (en Odoo):**

### Paso 1: Buscar el pallet
*"A ver, ¿dónde está este pallet?"*
- Busca en la base de datos: "PALLET-RF-2024-0156"
- Encuentra que tiene el lote "LOTE-PT-2024-0892"

### Paso 2: Buscar cuándo se creó ese lote
*"¿Cuándo se hizo este lote?"*
- Busca la primera vez que apareció ese lote
- Descubre que fue el 15/12 en la orden "MO/PACK/2024/0892"

### Paso 3: Ver qué consumió esa orden
*"¿Qué ingredientes usó?"*
- La orden de empaque dice: "Usé 520 kg del lote LOTE-CONG-2024-0445"

### Paso 4: Buscar cuándo se creó ESE lote
*"¿Y ese de dónde salió?"*
- Busca la primera vez que apareció "LOTE-CONG-2024-0445"
- Descubre que fue el 14/12 en la orden "MO/TUNEL/2024/0156"

### Paso 5: Repetir el proceso
*"¿Qué consumió el túnel?"*
- La orden de congelado dice: "Usé 800 kg del lote LOTE-VAC-2024-0223"

### Paso 6: Seguir rastreando
*"¿Y ese?"*
- Busca "LOTE-VAC-2024-0223"
- Descubre que fue el 14/12 en la orden "MO/SALA3/2024/0223"

### Paso 7: Llegar al origen
*"¿Qué consumió el vaciado?"*
- La orden de proceso dice: "Usé 1000 kg del lote MP-2024-1892"

### Paso 8: Buscar quién trajo esa MP
*"¿Y de dónde vino esa fruta fresca?"*
- Busca el lote "MP-2024-1892"
- Ve que llegó el 10/12 en el camión "WH/IN/2024/0445"
- Ese camión era del proveedor "Agrícola San José S.A."

**¡BINGO! 🎯 Ya sabemos de dónde vino todo.**

---

## 📊 RESULTADO VISUAL

```
VENTA (22/12)
   PALLET-RF-2024-0156 → 500 kg
      ↓
EMPAQUE (15/12) - Línea Retail
   Consumió: 520 kg congelado
   Produjo: 500 kg empacado
   Rendimiento: 96%
      ↓
CONGELADO (14/12) - Túnel
   Consumió: 800 kg procesado
   Produjo: 800 kg congelado
   Rendimiento: 100%
      ↓
VACIADO (14/12) - Sala 3
   Consumió: 1000 kg fresco
   Produjo: 800 kg procesado
   Rendimiento: 80%
      ↓
RECEPCIÓN (10/12)
   Proveedor: Agrícola San José S.A.
   Cantidad: 1000 kg frambuesa fresca
   
RENDIMIENTO TOTAL: 500/1000 = 50%
(De cada kilo que compras, terminas vendiendo medio kilo)
```

---

## 🔑 LAS 3 CLAVES QUE HACEN QUE FUNCIONE

### 1. **Los Lotes (Números de Serie)**
- Cada "grupo" de fruta tiene un número único
- Como cuando ves en un huevo: "Lote: 2024-12-10-A"
- En Odoo se llaman `stock.lot`

### 2. **Las Órdenes de Manufactura (Recetas)**
- Cada proceso tiene una "orden de trabajo"
- Dice: "Usé X kilos de esto → obtuve Y kilos de aquello"
- En Odoo se llaman `mrp.production`

### 3. **Los Movimientos (El Historial)**
- Cada vez que algo se mueve, queda registrado
- Como el historial de seguimiento de un paquete
- En Odoo se llaman `stock.move.line`

---

## 💡 EJEMPLO DE LA VIDA REAL

Es como cuando compras miel en el supermercado:

1. **En la etiqueta** dice: "Lote: 2024-001"
2. Buscas ese lote en internet
3. Te dice: "Este lote fue envasado el 15/01/2024 en la planta de Santiago"
4. Esa planta recibió miel del **apicultor Pedro González** el 10/01/2024
5. Pedro tiene colmenas en **Curicó, parcela 23**

**¡Exactamente lo mismo hace Odoo con tu frambuesa!**

---

## ✅ RESUMEN EN 3 FRASES

1. **Cada pallet tiene un código** (como un número de serie)
2. **Ese código te lleva a una "orden de trabajo"** que dice qué se usó para hacerlo
3. **Repites el proceso** hacia atrás hasta llegar al productor original

**Es como seguir las migas de pan de Hansel y Gretel, pero al revés** 🍞

---

## 🎓 VENTAJA PARA TU NEGOCIO

**Antes (Sin trazabilidad):**
- Cliente: "Este pallet tiene fruta mala"
- Tú: "Ehhh... no sé de dónde vino 🤷"

**Ahora (Con trazabilidad):**
- Cliente: "Este pallet tiene fruta mala"
- Tú: "Dame 2 minutos..."
- [Buscas en Odoo]
- Tú: "Ese pallet vino del productor Agrícola San José, lote recibido el 10/12. Ya lo estoy llamando para reclamar."

**¡Eso es poder!** 💪

---

## 🔍 PREGUNTA FRECUENTE

**P: ¿Y si mezclo fruta de 2 productores en el mismo pallet?**

**R:** ¡No hay problema! El sistema lo detecta.

Imagina que en el vaciado usaste:
- 600 kg del productor "San José" (lote MP-001)
- 400 kg del productor "Los Andes" (lote MP-002)

Cuando rastreas, el sistema te dirá:
```
"Este pallet viene de:
  - 60% Agrícola San José (600kg)
  - 40% Cooperativa Los Andes (400kg)"
```

**Es como los ingredientes en una receta:** si haces una pizza mitad jamón (proveedor A) y mitad champiñones (proveedor B), sabes exactamente qué vino de dónde.

---

**Creado para entender fácil 🎯**
**Sin tecnicismos, solo lógica simple**
