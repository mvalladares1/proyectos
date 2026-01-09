"""Script para verificar el estado actual del JSON en Odoo."""
import sys
sys.path.insert(0, '/app')
from shared.odoo_client import get_odoo_client
import json

odoo = get_odoo_client(username='mvp', password='mvpodoo1618')
mo = odoo.read('mrp.production', [5637], ['name', 'x_studio_pending_receptions'])[0]

print(f"Orden: {mo['name']}")
print(f"\nJSON completo:")
print(mo['x_studio_pending_receptions'][:1000] if mo['x_studio_pending_receptions'] else "NULL")

if mo['x_studio_pending_receptions']:
    data = json.loads(mo['x_studio_pending_receptions'])
    print(f"\n=== RESUMEN ===")
    print(f"Pending flag: {data.get('pending')}")
    print(f"Total pallets: {len(data.get('pallets', []))}")
    
    print(f"\n=== PALLETS ===")
    for p in data.get('pallets', []):
        estado = p.get('estado_ultima_revision', 'sin_estado')
        agregado = p.get('timestamp_agregado', None)
        print(f"  {p['codigo']}: estado={estado}, agregado={'SI' if agregado else 'NO'}")
    
    print(f"\n=== HISTORIAL (últimas 5) ===")
    historial = data.get('historial_revisiones', [])
    for h in historial[-5:]:
        print(f"  {h.get('timestamp', 'N/A')[:19]} - {h.get('accion', 'N/A')}")
