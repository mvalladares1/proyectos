# Fix: Recepciones Canceladas y Devoluciones

## Fecha: 5 de febrero de 2026

## Problemas Identificados

### 1. Recepción RF/RFP/IN/00507 (Cancelada aparece en dashboard)

**Problema:**
- La recepción RF/RFP/IN/00507 está CANCELADA en Odoo (state='cancel')
- Sin embargo, aparecía en el dashboard de recepciones
- Datos en Odoo:
  - ID: 13137
  - Estado: **cancel**
  - Fecha: 21/12/2025
  - Productor: AGRÍCOLA TRES ROBLES
  - Guía: 519,..
  - OC: OC09282
  - Producto: [101222000] AR HB Org. IQF en Bandeja
  - Kg planificados: 4633.7 kg
  - Kg hechos: 430.5 kg (antes de cancelar)

**Causa:**
El servicio `recepcion_service.py` no estaba filtrando explícitamente las recepciones canceladas.

**Solución:**
Se agregó un filtro explícito en el domain de búsqueda:
```python
# SIEMPRE excluir recepciones canceladas
domain.append(("state", "!=", "cancel"))
```

### 2. Recepción RF/RFP/IN/01045 (Devolución no reflejada)

**Problema:**
- La recepción RF/RFP/IN/01045 tiene una devolución asociada (RF/OUT/02586)
- Los kg devueltos NO se restaban de los kg recibidos
- Dashboard mostraba kg brutos en lugar de kg netos

**Datos en Odoo:**
- **Recepción IN/01045:**
  - ID: 14114
  - Estado: done
  - Fecha: 31/12/2025
  - Productor: AGRÍCOLA TRES ROBLES
  - Guía: 526
  - Producto: [101224000] AR DK Org. IQF en Bandeja
  - **Kg recibidos: 2745.55 kg**
  - Bandejas: 361 unidades (no se suman a los kg)

- **Devolución OUT/02586:**
  - ID: 14472
  - Estado: done
  - Fecha: 05/01/2026
  - Origin: "Retorno de RF/RFP/IN/01045"
  - Producto: [101224000] AR DK Org. IQF en Bandeja
  - **Kg devueltos: 1072.30 kg**

**Kg Netos Esperados:**
```
2745.55 kg (recibidos) - 1072.30 kg (devueltos) = 1673.25 kg NETOS
```

*Nota: Las bandejas (361 unidades) no se incluyen en el cálculo de kg porque tienen una UOM diferente (unidades vs kg).*

**Causa:**
1. El servicio buscaba devoluciones pero las EXCLUÍA completamente en lugar de restar los kg
2. La extracción del nombre de recepción desde el campo `origin` no era robusta
3. No se calculaban los kg netos por producto

**Solución:**

#### Mejora en detección de devoluciones:
```python
# Buscar devoluciones en un rango más amplio (30 días antes)
# Extraer nombre de recepción con regex
match = re.search(r'(RF/[A-Z]+/IN/\d+|SNJ/INMP/\d+|Vilk/IN/\d+)', origin)
```

#### Cálculo de kg netos:
```python
# Calcular kg devueltos por recepción y por producto
kg_total_devuelto = 0
if albaran in devoluciones_por_recepcion:
    for dev_id in devoluciones_por_recepcion[albaran]:
        dev_moves = moves_by_picking.get(dev_id, [])
        kg_total_devuelto += sum(m.get("quantity_done", 0) or 0 for m in dev_moves)

# Kg netos = kg recibidos - kg devueltos
kg_total = kg_total_recepcion - kg_total_devuelto
```

#### Cálculo por producto:
```python
# Calcular kg devueltos por producto
kg_devueltos_por_producto = {}
# ... (mapeo de devoluciones por producto)

# Al crear lista de productos:
kg_hechos_recepcion = m.get("quantity_done", 0) or 0
kg_hechos_devueltos = kg_devueltos_por_producto.get(prod_id, 0)
kg_hechos = kg_hechos_recepcion - kg_hechos_devueltos  # Kg netos
```

## Cambios Implementados

### Archivo modificado: `backend/services/recepcion_service.py`

1. **Filtrado de recepciones canceladas:**
   - Se agregó `domain.append(("state", "!=", "cancel"))` después del filtrado de estados
   - Esto garantiza que NUNCA se incluyan recepciones canceladas

2. **Mejora en detección de devoluciones:**
   - Se cambiaron de `recepciones_con_devolucion` (set) a `devoluciones_por_recepcion` (dict)
   - Se usa regex para extraer nombres de recepción desde el campo `origin`
   - Se buscan devoluciones en un rango de 30 días antes de fecha_inicio

3. **Cálculo de kg netos:**
   - Se obtienen movimientos de devoluciones junto con movimientos de recepciones
   - Se calculan kg devueltos total y por producto
   - Se restan los kg devueltos de los kg recibidos
   - Se excluyen recepciones con kg netos <= 0 (devolución completa)

4. **Mejora en productos:**
   - Cada producto muestra kg netos (después de devoluciones)
   - Costos se calculan sobre kg netos
   - Solo se incluyen productos con kg > 0 después de devoluciones

## Verificación

### Script de debug: `debug_recepciones_507_1045.py`

Se creó un script para investigar estas recepciones específicas en Odoo.

**Ejecución:**
```bash
cd "c:\new\RIO FUTURO\DASHBOARD\proyectos"
python debug_recepciones_507_1045.py
```

**Resultados:**
- ✅ RF/RFP/IN/00507: Confirmado estado CANCEL en Odoo
- ✅ RF/RFP/IN/01045: Confirmado devolución RF/OUT/02586
- ✅ Kg netos calculados correctamente: 2745.55 - 1072.30 = 1673.25 kg

## Impacto en Dashboard

### Antes:
- RF/RFP/IN/00507 aparecía con 430.5 kg (cancelada pero visible)
- RF/RFP/IN/01045 mostraba 2745.55 kg (sin restar devolución)

### Después:
- ❌ RF/RFP/IN/00507: NO aparece (filtrada por estado cancel)
- ✅ RF/RFP/IN/01045: Muestra 1673.25 kg (kg netos después de devolución)

## Consideraciones

1. **Caché:** Los cambios requieren que el caché expire (5 minutos) o se invalide manualmente
2. **Performance:** Se agregó una llamada adicional para obtener movimientos de devoluciones, pero se hace en batch para mantener eficiencia
3. **Devoluciones parciales:** El sistema ahora maneja correctamente devoluciones parciales mostrando kg netos
4. **Devoluciones completas:** Recepciones con devolución 100% se excluyen automáticamente

## Próximos Pasos

1. ✅ Validar en dashboard que RF/RFP/IN/00507 ya no aparece
2. ✅ Validar en dashboard que RF/RFP/IN/01045 muestra kg netos correctos
3. 📋 Verificar otras recepciones con devoluciones en el sistema
4. 📋 Actualizar documentación de usuario sobre cálculo de kg netos

## Logs de Debug

Cuando el servicio detecta devoluciones, ahora imprime:
```
[INFO] Se encontraron 5 devoluciones completadas
[INFO] Recepciones con devoluciones: 3
[INFO] RF/RFP/IN/01045: 2745.55 kg recibidos - 1072.30 kg devueltos = 1673.25 kg netos
```

Cuando excluye una recepción cancelada o con devolución completa:
```
[INFO] Excluyendo RF/RFP/IN/00507: devolución completa (0 kg netos)
```
