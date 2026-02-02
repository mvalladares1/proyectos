# 🧪 Scripts de Prueba - Sistema de Proformas

Este directorio contiene scripts para probar y validar el sistema de envío de proformas de fletes.

## 📁 Archivos Disponibles

### 1. `test_proforma_email.py`
**Propósito**: Genera ejemplos de PDF y template HTML actual

**Salida**:
- `proforma_test_YYYYMMDD_HHMMSS.pdf` - PDF de ejemplo con datos de prueba
- `proforma_email_test_YYYYMMDD_HHMMSS.html` - Template HTML actual

**Uso**:
```powershell
python test_proforma_email.py
```

### 2. `test_email_templates.py`
**Propósito**: Compara template actual vs mejorado

**Salida**:
- `proforma_email_ACTUAL_YYYYMMDD_HHMMSS.html` - Template simple (versión anterior)
- `proforma_email_MEJORADO_YYYYMMDD_HHMMSS.html` - Template mejorado (versión nueva)
- `COMPARACION_templates_YYYYMMDD_HHMMSS.html` - Página de comparación lado a lado

**Uso**:
```powershell
python test_email_templates.py
```

## 🎯 ¿Cuándo usar cada script?

### Usa `test_proforma_email.py` cuando:
- Quieras ver cómo se ve el PDF generado
- Necesites un ejemplo rápido del correo
- Estés probando cambios en el formato del PDF

### Usa `test_email_templates.py` cuando:
- Quieras comparar visualmente ambos templates
- Necesites decidir qué template implementar
- Estés evaluando cambios en el diseño del email

## 📊 Datos de Prueba

Ambos scripts usan los mismos datos de prueba:

```python
Transportista: TRANSPORTES RODRIGUEZ LIMITADA
Período: 2026-01-01 al 2026-01-31
OCs: 3 órdenes de compra
- PO00123: San José - La Granja (450 km, 12,500 kg, $225,000)
- PO00145: Temuco - La Granja (680 km, 18,000 kg, $340,000)
- PO00167: Curicó - La Granja (250 km, 9,000 kg, $125,000)

Total: 1,380 km | 39,500 kg | $690,000
```

## ✅ Validación

Después de ejecutar los scripts:

1. **Abre los archivos HTML** en tu navegador
2. **Verifica el diseño** - ¿Se ve profesional?
3. **Revisa los datos** - ¿Son precisos y están bien formateados?
4. **Prueba en móvil** - ¿Es responsive el diseño mejorado?
5. **Compara colores** - ¿Coinciden con la identidad corporativa?

## 🎨 Diferencias Clave

| Aspecto | Template Actual | Template Mejorado |
|---------|----------------|-------------------|
| Tamaño | ~1,775 chars | ~10,712 chars |
| Header | Azul plano | Gradiente azul |
| Resumen | Lista simple | Tabla visual |
| Total | En lista | Caja destacada |
| Contacto | No incluido | Email + Teléfono |
| Responsive | ❌ No | ✅ Sí |
| Adjunto | Mención simple | Aviso destacado |

## 🚀 Implementación

Una vez validados los templates, el sistema de producción en 
`tab_proforma_consolidada.py` ya está configurado para usar 
el template mejorado automáticamente.

## 📝 Notas

- Los archivos se generan en el mismo directorio donde ejecutas el script
- Los nombres incluyen timestamp para evitar sobrescribir archivos anteriores
- Puedes modificar los datos de prueba editando las variables al inicio de cada script
