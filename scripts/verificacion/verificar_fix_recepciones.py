"""
Script de verificación: Comprobar que las correcciones funcionan correctamente
- RF/RFP/IN/00507 no debe aparecer (cancelada)
- RF/RFP/IN/01045 debe mostrar kg netos (después de devolución)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.recepcion_service import get_recepciones_mp

# Credenciales
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

print("=" * 100)
print("VERIFICACIÓN DE CORRECCIONES EN RECEPCIONES")
print("=" * 100)

# Obtener recepciones del período que incluye las problemáticas
print("\n🔍 Buscando recepciones del 20/12/2025 al 05/01/2026...")
recepciones = get_recepciones_mp(
    username=username,
    password=password,
    fecha_inicio="2025-12-20",
    fecha_fin="2026-01-05",
    solo_hechas=False,  # Incluir todos los estados para verificar filtrado
    origen=None
)

print(f"\n✅ Se obtuvieron {len(recepciones)} recepciones")

# Verificar que RF/RFP/IN/00507 NO aparece
print("\n" + "=" * 100)
print("VERIFICACIÓN 1: RF/RFP/IN/00507 (Cancelada)")
print("=" * 100)

encontrada_507 = None
for r in recepciones:
    if r.get('albaran') == 'RF/RFP/IN/00507':
        encontrada_507 = r
        break

if encontrada_507:
    print("❌ ERROR: RF/RFP/IN/00507 APARECE en los resultados")
    print(f"   Estado: {encontrada_507.get('state')}")
    print(f"   Kg: {encontrada_507.get('kg_recepcionados')}")
    print("   Debería estar filtrada por state='cancel'")
else:
    print("✅ CORRECTO: RF/RFP/IN/00507 NO aparece en los resultados")
    print("   La recepción cancelada está correctamente filtrada")

# Verificar que RF/RFP/IN/01045 muestra kg netos
print("\n" + "=" * 100)
print("VERIFICACIÓN 2: RF/RFP/IN/01045 (Con devolución)")
print("=" * 100)

encontrada_1045 = None
for r in recepciones:
    if r.get('albaran') == 'RF/RFP/IN/01045':
        encontrada_1045 = r
        break

if encontrada_1045:
    kg_mostrados = encontrada_1045.get('kg_recepcionados', 0)
    print(f"✅ ENCONTRADA: RF/RFP/IN/01045")
    print(f"   Kg mostrados: {kg_mostrados:.2f} kg")
    print(f"   Estado: {encontrada_1045.get('state')}")
    print(f"   Productor: {encontrada_1045.get('productor')}")
    print(f"   Guía: {encontrada_1045.get('guia_despacho')}")
    
    # Verificar productos
    productos = encontrada_1045.get('productos', [])
    print(f"\n   Productos ({len(productos)}):")
    for p in productos:
        categoria = p.get('Categoria', '')
        if 'BANDEJ' not in categoria.upper():  # Solo productos tipo fruta
            print(f"      - {p.get('Producto', 'N/A')}")
            print(f"        Kg Netos: {p.get('Kg Hechos', 0):.2f} kg")
            print(f"        Costo Unitario: ${p.get('Costo Unitario', 0):,.2f}")
            print(f"        Costo Total: ${p.get('Costo Total', 0):,.2f}")
    
    print("\n   ANÁLISIS:")
    # Valores esperados según debug (solo producto fruta, sin bandejas)
    kg_esperados_min = 1670  # Aproximado
    kg_esperados_max = 1680
    
    if kg_esperados_min <= kg_mostrados <= kg_esperados_max:
        print(f"   ✅ Kg mostrados están en el rango esperado (1673.25 kg netos aprox)")
        print(f"      Recepción: ~2745.55 kg")
        print(f"      Devolución: ~1072.30 kg")
        print(f"      Neto: ~1673.25 kg")
    elif kg_mostrados > 2700:
        print(f"   ❌ ERROR: Kg mostrados son los brutos (sin restar devolución)")
        print(f"      Se esperaban ~1673.25 kg netos")
        print(f"      Se muestran {kg_mostrados:.2f} kg (kg brutos)")
    else:
        print(f"   ⚠️  ADVERTENCIA: Kg mostrados fuera del rango esperado")
        print(f"      Se esperaban ~1673.25 kg netos")
        print(f"      Se muestran {kg_mostrados:.2f} kg")
else:
    print("⚠️  RF/RFP/IN/01045 NO encontrada en los resultados")
    print("   Verificar rango de fechas o estado")

# Buscar otras recepciones del mismo productor para contexto
print("\n" + "=" * 100)
print("CONTEXTO: Otras recepciones de AGRÍCOLA TRES ROBLES en el período")
print("=" * 100)

tres_robles = [r for r in recepciones if 'TRES ROBLES' in r.get('productor', '').upper()]
print(f"\nSe encontraron {len(tres_robles)} recepciones de AGRÍCOLA TRES ROBLES:")

for r in tres_robles[:10]:  # Mostrar primeras 10
    albaran = r.get('albaran', 'N/A')
    fecha = r.get('fecha', 'N/A')[:10] if r.get('fecha') else 'N/A'
    kg = r.get('kg_recepcionados', 0)
    guia = r.get('guia_despacho', 'N/A')
    estado = r.get('state', 'N/A')
    
    # Marcar las problemáticas
    marca = ""
    if albaran == 'RF/RFP/IN/00507':
        marca = " ⚠️  [CANCELADA - NO DEBERÍA APARECER]"
    elif albaran == 'RF/RFP/IN/01045':
        marca = " 📌 [CON DEVOLUCIÓN]"
    
    print(f"   {albaran:20} | {fecha} | {kg:8.2f} kg | Guía: {str(guia):10} | {estado:10}{marca}")

print("\n" + "=" * 100)
print("FIN DE VERIFICACIÓN")
print("=" * 100)

print("\n📋 RESUMEN:")
print(f"   Total recepciones en período: {len(recepciones)}")
print(f"   RF/RFP/IN/00507 filtrada: {'✅ SÍ' if not encontrada_507 else '❌ NO'}")
if encontrada_1045:
    kg = encontrada_1045.get('kg_recepcionados', 0)
    kg_ok = 1670 <= kg <= 1680
    print(f"   RF/RFP/IN/01045 kg netos: {'✅ SÍ' if kg_ok else '❌ NO'} ({kg:.2f} kg)")
else:
    print(f"   RF/RFP/IN/01045 encontrada: ❌ NO")
