"""
Buscar rates de USD (la moneda extranjera)
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

client = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 100)
print("🔍 RATES DE USD (la moneda de las facturas)")
print("=" * 100)

# Buscar USD
usd_currency = client.search_read(
    "res.currency",
    [("name", "=", "USD")],
    ["id", "name"],
    limit=1
)

if usd_currency:
    usd_id = usd_currency[0]['id']
    
    # Buscar rates históricos de USD
    rates = client.search_read(
        "res.currency.rate",
        [("currency_id", "=", usd_id)],
        ["id", "name", "rate", "currency_id"],
        limit=30,
        order="name desc"
    )
    
    print(f"\nRates históricos de USD:")
    print(f"{'FECHA':<15} | {'RATE (1/TC)':>18} | {'TC (CLP/USD)':>15}")
    print("-" * 55)
    
    for r in rates:
        rate = r.get('rate', 0)
        tc = 1 / rate if rate > 0 else 0
        fecha = r.get('name', 'N/A')
        print(f"{fecha:<15} | {rate:>18.10f} | {tc:>15.2f}")
    
    print("\n" + "=" * 100)
    print("✅ AQUÍ ESTÁN LOS TCs HISTÓRICOS QUE DEBERÍAMOS USAR")
    print("=" * 100)
    
    # Comparar con nuestros cálculos
    print(f"\n📊 Comparación:")
    print(f"   • Rate del 5 Feb 2026: buscar arriba")
    print(f"   • Rate del 27 Ene 2025: buscar arriba")
    print(f"\n⚠️ PROBLEMA: Estamos usando 'debit' que se calcula con el TC de HOY")
    print(f"   SOLUCIÓN: Debemos usar estos rates históricos según la fecha del move")

print("\n" + "=" * 100)
