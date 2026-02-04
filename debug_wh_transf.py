"""Debug: Verificar WH/Transf/00959"""
import httpx
import json

API_URL = "http://167.114.114.51:8002"

# Buscar en mrp.production
print("=" * 60)
print("Buscando WH/Transf/00959...")
print("=" * 60)

# Necesitamos credenciales - usar las del log
params = {
    "model": "mrp.production",
    "domain": "[['name', 'ilike', 'WH/Transf/00959']]",
    "fields": "['name', 'state', 'date_finished', 'x_studio_termino_de_proceso']"
}

# También buscar en stock.picking
print("\nEste registro parece ser de stock.picking (transferencias)")
print("El monitor actual solo busca en mrp.production (órdenes de fabricación)")
print("\nPara incluir transferencias se necesita modificar el servicio")
