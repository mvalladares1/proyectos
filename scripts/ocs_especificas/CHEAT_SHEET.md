# 📝 CHEAT SHEET - Corrección de OCs

**Comandos y snippets más usados para corrección rápida**

---

## 🚀 INICIO RÁPIDO

```powershell
# Activar entorno
& "c:\new\RIO FUTURO\DASHBOARD\.venv\Scripts\Activate.ps1"

# Ir al directorio
cd "proyectos\scripts\ocs_especificas"

# Verificar estructura
python verificar_estructura.py
```

---

## 📋 WORKFLOW BÁSICO

### 1️⃣ Copiar templates
```powershell
# Para análisis
cp templates/TEMPLATE_1_analizar_oc.py analisis/analizar_oc12345.py

# Para corrección
cp templates/TEMPLATE_2_corregir_oc_cadena.py ejecuciones/EJECUTAR_corregir_oc12345.py
```

### 2️⃣ Configurar análisis
```python
# En analisis/analizar_oc12345.py
OC_NAME = "OC12345"
PRECIO_CORRECTO = 3300.0  # Nuevo precio
CANTIDAD_CORRECTA = 1000.0  # Nueva cantidad (opcional)
```

### 3️⃣ Ejecutar análisis
```powershell
python analisis/analizar_oc12345.py
```

### 4️⃣ Anotar datos del análisis
```
📝 ANOTAR:
- ID de la OC: _______
- ID línea a corregir: _______
- ID moves asociados: _______
- IDs facturas a eliminar: _______
```

### 5️⃣ Configurar corrección
```python
# En ejecuciones/EJECUTAR_corregir_oc12345.py
CORRECCIONES = {
    'oc_id': 9999,                    # Del análisis
    'oc_name': 'OC12345',
    'moneda_id': None,                # 2=USD, 45=CLP, None=no cambiar
    'facturas_eliminar': [],          # IDs de facturas draft
    'lineas': [
        {
            'linea_id': 20111,        # Del análisis
            'precio_nuevo': 3300.0,   # Precio correcto
            'cantidad_nueva': None,   # None si no se cambia
            'moves_ids': [160742]     # Del análisis
        }
    ]
}
```

### 6️⃣ Ejecutar corrección
```powershell
python ejecuciones/EJECUTAR_corregir_oc12345.py
```

### 7️⃣ Verificar resultado
```powershell
# Ver estado de todas las OCs
python utils/verificar_estado_general.py

# Verificar propagación de precios
python utils/verificar_propagacion_precios.py
```

---

## 🎯 CASOS ESPECÍFICOS

### Solo cambiar PRECIO
```python
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'lineas': [{
        'linea_id': 20111,
        'precio_nuevo': 2.0,
        'cantidad_nueva': None,       # ⬅️ None
        'moves_ids': [160742]
    }]
}
```

### Solo cambiar CANTIDAD
```python
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'lineas': [{
        'linea_id': 20111,
        'precio_nuevo': None,         # ⬅️ None
        'cantidad_nueva': 746.65,
        'moves_ids': []               # ⬅️ Vacío
    }]
}
```

### Cambiar PRECIO + CANTIDAD
```python
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'lineas': [{
        'linea_id': 20111,
        'precio_nuevo': 3300.0,
        'cantidad_nueva': 5000.0,
        'moves_ids': [160742]
    }]
}
```

### Eliminar FACTURA DRAFT antes
```python
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'facturas_eliminar': [307678],    # ⬅️ IDs de facturas
    'lineas': [...]
}
```

### Cambiar MONEDA (DOS SCRIPTS)
```python
# SCRIPT 1: Solo moneda
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'moneda_id': 45,                  # 2=USD, 45=CLP
    'lineas': [{
        'linea_id': 20111,
        'precio_nuevo': None,         # ⬅️ NO cambiar aún
        'cantidad_nueva': None,
        'moves_ids': []
    }]
}

# SCRIPT 2: Solo precio (después)
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'moneda_id': None,                # ⬅️ Ya está en moneda correcta
    'lineas': [{
        'linea_id': 20111,
        'precio_nuevo': 3085.0,
        'moves_ids': [160742]
    }]
}
```

### Múltiples LÍNEAS
```python
CORRECCIONES = {
    'oc_id': 9999,
    'oc_name': 'OC12345',
    'lineas': [
        {
            'linea_id': 20111,
            'precio_nuevo': 2.0,
            'moves_ids': [160742]
        },
        {
            'linea_id': 20112,
            'precio_nuevo': 3.0,
            'moves_ids': [160743]
        }
    ]
}
```

---

## 🔍 BÚSQUEDAS RÁPIDAS

```powershell
# Buscar OC específica en archivos
Get-ChildItem -Recurse -Filter "*12288*"

# Buscar en contenido
Select-String -Path "ejecuciones\*.py" -Pattern "OC12288"

# Ver último log generado
Get-ChildItem -Filter "log_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1

# Ver contenido de log
Get-Content (Get-ChildItem -Filter "log_*" | Sort-Object LastWriteTime -Descending | Select-Object -First 1).FullName | ConvertFrom-Json | ConvertTo-Json
```

---

## 📊 REPORTES

```powershell
# Reporte completo de todas las OCs
python utils/REPORTE_COMPLETO_ocs_corregidas.py

# Ver estado general
python utils/verificar_estado_general.py

# Verificar propagación
python utils/verificar_propagacion_precios.py
```

---

## 🔧 SNIPPETS ÚTILES

### Conectar a Odoo
```python
import xmlrpc.client

url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})

models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')
```

### Buscar OC por nombre
```python
oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
    [[('name', '=', 'OC12345')]],
    {'fields': ['id', 'name', 'state', 'amount_total', 'currency_id']}
)[0]
```

### Buscar líneas de OC
```python
lineas = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[('order_id', '=', oc_id)]],
    {'fields': ['id', 'product_id', 'price_unit', 'product_qty', 'price_subtotal']}
)
```

### Buscar stock moves
```python
moves = models.execute_kw(db, uid, password, 'stock.move', 'search_read',
    [[('purchase_line_id', '=', linea_id)]],
    {'fields': ['id', 'price_unit', 'quantity_done', 'state']}
)
```

### Buscar valuation layers por move
```python
layers = models.execute_kw(db, uid, password, 'stock.valuation.layer', 'search_read',
    [[('stock_move_id', '=', move_id)]],
    {'fields': ['id', 'description', 'unit_cost', 'value', 'quantity']}
)
```

### Actualizar registro
```python
models.execute_kw(db, uid, password, 'purchase.order.line', 'write',
    [[linea_id], {'price_unit': 3300.0}]
)
```

### Eliminar factura draft
```python
models.execute_kw(db, uid, password, 'account.move', 'unlink', [[factura_id]])
```

---

## ⚠️ REGLAS DE ORO

1. **Siempre analizar antes de corregir** → `TEMPLATE_1` primero
2. **Eliminar facturas draft antes** → Bloquean cambios
3. **Moneda antes que precio** → Dos scripts separados
4. **Anotar todos los IDs** → Del análisis a la corrección
5. **Verificar después** → `verificar_estado_general.py`
6. **Corrección en cadena** → purchase.order.line → stock.move → stock.valuation.layer
7. **Un move cancelado no afecta** → Solo si `quantity_done > 0`
8. **Logs = evidencia** → Siempre revisar JSON generado

---

## 🆘 ERRORES COMUNES

| Error | Causa | Solución |
|-------|-------|----------|
| `cannot change currency` | Factura confirmada | No usar sistema, manual |
| `no match found` | Patrón búsqueda incorrecto | Usar `stock_move_id` |
| `amount_total` no coincide | Precio no actualizado | Corrección en cadena |
| `draft invoice` impide cambios | Factura borrador | Eliminarla primero |

---

## 📚 DOCUMENTACIÓN

- **Guía rápida**: [`docs/GUIA_RAPIDA.md`](docs/GUIA_RAPIDA.md)
- **Flujo detallado**: [`docs/FLUJO_CORRECCION_OCS.md`](docs/FLUJO_CORRECCION_OCS.md)
- **Documentación técnica**: [`docs/README.md`](docs/README.md)
- **Índice completo**: [`INDICE.md`](INDICE.md)

---

**Última actualización**: 11 de Marzo, 2026  
**Versión**: 2.0
