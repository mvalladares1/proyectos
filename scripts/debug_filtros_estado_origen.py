"""
DEBUG: Verificar filtros de Estado y Origen en Recepciones y Produccion
Objetivo: Asegurar que los filtros funcionan correctamente cuando se combinan

ESCENARIOS A PROBAR:
1. Recepciones: Origen=Vilkun + Estado=assigned (En Proceso)
2. Recepciones: Origen=Vilkun + Estado=done (Hecho)
3. Produccion: Planta=Vilkun + Estado=progress (En Progreso)
"""
import sys
import os
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

# Configuracion
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Rango de fechas (ultimos 30 dias)
FECHA_FIN = datetime.now().strftime("%Y-%m-%d")
FECHA_INICIO = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

print("=" * 140)
print("DEBUG: VERIFICACION DE FILTROS DE ESTADO Y ORIGEN")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Rango: {FECHA_INICIO} a {FECHA_FIN}")
print("=" * 140)

try:
    odoo = OdooClient(username=USERNAME, password=PASSWORD)
    print("[OK] Conexion a Odoo establecida\n")
except Exception as e:
    print(f"[ERROR] Error al conectar a Odoo: {e}")
    sys.exit(1)

# === CONSTANTES ===
ORIGEN_PICKING_MAP = {
    "RFP": 1,
    "VILKUN": 217,
    "SAN JOSE": 164
}

ESTADOS_RECEPCION = {
    "draft": "Borrador",
    "waiting": "Esperando otra operacion",
    "confirmed": "Esperando",
    "assigned": "Listo (En Proceso)",
    "done": "Hecho",
    "cancel": "Cancelado"
}

# =============================================================================
# TEST 1: RECEPCIONES - Verificar conteo por origen y estado
# =============================================================================
print("\n" + "=" * 140)
print("TEST 1: RECEPCIONES - CONTEO POR ORIGEN Y ESTADO")
print("=" * 140)

print("\n[INFO] Consultando TODAS las recepciones de MP en el rango...\n")

# Query base para recepciones
base_domain = [
    ("x_studio_categora_de_producto", "=", "MP"),
    ("scheduled_date", ">=", FECHA_INICIO),
    ("scheduled_date", "<=", FECHA_FIN),
]

# Para cada origen, contar por estado
for origen, picking_type_id in ORIGEN_PICKING_MAP.items():
    print(f"\n--- ORIGEN: {origen} (picking_type_id={picking_type_id}) ---")
    
    for state, state_label in ESTADOS_RECEPCION.items():
        domain = base_domain + [
            ("picking_type_id", "=", picking_type_id),
            ("state", "=", state)
        ]
        
        count = odoo.search(
            "stock.picking",
            domain,
            limit=1
        )
        
        # search devuelve lista de IDs, necesitamos search_count o len
        recepciones = odoo.search_read(
            "stock.picking",
            domain,
            ["id", "name", "state", "scheduled_date"],
            limit=5000
        )
        
        n = len(recepciones)
        if n > 0:
            print(f"   {state_label:<25} ({state:<10}): {n:>5} recepciones")
            # Mostrar primeras 3 como ejemplo
            for r in recepciones[:3]:
                print(f"      -> {r['name']} | fecha: {str(r.get('scheduled_date', ''))[:10]}")

# =============================================================================
# TEST 2: RECEPCIONES - Test especifico de filtro combinado
# =============================================================================
print("\n\n" + "=" * 140)
print("TEST 2: RECEPCIONES - FILTRO COMBINADO (Vilkun + assigned)")
print("=" * 140)

test_domain = [
    ("picking_type_id", "=", 217),  # VILKUN
    ("x_studio_categora_de_producto", "=", "MP"),
    ("scheduled_date", ">=", FECHA_INICIO),
    ("scheduled_date", "<=", FECHA_FIN),
    ("state", "=", "assigned")  # En Proceso
]

recepciones_vilkun_assigned = odoo.search_read(
    "stock.picking",
    test_domain,
    ["id", "name", "state", "scheduled_date", "partner_id"],
    limit=100
)

print(f"\n[RESULTADO] Recepciones Vilkun en estado 'assigned': {len(recepciones_vilkun_assigned)}")
if recepciones_vilkun_assigned:
    print("\nPrimeras 10:")
    print(f"{'Nombre':<25} {'Estado':<15} {'Fecha':<12} {'Productor':<40}")
    print("-" * 100)
    for r in recepciones_vilkun_assigned[:10]:
        partner = r.get('partner_id')
        partner_name = partner[1][:38] if isinstance(partner, (list, tuple)) else ''
        print(f"{r['name']:<25} {r['state']:<15} {str(r.get('scheduled_date', ''))[:10]:<12} {partner_name:<40}")
else:
    print("[!] No se encontraron recepciones. Esto podria ser correcto si no hay datos.")

# =============================================================================
# TEST 3: PRODUCCION - Verificar filtro de planta Vilkun
# =============================================================================
print("\n\n" + "=" * 140)
print("TEST 3: PRODUCCION - ORDENES DE FABRICACION CON NOMBRE VLK")
print("=" * 140)

# Buscar MOs que empiezan con VLK (Vilkun)
mos_vilkun = odoo.search_read(
    "mrp.production",
    [
        ("name", "ilike", "VLK%"),
        ("date_planned_start", ">=", FECHA_INICIO),
        ("date_planned_start", "<=", FECHA_FIN),
    ],
    ["id", "name", "state", "date_planned_start", "product_id"],
    limit=100
)

print(f"\n[RESULTADO] MOs con nombre 'VLK*': {len(mos_vilkun)}")

# Agrupar por estado
estados_mo = {}
for mo in mos_vilkun:
    state = mo.get('state', 'unknown')
    if state not in estados_mo:
        estados_mo[state] = []
    estados_mo[state].append(mo)

print("\nDistribucion por estado:")
for state, mos in sorted(estados_mo.items()):
    print(f"   {state:<15}: {len(mos):>5} MOs")
    for mo in mos[:2]:
        print(f"      -> {mo['name']}")

# =============================================================================
# TEST 4: PRODUCCION - Todas las MOs por estado
# =============================================================================
print("\n\n" + "=" * 140)
print("TEST 4: PRODUCCION - TODAS LAS MOS POR ESTADO (sin filtro planta)")
print("=" * 140)

ESTADOS_MO = {
    'draft': 'Borrador',
    'confirmed': 'Confirmado',
    'progress': 'En Progreso',
    'to_close': 'Por Cerrar',
    'done': 'Hecho',
    'cancel': 'Cancelado'
}

for state, label in ESTADOS_MO.items():
    mos = odoo.search_read(
        "mrp.production",
        [
            ("date_planned_start", ">=", FECHA_INICIO),
            ("date_planned_start", "<=", FECHA_FIN),
            ("state", "=", state)
        ],
        ["id", "name"],
        limit=5000
    )
    
    # Contar cuantas son VLK
    mos_vlk = [mo for mo in mos if mo.get('name', '').upper().startswith('VLK')]
    mos_rfp = [mo for mo in mos if not mo.get('name', '').upper().startswith('VLK')]
    
    print(f"\n{label:<15} ({state:<10}): Total={len(mos):>4} | VLK={len(mos_vlk):>4} | RFP={len(mos_rfp):>4}")

# =============================================================================
# TEST 5: Verificar si el API endpoint respeta los filtros
# =============================================================================
print("\n\n" + "=" * 140)
print("TEST 5: LLAMADA DIRECTA AL SERVICIO DE RECEPCIONES")
print("=" * 140)

try:
    # Importar el servicio directamente
    from backend.services.recepcion_service import get_recepciones_mp
    
    print("\n[PRUEBA 1] Origen=VILKUN, Estados=None (solo done por defecto)")
    result1 = get_recepciones_mp(
        username=USERNAME,
        password=PASSWORD,
        fecha_inicio=FECHA_INICIO,
        fecha_fin=FECHA_FIN,
        origen=["VILKUN"],
        estados=None,
        solo_hechas=True
    )
    print(f"   Resultado: {len(result1)} recepciones")
    if result1:
        estados_result = {}
        for r in result1:
            s = r.get('state', 'unknown')
            estados_result[s] = estados_result.get(s, 0) + 1
        print(f"   Por estado: {estados_result}")
    
    print("\n[PRUEBA 2] Origen=VILKUN, Estados=['assigned']")
    result2 = get_recepciones_mp(
        username=USERNAME,
        password=PASSWORD,
        fecha_inicio=FECHA_INICIO,
        fecha_fin=FECHA_FIN,
        origen=["VILKUN"],
        estados=["assigned"]
    )
    print(f"   Resultado: {len(result2)} recepciones")
    if result2:
        estados_result = {}
        for r in result2:
            s = r.get('state', 'unknown')
            estados_result[s] = estados_result.get(s, 0) + 1
        print(f"   Por estado: {estados_result}")
    
    print("\n[PRUEBA 3] Origen=VILKUN, Estados=['assigned', 'done']")
    result3 = get_recepciones_mp(
        username=USERNAME,
        password=PASSWORD,
        fecha_inicio=FECHA_INICIO,
        fecha_fin=FECHA_FIN,
        origen=["VILKUN"],
        estados=["assigned", "done"]
    )
    print(f"   Resultado: {len(result3)} recepciones")
    if result3:
        estados_result = {}
        for r in result3:
            s = r.get('state', 'unknown')
            estados_result[s] = estados_result.get(s, 0) + 1
        print(f"   Por estado: {estados_result}")

except ImportError as e:
    print(f"[ERROR] No se pudo importar servicio: {e}")
except Exception as e:
    print(f"[ERROR] Error ejecutando servicio: {e}")

print("\n" + "=" * 140)
print("DEBUG COMPLETADO")
print("=" * 140)
print("""
CONCLUSIONES:
- Si TEST 1 muestra recepciones en diferentes estados por origen, los datos existen
- Si TEST 2 muestra 0 pero TEST 1 muestra datos en 'assigned' para Vilkun, hay problema de filtro
- Si TEST 5 muestra diferencias entre PRUEBA 1, 2, 3, el servicio funciona correctamente
- Si TEST 5 muestra el mismo resultado, el filtro de estados no esta funcionando

POSIBLES PROBLEMAS:
1. El frontend no pasa correctamente el parametro 'estados'
2. El cache esta devolviendo datos antiguos
3. El filtro de origen override esta afectando resultados
""")
