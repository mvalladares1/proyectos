"""
Verificar de dónde viene el TC - comparar con histórico real
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from shared.odoo_client import OdooClient
from datetime import datetime

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

client = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 120)
print("🔍 VERIFICACIÓN: ¿De dónde viene el TC?")
print("=" * 120)

# TC históricos según la imagen que compartiste
tc_historico = {
    "2026-02-05": 857.59,
    "2026-02-04": 859.53,
    "2026-02-03": 868.52,
    "2026-02-02": 865.10,
    "2026-01-05": 901.55,
    "2025-02-27": 993.83,  # Aproximado
    "2025-02-25": 994.00,  # Aproximado
    "2025-01-27": 995.83,  # Aproximado
}

# Buscar una OC antigua
oc = client.search_read(
    "purchase.order",
    [("name", "=", "P05826")],  # OC de enero 2025
    ["id", "name", "date_order", "currency_id"],
    limit=1
)[0]

print(f"\n📦 OC: {oc['name']}")
print(f"📅 Fecha OC: {oc['date_order']}")
fecha_oc = oc['date_order'][:10]

# Buscar el move asociado
moves = client.search_read(
    "account.move",
    [("invoice_origin", "like", "P05826")],
    ["id", "name", "date", "create_date", "currency_id"],
    limit=1
)

if moves:
    move = moves[0]
    print(f"📄 Move: {move['name']}")
    print(f"📅 Fecha Move: {move.get('date', 'N/A')}")
    print(f"📅 Create Date: {move.get('create_date', 'N/A')}")
    
    # Obtener líneas del move
    move_lines = client.search_read(
        "account.move.line",
        [
            ("move_id", "=", move['id']),
            ("debit", ">", 0),
            ("display_type", "=", False)
        ],
        ["id", "name", "debit", "credit", "amount_currency", "price_subtotal", "currency_id", "date"],
        limit=1
    )
    
    if move_lines:
        ml = move_lines[0]
        print(f"\n📊 Línea del Move:")
        print(f"   amount_currency (USD): {ml.get('amount_currency', 0)}")
        print(f"   price_subtotal (USD): {ml.get('price_subtotal', 0)}")
        print(f"   debit (CLP): {ml.get('debit', 0)}")
        print(f"   credit (CLP): {ml.get('credit', 0)}")
        
        usd = ml.get('price_subtotal', 0) or 0
        clp = ml.get('debit', 0) or 0
        tc_calculado = clp / usd if usd > 0 else 0
        
        print(f"\n💱 TC CALCULADO desde debit/price_subtotal: {tc_calculado:.2f}")
        print(f"💱 TC ESPERADO (del 27 ene 2025): ~995.83")
        print(f"💱 TC DE HOY (5 feb 2026): 857.59")
        
        if abs(tc_calculado - 857.59) < 1:
            print(f"\n❌ PROBLEMA CONFIRMADO: Está usando el TC de HOY, no el histórico!")
        
        # Verificar si hay un campo de TC almacenado
        print(f"\n🔍 Buscando campos de TC en account.move.line...")
        
        # Leer más campos para ver si hay TC guardado
        ml_full = client.read(
            "account.move.line",
            [ml['id']],
            ["id", "name", "debit", "price_subtotal", "amount_currency", "balance", 
             "amount_residual", "company_currency_id", "currency_id"]
        )[0]
        
        print(f"\nCampos disponibles:")
        for key, val in ml_full.items():
            if val and key not in ['id', 'name']:
                print(f"   {key}: {val}")

print("\n" + "=" * 120)
print("🔍 Buscando en res.currency.rate (tabla de TCs históricos de Odoo)")
print("=" * 120)

# Buscar rates de CLP
clp_currency = client.search_read(
    "res.currency",
    [("name", "=", "CLP")],
    ["id", "name"],
    limit=1
)

if clp_currency:
    clp_id = clp_currency[0]['id']
    
    # Buscar rates históricos
    rates = client.search_read(
        "res.currency.rate",
        [("currency_id", "=", clp_id)],
        ["id", "name", "rate", "currency_id", "company_id"],
        limit=10,
        order="name desc"
    )
    
    print(f"\nÚltimos 10 rates de CLP:")
    print(f"{'FECHA':<15} | {'RATE':>15}")
    print("-" * 35)
    for r in rates:
        print(f"{r.get('name', 'N/A'):<15} | {r.get('rate', 0):>15.10f}")
    
    print(f"\n⚠️ El 'rate' en Odoo es 1/TC (inverso)")
    print(f"   Ejemplo: si rate = 0.001165, entonces TC = 1/0.001165 = 858.37")

print("\n" + "=" * 120)
