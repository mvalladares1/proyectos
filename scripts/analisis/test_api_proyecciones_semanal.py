import requests

url = "http://167.114.114.51:8002/api/v1/flujo-caja/semanal"
params = {
    "fecha_inicio": "2026-01-01",
    "fecha_fin": "2026-09-30",
    "username": "mvalladares@riofuturo.cl",
    "password": "c0766224bec30cac071ffe43a858c9ccbd521ddd",
    "incluir_proyecciones": True,
}

resp = requests.get(url, params=params, timeout=120)
print("status:", resp.status_code)
if resp.status_code != 200:
    print(resp.text[:600])
    raise SystemExit(1)

data = resp.json()
conceptos = data.get("actividades", {}).get("OPERACION", {}).get("conceptos", [])
concepto = next((c for c in conceptos if c.get("id") == "1.1.1"), None)
if not concepto:
    print("No se encontró 1.1.1")
    raise SystemExit(1)

print("total 1.1.1:", round(concepto.get("total", 0), 0))
cuentas = concepto.get("cuentas", [])
proj = next((c for c in cuentas if c.get("codigo") == "estado_projected"), None)
if not proj:
    print("No se encontró estado_projected")
    print("codigos:", [c.get("codigo") for c in cuentas])
    raise SystemExit(1)

print("projected total:", round(proj.get("monto", 0), 0))
weeks = proj.get("montos_por_mes", {})
non_zero = {k: v for k, v in weeks.items() if v}
print("weeks with projected:", len(non_zero))
print("sample:", list(non_zero.items())[:8])
