import json, sys, urllib.request

url = "http://localhost:8002/api/v1/flujo-caja/mensual?fecha_inicio=2026-01-01&fecha_fin=2026-01-31&username=admin&password=admin&vista=semanal"
data = json.loads(urllib.request.urlopen(url).read())

for c in data.get("conceptos", []):
    if c.get("id") == "1.1.1":
        for cu in c.get("cuentas", []):
            nombre = cu.get("nombre", "")
            if "Pagad" in nombre or "Parcial" in nombre:
                print(f"\n=== {nombre} ===")
                print(f"  monto total: {cu.get('monto', 0):,.0f}")
                for etq in cu.get("etiquetas", []):
                    if etq.get("tipo") == "categoria":
                        for se in etq.get("sub_etiquetas", []):
                            n = se.get("nombre", "")
                            if "TRONADOR" in n.upper():
                                print(f"  {n}: monto={se.get('monto', 0):,.0f}")
                                for p, v in sorted(se.get("periodos", {}).items()):
                                    if v != 0:
                                        print(f"    {p}: {v:,.0f}")
