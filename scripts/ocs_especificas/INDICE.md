# 🗂️ ÍNDICE RÁPIDO - Sistema de Corrección de OCs

**Última actualización**: 11 de Marzo, 2026

---

## 📚 DOCUMENTACIÓN

📖 **Empezar aquí**:
- [`docs/GUIA_RAPIDA.md`](docs/GUIA_RAPIDA.md) - ⭐ Guía de uso con ejemplos
- [`docs/README.md`](docs/README.md) - Documentación técnica completa
- [`docs/FLUJO_CORRECCION_OCS.md`](docs/FLUJO_CORRECCION_OCS.md) - Proceso detallado

---

## 🛠️ TEMPLATES (Copiar y usar)

📝 **Plantillas reutilizables**:
- [`templates/TEMPLATE_1_analizar_oc.py`](templates/TEMPLATE_1_analizar_oc.py) - Para análisis
- [`templates/TEMPLATE_2_corregir_oc_cadena.py`](templates/TEMPLATE_2_corregir_oc_cadena.py) - Para corrección

**Uso**:
```bash
# Copiar template de análisis
cp templates/TEMPLATE_1_analizar_oc.py analisis/analizar_oc12345.py

# Copiar template de corrección
cp templates/TEMPLATE_2_corregir_oc_cadena.py ejecuciones/EJECUTAR_corregir_oc12345.py
```

---

## ⚙️ UTILIDADES

🔧 **Herramientas de verificación**:
- [`utils/verificar_estado_general.py`](utils/verificar_estado_general.py) - Verificar todas las OCs corregidas
- [`utils/verificar_propagacion_precios.py`](utils/verificar_propagacion_precios.py) - Verificar precios en cadena
- [`utils/REPORTE_COMPLETO_ocs_corregidas.py`](utils/REPORTE_COMPLETO_ocs_corregidas.py) - Reporte detallado

**Ejecutar**:
```bash
python utils/verificar_estado_general.py
python utils/verificar_propagacion_precios.py
```

---

## 🔍 ANÁLISIS HISTÓRICOS

📊 **Scripts de análisis realizados** (en `analisis/`):

### OC12288 (Precio $0 → $2.0)
- `analizar_oc12288_impacto.py`

### OC11401 (Precio $6.5 → $1.6)
- `analizar_oc11401_completo.py`
- `analizar_oc11401_impacto.py`

### OC09581 (Cantidad 103 → 746.65)
- `analizar_oc09581_cantidad.py`

### Múltiples OCs
- `analizar_3_ocs_errores.py` - OC12902, OC09581, OC12363
- `analizar_4_ocs_errores.py` - OC12755, OC13491, OC13530, OC13596

### Otros
- `investigar_factura_oc12288.py`
- `investigar_aprobacion_oc12393.py`

---

## ▶️ EJECUCIONES REALIZADAS

✅ **Scripts de corrección ejecutados** (en `ejecuciones/`):

| Script | OC(s) Corregida(s) | Tipo |
|--------|-------------------|------|
| `EJECUTAR_corregir_oc12288.py` | OC12288 | Precio $0→$2.0 |
| `EJECUTAR_corregir_oc11401.py` | OC11401 | Precio + Factura |
| `EJECUTAR_corregir_3_ocs.py` | OC12902, OC09581, OC12363 | Moneda |
| `EJECUTAR_corregir_4_ocs.py` | OC12755, OC13491, OC13530, OC13596 | Precio + Cantidad |
| `EJECUTAR_corregir_oc09581_cantidad.py` | OC09581 | Cantidad |
| `EJECUTAR_ajustar_precio_oc12902.py` | OC12902 | Precio (inicial) |
| `REVERTIR_oc12902_solo_precio.py` | OC12902 | Revertir moneda |
| `EJECUTAR_correccion_cadena_precios.py` | 5 OCs | Corrección en cadena |

---

## 🎯 FLUJO DE TRABAJO ESTÁNDAR

```
┌─────────────────────────────────────────────────────────┐
│ 1. COPIAR TEMPLATES                                     │
│    cp templates/TEMPLATE_1_*.py analisis/               │
│    cp templates/TEMPLATE_2_*.py ejecuciones/            │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 2. CONFIGURAR Y EJECUTAR ANÁLISIS                       │
│    - Editar OC_NAME, PRECIO_CORRECTO, CANTIDAD          │
│    - python analisis/analizar_ocXXXXX.py                │
│    - Anotar IDs de líneas, moves, facturas              │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 3. CONFIGURAR CORRECCIÓN                                │
│    - Editar CORRECCIONES{} con datos del análisis       │
│    - Configurar lineas, moves_ids, facturas_eliminar    │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 4. EJECUTAR CORRECCIÓN                                  │
│    - python ejecuciones/EJECUTAR_corregir_ocXXXXX.py    │
│    - Revisar log JSON generado                          │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ 5. VERIFICAR                                            │
│    - python utils/verificar_estado_general.py           │
│    - Validar en Odoo UI si es necesario                 │
└─────────────────────────────────────────────────────────┘
```

---

## ⚡ COMANDOS RÁPIDOS

```bash
# Activar entorno virtual
& "c:\new\RIO FUTURO\DASHBOARD\.venv\Scripts\Activate.ps1"

# Navegar a directorio
cd "proyectos\scripts\ocs_especificas"

# Ver estructura
Get-ChildItem -Directory

# Ejecutar análisis ejemplo
python analisis/analizar_oc12288_impacto.py

# Ejecutar verificación general
python utils/verificar_estado_general.py

# Buscar OC específica
Get-ChildItem -Recurse -Filter "*12288*"
```

---

## 📋 CASOS DE USO COMUNES

### Corregir solo precio
```python
# En ejecuciones/EJECUTAR_*.py
CORRECCIONES = {
    'lineas': [{
        'linea_id': 20111,
        'precio_nuevo': 2.0,
        'cantidad_nueva': None,
        'moves_ids': [160742]
    }]
}
```

### Corregir solo cantidad
```python
CORRECCIONES = {
    'lineas': [{
        'linea_id': 16048,
        'precio_nuevo': None,
        'cantidad_nueva': 746.65,
        'moves_ids': []  # Cantidad no requiere actualizar moves
    }]
}
```

### Corregir precio + cantidad
```python
CORRECCIONES = {
    'lineas': [{
        'linea_id': 20854,
        'precio_nuevo': 2000.0,
        'cantidad_nueva': 138.48,
        'moves_ids': [163847]
    }]
}
```

### Cambiar moneda + precio
```python
# PASO 1: Solo moneda
CORRECCIONES = {
    'moneda_id': 45,  # CLP
    'lineas': [{
        'linea_id': 21140,
        'precio_nuevo': None,  # NO cambiar aún
        'moves_ids': []
    }]
}

# PASO 2 (script separado): Solo precio
CORRECCIONES = {
    'moneda_id': None,  # Ya está en CLP
    'lineas': [{
        'linea_id': 21140,
        'precio_nuevo': 3085.0,
        'moves_ids': [166160]
    }]
}
```

---

## 🔐 ARCHIVOS DE CONFIGURACIÓN

### Credenciales de Odoo
Están hardcoded en todos los scripts:
```python
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'
```

### IDs de Monedas
- USD: `2`
- CLP: `45`

---

## 📊 ESTADÍSTICAS

- **OCs corregidas**: 8
- **Scripts creados**: 25+
- **Templates**: 2
- **Utilidades**: 4
- **Documentos**: 3
- **Impacto total**: ~$68M CLP + $12K USD

---

## 🆘 TROUBLESHOOTING

| Problema | Solución |
|----------|----------|
| Moneda no coincide | Cambiar moneda antes de precio (2 scripts) |
| No encuentra capas | Buscar por stock_move_id (automático en template) |
| Factura bloqueada | Revisar si es borrador (se elimina) o confirmada (no usar sistema) |
| Total no coincide | Verificar precio en purchase.order.line |

---

## 📞 SOPORTE

1. ⭐ **Primera vez**: Leer `docs/GUIA_RAPIDA.md`
2. 📖 **Técnico**: Consultar `docs/FLUJO_CORRECCION_OCS.md`
3. 🔍 **Ejemplos**: Ver scripts en `ejecuciones/` y `analisis/`
4. ✅ **Verificar**: Ejecutar `utils/verificar_estado_general.py`

---

**Versión**: 2.0  
**Empresa**: AGRICOLA RIO FUTURO Spa  
**Contacto**: mvalladares@riofuturo.cl
