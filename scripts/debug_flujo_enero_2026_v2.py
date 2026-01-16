"""
Debug script v2: Incluir BORRADORES para encontrar "Leasing Tunel Continuo"
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Configuración
codigo_cuenta = "82010102"
fecha_inicio = "2026-01-01"
fecha_fin = "2026-01-31"

print("="*80)
print(f"DEBUG FLUJO ENERO 2026 - V2 (INCLUYENDO BORRADORES)")
print("="*80)

# Conectar a Odoo
print("\n1. Conectando a Odoo...")
odoo = OdooClient(
    url="https://rio-futuro-master-11821236.dev.odoo.com",
    db="rio-futuro-master-11821236",
    username="mvalladares@riofuturo.cl",
    password="c0766224bec30cac071ffe43a858c9ccbd521ddd"
)
print("   ✓ Conectado")

# 2. Obtener cuenta objetivo
print(f"\n2. Buscando cuenta {codigo_cuenta}...")
cuenta_objetivo = odoo.search_read(
    'account.account',
    [['code', '=', codigo_cuenta]],
    ['id', 'code', 'name']
)

if cuenta_objetivo:
    cuenta = cuenta_objetivo[0]
    account_id = cuenta['id']
    print(f"   ID: {account_id}")
    print(f"   Código: {cuenta['code']}")
    print(f"   Nombre: {cuenta['name']}")
else:
    print("   ERROR: No se encontró la cuenta")
    sys.exit(1)

# 3. Buscar líneas INCLUYENDO BORRADORES
print(f"\n3. Buscando líneas de {codigo_cuenta} en enero 2026 (POSTED + DRAFT)...")
lineas = odoo.models.execute_kw(
    odoo.db, odoo.uid, odoo.password,
    'account.move.line', 'search_read',
    [[
        ['account_id', '=', account_id],
        ['date', '>=', fecha_inicio],
        ['date', '<=', fecha_fin],
        ['parent_state', 'in', ['posted', 'draft']]  # 🔑 INCLUIR BORRADORES
    ]],
    {
        'fields': ['id', 'name', 'debit', 'credit', 'balance', 'date', 'move_id', 'parent_state'],
        'limit': 1000
    }
)

print(f"\n   Total líneas encontradas: {len(lineas)}")
print("\n   DETALLE DE LÍNEAS:")
print("   " + "-"*100)

etiquetas_encontradas = {}
for linea in lineas:
    etiqueta = linea.get('name', 'Sin etiqueta')
    balance = linea.get('balance', 0)
    fecha = linea.get('date', '')
    estado = linea.get('parent_state', '')
    move_id = linea.get('move_id', [None, ''])[0] if linea.get('move_id') else None
    
    print(f"   {fecha} | Estado: {estado:8s} | Balance: {balance:>12,.2f} | Etiqueta: '{etiqueta}'")
    
    # Agrupar por etiqueta
    if etiqueta not in etiquetas_encontradas:
        etiquetas_encontradas[etiqueta] = {
            'balance_total': 0,
            'count': 0,
            'estados': set()
        }
    
    etiquetas_encontradas[etiqueta]['balance_total'] += balance
    etiquetas_encontradas[etiqueta]['count'] += 1
    etiquetas_encontradas[etiqueta]['estados'].add(estado)

print("\n" + "="*80)
print("RESUMEN POR ETIQUETA:")
print("="*80)

for etiqueta, datos in sorted(etiquetas_encontradas.items(), key=lambda x: abs(x[1]['balance_total']), reverse=True):
    print(f"\nEtiqueta: '{etiqueta}'")
    print(f"  Balance total: {datos['balance_total']:>12,.2f}")
    print(f"  Cantidad líneas: {datos['count']}")
    print(f"  Estados: {', '.join(datos['estados'])}")
    
    # Verificar espacios
    if etiqueta != etiqueta.strip():
        print(f"  ⚠️ TIENE ESPACIOS: '{etiqueta}' -> '{etiqueta.strip()}'")
    
    # Limpiar con el método mejorado
    etiqueta_limpia = ' '.join(etiqueta.split())[:60]
    if etiqueta != etiqueta_limpia:
        print(f"  🧹 Limpio: '{etiqueta_limpia}'")

print("\n" + "="*80)
print(f"Total etiquetas únicas: {len(etiquetas_encontradas)}")
print("="*80)

# 4. Verificar si "Tunel Continuo" existe
tunel_encontrado = False
for etiqueta in etiquetas_encontradas.keys():
    if 'tunel' in etiqueta.lower() or 'continuo' in etiqueta.lower():
        print(f"\n✓ ENCONTRADO: '{etiqueta}'")
        tunel_encontrado = True

if not tunel_encontrado:
    print("\n✗ NO se encontró ninguna etiqueta con 'Tunel' o 'Continuo'")
else:
    print("\n✓ Confirmado: 'Leasing Tunel Continuo' SÍ existe en la cuenta 82010102")
