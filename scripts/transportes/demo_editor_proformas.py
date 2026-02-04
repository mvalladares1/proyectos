"""
Demo del Editor de Proformas con Datos Faltantes
Simula la interfaz y funcionalidad del editor
"""

import pandas as pd
from datetime import datetime

# Datos de prueba con problemas realistas
datos_ocs = [
    {
        'OC': 'PO00123',
        'Fecha': '2026-01-15',
        'Transportista': 'TRANSPORTES RODRIGUEZ LIMITADA',
        'Ruta': 'Sin ruta',  # ❌ Problema
        'Kms': 0,  # ❌ Problema
        'Kilos': 0,  # ❌ Problema
        'Costo': 225000,
        'Tipo Camión': 'N/A'  # ❌ Problema
    },
    {
        'OC': 'PO00145',
        'Fecha': '2026-01-20',
        'Transportista': 'TRANSPORTES PEREZ SPA',
        'Ruta': 'Temuco - La Granja',  # ✅ OK
        'Kms': 680,  # ✅ OK
        'Kilos': 18000,  # ✅ OK
        'Costo': 340000,  # ✅ OK
        'Tipo Camión': 'N/A'  # ❌ Problema
    },
    {
        'OC': 'PO00167',
        'Fecha': '2026-01-28',
        'Transportista': 'TRANSPORTES GOMEZ Y CIA',
        'Ruta': 'Curicó - La Granja',  # ✅ OK
        'Kms': 0,  # ❌ Problema
        'Kilos': 9000,  # ✅ OK
        'Costo': 0,  # ❌ Problema
        'Tipo Camión': '🚚 Camión 8 Ton'  # ✅ OK
    },
    {
        'OC': 'PO00189',
        'Fecha': '2026-01-30',
        'Transportista': 'TRANSPORTES RODRIGUEZ LIMITADA',
        'Ruta': 'San José - La Granja',  # ✅ OK
        'Kms': 450,  # ✅ OK
        'Kilos': 12500,  # ✅ OK
        'Costo': 225000,  # ✅ OK
        'Tipo Camión': '🚛 Camión 12-14 Ton'  # ✅ OK
    },
    {
        'OC': 'PO00201',
        'Fecha': '2026-02-01',
        'Transportista': 'TRANSPORTES PEREZ SPA',
        'Ruta': '',  # ❌ Problema (vacío)
        'Kms': 320,  # ✅ OK
        'Kilos': 0,  # ❌ Problema
        'Costo': 160000,  # ✅ OK
        'Tipo Camión': 'N/A'  # ❌ Problema
    }
]

def detectar_datos_faltantes(df_data):
    """Detecta OCs con datos faltantes o incompletos"""
    problemas = []
    for idx, row in df_data.iterrows():
        issues = []
        if not row['Ruta'] or row['Ruta'] == 'Sin ruta':
            issues.append('Ruta')
        if row['Kms'] == 0 or pd.isna(row['Kms']):
            issues.append('Kms')
        if row['Kilos'] == 0 or pd.isna(row['Kilos']):
            issues.append('Kilos')
        if row['Costo'] == 0 or pd.isna(row['Costo']):
            issues.append('Costo')
        if not row['Tipo Camión'] or row['Tipo Camión'] == 'N/A':
            issues.append('Tipo Camión')
        
        if issues:
            problemas.append({
                'indice': idx,
                'oc': row['OC'],
                'transportista': row['Transportista'],
                'campos_faltantes': issues
            })
    return problemas

# Crear DataFrame
df = pd.DataFrame(datos_ocs)

# Calcular $/km
df['$/km'] = df.apply(
    lambda row: (row['Costo'] / row['Kms']) if row['Kms'] > 0 else 0,
    axis=1
)

# Detectar problemas
problemas = detectar_datos_faltantes(df)

# Añadir columna de estado
df['Estado'] = df.apply(
    lambda row: '⚠️ Incompleto' if any(
        p['oc'] == row['OC'] for p in problemas
    ) else '✅ Completo',
    axis=1
)

print("=" * 100)
print("DEMO: EDITOR DE PROFORMAS CON DETECCIÓN DE DATOS FALTANTES")
print("=" * 100)

print(f"\n📊 RESUMEN GENERAL:")
print(f"   Total OCs: {len(df)}")
print(f"   OCs completas: {len(df[df['Estado'] == '✅ Completo'])}")
print(f"   OCs incompletas: {len(df[df['Estado'] == '⚠️ Incompleto'])}")

print(f"\n⚠️ Se detectaron {len(problemas)} OCs con datos incompletos:")
print("-" * 100)

for problema in problemas:
    print(f"\n{problema['oc']} - {problema['transportista']}")
    print(f"  ❌ Faltan datos de: {', '.join(problema['campos_faltantes'])}")

print("\n" + "=" * 100)
print("TABLA DE DATOS ACTUAL (antes de editar)")
print("=" * 100)

# Mostrar tabla
print(df[['Estado', 'OC', 'Transportista', 'Ruta', 'Kms', 'Kilos', 'Costo', '$/km', 'Tipo Camión']].to_string(index=False))

print("\n" + "=" * 100)
print("EJEMPLO DE CORRECCIÓN - OC PO00123")
print("=" * 100)

print("\n🔴 ANTES (datos incompletos):")
oc_antes = df[df['OC'] == 'PO00123'].iloc[0]
print(f"   Ruta: {oc_antes['Ruta']} ❌")
print(f"   Kms: {oc_antes['Kms']} ❌")
print(f"   Kilos: {oc_antes['Kilos']} ❌")
print(f"   Costo: ${oc_antes['Costo']:,.0f}")
print(f"   Tipo Camión: {oc_antes['Tipo Camión']} ❌")
print(f"   $/km: ${oc_antes['$/km']:.0f}")
print(f"   Estado: {oc_antes['Estado']}")

# Simular edición
df.loc[df['OC'] == 'PO00123', 'Ruta'] = 'San José - La Granja'
df.loc[df['OC'] == 'PO00123', 'Kms'] = 450
df.loc[df['OC'] == 'PO00123', 'Kilos'] = 12500
df.loc[df['OC'] == 'PO00123', 'Tipo Camión'] = '🚛 Camión 12-14 Ton'

# Recalcular $/km
df.loc[df['OC'] == 'PO00123', '$/km'] = df.loc[df['OC'] == 'PO00123', 'Costo'] / df.loc[df['OC'] == 'PO00123', 'Kms']

# Actualizar estado
df.loc[df['OC'] == 'PO00123', 'Estado'] = '✅ Completo'

print("\n🟢 DESPUÉS (datos corregidos):")
oc_despues = df[df['OC'] == 'PO00123'].iloc[0]
print(f"   Ruta: {oc_despues['Ruta']} ✅")
print(f"   Kms: {oc_despues['Kms']:.0f} ✅")
print(f"   Kilos: {oc_despues['Kilos']:.1f} ✅")
print(f"   Costo: ${oc_despues['Costo']:,.0f} ✅")
print(f"   Tipo Camión: {oc_despues['Tipo Camión']} ✅")
print(f"   $/km: ${oc_despues['$/km']:.0f} (auto-calculado)")
print(f"   Estado: {oc_despues['Estado']}")

print("\n" + "=" * 100)
print("TABLA ACTUALIZADA (después de correcciones)")
print("=" * 100)

# Re-detectar problemas
problemas_nuevos = detectar_datos_faltantes(df)
print(f"\n⚠️ Quedan {len(problemas_nuevos)} OCs con datos incompletos\n")

print(df[['Estado', 'OC', 'Transportista', 'Ruta', 'Kms', 'Kilos', 'Costo', '$/km', 'Tipo Camión']].to_string(index=False))

print("\n" + "=" * 100)
print("VISTA PREVIA DEL PDF - CONSOLIDADO POR TRANSPORTISTA")
print("=" * 100)

# Agrupar por transportista
for transportista in df['Transportista'].unique():
    ocs_transp = df[df['Transportista'] == transportista]
    
    print(f"\n🚛 {transportista}")
    print(f"   {len(ocs_transp)} OCs | {ocs_transp['Kms'].sum():,.0f} km | {ocs_transp['Kilos'].sum():,.1f} kg | ${ocs_transp['Costo'].sum():,.0f}")
    print("   " + "-" * 90)
    
    for _, row in ocs_transp.iterrows():
        estado_emoji = '✅' if row['Estado'] == '✅ Completo' else '⚠️'
        print(f"   {estado_emoji} {row['OC']} | {row['Fecha']} | {row['Ruta'][:30]:30s} | {row['Kms']:4.0f} km | {row['Kilos']:8.1f} kg | ${row['Costo']:8,.0f} | {row['Tipo Camión']}")

print("\n" + "=" * 100)
print("RECOMENDACIONES")
print("=" * 100)

print("\n📋 OCs que aún necesitan corrección:")
for problema in problemas_nuevos:
    print(f"\n   {problema['oc']} ({problema['transportista']})")
    print(f"      Campos faltantes: {', '.join(problema['campos_faltantes'])}")
    
    # Sugerencias específicas
    oc_data = df[df['OC'] == problema['oc']].iloc[0]
    print(f"      Sugerencias:")
    if 'Ruta' in problema['campos_faltantes']:
        print(f"         • Ruta: Consulta guía de despacho o pregunta al transportista")
    if 'Kms' in problema['campos_faltantes']:
        if oc_data['Costo'] > 0:
            kms_sugeridos = oc_data['Costo'] / 500  # Asumiendo $500/km
            print(f"         • Kms: Si costo es ${oc_data['Costo']:,.0f} y $/km promedio es $500, serían aprox {kms_sugeridos:.0f} km")
    if 'Kilos' in problema['campos_faltantes']:
        print(f"         • Kilos: Revisar guía de despacho o nota de peso")
    if 'Costo' in problema['campos_faltantes']:
        if oc_data['Kms'] > 0:
            costo_sugerido = oc_data['Kms'] * 500  # Asumiendo $500/km
            print(f"         • Costo: Si distancia es {oc_data['Kms']:.0f} km y $/km promedio es $500, sería aprox ${costo_sugerido:,.0f}")
    if 'Tipo Camión' in problema['campos_faltantes']:
        print(f"         • Tipo Camión: Pregunta al transportista qué tipo de vehículo usó")

print("\n" + "=" * 100)
print("✅ El sistema está listo para generar PDF con los datos disponibles")
print("⚠️ Recomendación: Completa todos los datos antes de enviar para mayor profesionalismo")
print("=" * 100)

# Guardar CSV de ejemplo
filename = f"ejemplo_ocs_para_editar_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
df.to_csv(filename, index=False, encoding='utf-8-sig')
print(f"\n💾 Datos guardados en: {filename}")
print("   Puedes usar este CSV como referencia de qué datos completar\n")
