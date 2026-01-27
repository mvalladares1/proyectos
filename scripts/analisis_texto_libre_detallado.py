import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from collections import defaultdict

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 100)
print("ANÁLISIS DETALLADO - LÍNEAS DE TEXTO LIBRE")
print("=" * 100)

# Obtener todas las líneas de texto libre
lineas_texto_libre = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['display_type', '=', 'product'],
        ['product_id', '=', False],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id', 'name', 'quantity', 'credit', 'debit', 'move_id', 'date', 'account_id'],
    limit=1000
)

print(f"\n📊 Total líneas texto libre: {len(lineas_texto_libre):,}")

# Agrupar por cuenta
cuentas_texto_libre = defaultdict(list)
for l in lineas_texto_libre:
    cuenta = l.get('account_id', [None, 'Sin cuenta'])
    cuenta_name = cuenta[1] if isinstance(cuenta, (list, tuple)) else str(cuenta)
    cuentas_texto_libre[cuenta_name].append(l)

print("\n📋 Por cuenta contable:")
for cuenta, lineas in sorted(cuentas_texto_libre.items(), key=lambda x: -len(x[1])):
    total_kg = sum(l.get('quantity', 0) for l in lineas)
    total_monto = sum(l.get('credit', 0) - l.get('debit', 0) for l in lineas)
    print(f"   {cuenta[:60]:60s}: {len(lineas):3d} líneas  {total_kg:10,.0f} kg  ${total_monto:15,.0f}")

# Analizar patrones en nombres
print("\n" + "=" * 100)
print("📋 ANÁLISIS DE PATRONES EN NOMBRES")
print("=" * 100)

# Keywords de frutas
frutas_keywords = {
    'ARANDANO': 'Arándano',
    'ARÁNDANO': 'Arándano', 
    'BLUEBERRY': 'Arándano',
    'FRAMBUESA': 'Frambuesa',
    'RASPBERRY': 'Frambuesa',
    'MORA': 'Mora',
    'BLACKBERRY': 'Mora',
    'FRUTILLA': 'Frutilla',
    'STRAWBERRY': 'Frutilla',
    'CEREZA': 'Cereza',
    'CHERRY': 'Cereza',
    'MIX': 'Mix',
    'TRIPLE': 'Mix'
}

# Keywords de manejo
manejo_keywords = {
    'ORGANICO': 'Orgánico',
    'ORGÁNICO': 'Orgánico',
    'ORGANIC': 'Orgánico',
    'CONVENCIONAL': 'Convencional',
    'CONVENTIONAL': 'Convencional',
    'CONV.': 'Convencional',
    'CONV ': 'Convencional'
}

# Categorizar líneas
categorizadas = {
    'frutas_identificables': [],
    'servicios': [],
    'activos_fijos': [],
    'otros_ingresos': [],
    'basura': []
}

for linea in lineas_texto_libre:
    nombre = str(linea.get('name', '') or '').upper()
    cuenta = linea.get('account_id', [None, 'Sin cuenta'])
    cuenta_name = cuenta[1] if isinstance(cuenta, (list, tuple)) else str(cuenta)
    
    # Detectar tipo de contenido
    if 'INGRESOS POR VENTAS DE PRODUCTOS' in cuenta_name:
        # Buscar si menciona alguna fruta
        tiene_fruta = any(key in nombre for key in frutas_keywords.keys())
        if tiene_fruta:
            categorizadas['frutas_identificables'].append(linea)
        else:
            categorizadas['basura'].append(linea)
    elif 'SERVICIOS' in cuenta_name or 'CAMARA' in nombre:
        categorizadas['servicios'].append(linea)
    elif 'ACTIVO' in cuenta_name or 'TRACTOR' in nombre or 'MTD' in nombre:
        categorizadas['activos_fijos'].append(linea)
    elif 'OTROS INGRESOS' in cuenta_name:
        categorizadas['otros_ingresos'].append(linea)
    else:
        categorizadas['basura'].append(linea)

print("\n📊 CATEGORIZACIÓN:")
for categoria, lineas in categorizadas.items():
    if lineas:
        total_kg = sum(l.get('quantity', 0) for l in lineas)
        total_monto = sum(l.get('credit', 0) - l.get('debit', 0) for l in lineas)
        print(f"\n   {categoria.upper().replace('_', ' ')}:")
        print(f"      Líneas: {len(lineas):,}")
        print(f"      Kg: {total_kg:,.0f}")
        print(f"      Monto: ${total_monto:,.0f}")

# Mostrar ejemplos de cada categoría
print("\n" + "=" * 100)
print("📋 EJEMPLOS POR CATEGORÍA")
print("=" * 100)

for categoria, lineas in categorizadas.items():
    if lineas:
        print(f"\n{categoria.upper().replace('_', ' ')} ({len(lineas)} líneas):")
        for i, l in enumerate(lineas[:5], 1):
            move_name = l.get('move_id', [None, 'N/A'])[1]
            nombre = str(l.get('name', 'N/A') or 'N/A')
            kg = l.get('quantity', 0)
            monto = l.get('credit', 0) - l.get('debit', 0)
            
            # Intentar detectar fruta y manejo
            nombre_upper = str(nombre or '').upper()
            fruta_detectada = None
            manejo_detectado = None
            
            for key, value in frutas_keywords.items():
                if key in nombre_upper:
                    fruta_detectada = value
                    break
            
            for key, value in manejo_keywords.items():
                if key in nombre_upper:
                    manejo_detectado = value
                    break
            
            info_extra = ""
            if fruta_detectada:
                info_extra += f" → {fruta_detectada}"
            if manejo_detectado:
                info_extra += f" / {manejo_detectado}"
            
            print(f"   {i}. {move_name}: {nombre[:70]}")
            print(f"      {kg:,.1f} kg | ${monto:,.0f}{info_extra}")

# Análisis de "basura"
print("\n" + "=" * 100)
print("⚠️  ANÁLISIS DE LÍNEAS PROBLEMÁTICAS (BASURA)")
print("=" * 100)

if categorizadas['basura']:
    print(f"\n📊 Total líneas basura: {len(categorizadas['basura'])}")
    total_kg_basura = sum(l.get('quantity', 0) for l in categorizadas['basura'])
    total_monto_basura = sum(l.get('credit', 0) - l.get('debit', 0) for l in categorizadas['basura'])
    print(f"   Kg: {total_kg_basura:,.0f}")
    print(f"   Monto: ${total_monto_basura:,.0f}")
    
    print("\n📋 TODAS las líneas basura:")
    for i, l in enumerate(categorizadas['basura'], 1):
        move_name = l.get('move_id', [None, 'N/A'])[1]
        nombre = str(l.get('name', 'N/A') or 'N/A')
        kg = l.get('quantity', 0)
        monto = l.get('credit', 0) - l.get('debit', 0)
        fecha = l.get('date', 'N/A')
        cuenta = l.get('account_id', [None, 'N/A'])[1]
        
        print(f"\n   {i}. {move_name} ({fecha})")
        print(f"      Descripción: {nombre}")
        print(f"      Cantidad: {kg:,.1f} kg | Monto: ${monto:,.0f}")
        print(f"      Cuenta: {cuenta}")

# Recomendaciones
print("\n" + "=" * 100)
print("💡 RECOMENDACIONES")
print("=" * 100)

print(f"""
1️⃣  FRUTAS IDENTIFICABLES ({len(categorizadas['frutas_identificables'])} líneas, ${sum(l.get('credit', 0) - l.get('debit', 0) for l in categorizadas['frutas_identificables']):,.0f}):
   ✅ MANTENER - Podemos extraer tipo de fruta del texto
   📝 Implementar parser automático de frutas/manejo desde descripción

2️⃣  SERVICIOS ({len(categorizadas['servicios'])} líneas, ${sum(l.get('credit', 0) - l.get('debit', 0) for l in categorizadas['servicios']):,.0f}):
   ❌ EXCLUIR - No son productos, son servicios
   📝 Agregar filtro: cuenta != 'INGRESOS VENTAS SERVICIOS'

3️⃣  ACTIVOS FIJOS ({len(categorizadas['activos_fijos'])} líneas, ${sum(l.get('credit', 0) - l.get('debit', 0) for l in categorizadas['activos_fijos']):,.0f}):
   ❌ EXCLUIR - No son frutas, son ventas de equipos
   📝 Agregar filtro: cuenta != 'VENTAS DE ACTIVOS FIJOS'

4️⃣  OTROS INGRESOS ({len(categorizadas['otros_ingresos'])} líneas, ${sum(l.get('credit', 0) - l.get('debit', 0) for l in categorizadas['otros_ingresos']):,.0f}):
   ❌ EXCLUIR - No son productos
   📝 Agregar filtro: cuenta != 'OTROS INGRESOS'

5️⃣  BASURA ({len(categorizadas['basura'])} líneas, ${sum(l.get('credit', 0) - l.get('debit', 0) for l in categorizadas['basura']):,.0f}):
   ⚠️  REVISAR - Ver lista arriba para decidir caso a caso
""")

# Resumen de impacto
total_excluir = (len(categorizadas['servicios']) + 
                 len(categorizadas['activos_fijos']) + 
                 len(categorizadas['otros_ingresos']))
total_kg_excluir = sum(l.get('quantity', 0) for cat in ['servicios', 'activos_fijos', 'otros_ingresos'] for l in categorizadas[cat])
total_monto_excluir = sum(l.get('credit', 0) - l.get('debit', 0) for cat in ['servicios', 'activos_fijos', 'otros_ingresos'] for l in categorizadas[cat])

print("\n" + "=" * 100)
print("📊 IMPACTO DE FILTROS ADICIONALES")
print("=" * 100)

print(f"""
Actualmente: {len(lineas_texto_libre):,} líneas texto libre

Con filtros adicionales:
   - Excluir servicios/activos/otros: -{total_excluir:,} líneas ({total_kg_excluir:,.0f} kg, ${total_monto_excluir:,.0f})
   - Mantener frutas identificables: {len(categorizadas['frutas_identificables']):,} líneas
   - Revisar basura: {len(categorizadas['basura']):,} líneas

Total a incluir: {len(categorizadas['frutas_identificables']) + len(categorizadas['basura']):,} líneas
""")

print("=" * 100)
