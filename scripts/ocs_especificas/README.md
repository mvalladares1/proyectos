# 📁 Sistema de Corrección de Órdenes de Compra (OCs)

Sistema estandarizado para corregir errores en Órdenes de Compra en Odoo ERP con corrección en cadena completa.

> 🎯 **[ÍNDICE RÁPIDO](INDICE.md)** - Acceso rápido a casos de uso, comandos y troubleshooting  
> 📝 **[CHEAT SHEET](CHEAT_SHEET.md)** - Comandos y snippets para corrección rápida

---

## 📂 ESTRUCTURA DEL PROYECTO

```
ocs_especificas/
│
├── docs/                    # 📚 Documentación completa
│   ├── README.md           # Documentación técnica del sistema
│   ├── GUIA_RAPIDA.md      # Guía de uso con ejemplos prácticos
│   └── FLUJO_CORRECCION_OCS.md  # Flujo detallado (5 fases)
│
├── templates/              # 🛠️ Templates reutilizables
│   ├── TEMPLATE_1_analizar_oc.py      # Template para análisis
│   └── TEMPLATE_2_corregir_oc_cadena.py  # Template para corrección
│
├── utils/                  # ⚙️ Utilidades y verificaciones
│   ├── verificar_propagacion_precios.py  # Verificar precios en cadena
│   ├── verificar_estado_general.py       # Verificación completa de OCs
│   ├── REPORTE_COMPLETO_ocs_corregidas.py  # Reporte general
│   └── leer_check1_check2_completo.py    # Utilidad lectura
│
├── ejecuciones/            # ▶️ Scripts de ejecución (correcciones)
│   ├── EJECUTAR_corregir_oc12288.py
│   ├── EJECUTAR_corregir_oc11401.py
│   ├── EJECUTAR_corregir_3_ocs.py
│   ├── EJECUTAR_corregir_4_ocs.py
│   ├── EJECUTAR_corregir_oc09581_cantidad.py
│   ├── EJECUTAR_ajustar_precio_oc12902.py
│   ├── EJECUTAR_correccion_cadena_precios.py
│   └── REVERTIR_oc12902_solo_precio.py
│
└── analisis/               # 🔍 Scripts de análisis e investigación
    ├── analizar_oc12288_impacto.py
    ├── analizar_oc11401_completo.py
    ├── analizar_oc09581_cantidad.py
    ├── analizar_3_ocs_errores.py
    ├── analizar_4_ocs_errores.py
    ├── investigar_factura_oc12288.py
    ├── investigar_aprobacion_oc12393.py
    └── [otros scripts de análisis]
```

---

## 🚀 INICIO RÁPIDO

### Para corregir una nueva OC:

1. **Leer la guía**
   ```bash
   # Ver docs/GUIA_RAPIDA.md
   ```

2. **Copiar templates**
   ```bash
   cp templates/TEMPLATE_1_analizar_oc.py analisis/analizar_ocNUEVA.py
   cp templates/TEMPLATE_2_corregir_oc_cadena.py ejecuciones/EJECUTAR_corregir_ocNUEVA.py
   ```

3. **Editar y ejecutar análisis**
   ```bash
   # Editar analisis/analizar_ocNUEVA.py (configurar OC_NAME, precios)
   python analisis/analizar_ocNUEVA.py
   ```

4. **Configurar y ejecutar corrección**
   ```bash
   # Editar ejecuciones/EJECUTAR_corregir_ocNUEVA.py (con datos del análisis)
   python ejecuciones/EJECUTAR_corregir_ocNUEVA.py
   ```

5. **Verificar resultado**
   ```bash
   python utils/verificar_estado_general.py
   ```

---

## 📖 DOCUMENTACIÓN PRINCIPAL

| Documento | Ubicación | Descripción |
|-----------|-----------|-------------|
| **Guía Rápida** | `docs/GUIA_RAPIDA.md` | ⭐ **EMPEZAR AQUÍ** - Ejemplos y casos de uso |
| **README Técnico** | `docs/README.md` | Documentación completa del sistema |
| **Flujo de Corrección** | `docs/FLUJO_CORRECCION_OCS.md` | Proceso detallado en 5 fases |

---

## 🎯 CONCEPTOS CLAVE

### Corrección en Cadena (CRÍTICO)
Los precios NO se propagan automáticamente. Debes actualizar:

```
1. purchase.order.line   (precio_unit, product_qty)
      ↓
2. stock.move           (price_unit)
      ↓
3. stock.valuation.layer (unit_cost, value)
```

### Templates Reutilizables
- `TEMPLATE_1`: Análisis completo de OC
- `TEMPLATE_2`: Corrección en cadena completa

### Logs Automáticos
Cada ejecución genera JSON con todos los cambios.

---

## ✅ OCs CORREGIDAS

**8 OCs corregidas exitosamente:**

| OC | Corrección | Estado |
|----|-----------|--------|
| OC12288 | Precio $0→$2.0 USD | ✅ |
| OC11401 | Precio $6.5→$1.6 USD + factura | ✅ |
| OC12902 | Precio $3,080→$3,085 CLP | ✅ |
| OC09581 | Cantidad 103→746.65 kg | ✅ |
| OC12755 | Precio + Cantidad | ✅ |
| OC13491 | Precio + Cantidad | ✅ |
| OC13530 | Precio + Cantidad | ✅ |
| OC13596 | Precio + Cantidad | ✅ |

---

## 🛡️ SEGURIDAD

- ✅ Validaciones automáticas (estado, facturas)
- ✅ Logging exhaustivo en JSON
- ✅ Verificación post-corrección
- ✅ Templates probados en producción

---

## 📝 CONVENCIONES DE NOMBRES

### Archivos de Análisis:
- `analizar_ocXXXXX_*.py` - Análisis específicos
- `investigar_*.py` - Investigaciones detalladas

### Archivos de Ejecución:
- `EJECUTAR_corregir_ocXXXXX.py` - Correcciones específicas
- `EJECUTAR_*.py` - Cualquier ejecución que modifica datos

### Utilidades:
- `verificar_*.py` - Verificaciones sin modificar datos
- `REPORTE_*.py` - Generación de reportes

---

## 🔧 REQUISITOS

- Python 3.x
- xmlrpc.client (incluido en Python)
- Acceso a Odoo ERP (credenciales en templates)
- Virtual environment activado

---

## 📞 SOPORTE

1. **Primera vez**: Leer `docs/GUIA_RAPIDA.md`
2. **Dudas técnicas**: Consultar `docs/FLUJO_CORRECCION_OCS.md`
3. **Casos especiales**: Revisar logs de ejecuciones anteriores

---

## 🎓 LECCIONES APRENDIDAS

### ✅ Qué funciona:
- Corrección en cadena manual (line → move → layer)
- Búsqueda de capas por stock_move_id
- Templates reutilizables
- Logging detallado

### ❌ Qué NO hacer:
- Asumir propagación automática
- Corregir sin análisis previo
- Cambiar moneda y precio simultáneamente
- Modificar OCs con facturas confirmadas

---

## 🔄 ÚLTIMA ACTUALIZACIÓN

**Fecha**: 11 de Marzo, 2026  
**Versión**: 2.0  
**Total OCs corregidas**: 8  
**Scripts creados**: 25+

---

**📧 Contacto**: mvalladares@riofuturo.cl  
**🏢 Empresa**: AGRICOLA RIO FUTURO Spa
