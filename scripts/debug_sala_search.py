
import os
from dotenv import load_dotenv
import sys

# Forzar encoding UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# Simular carga de entorno
load_dotenv()

from backend.services.produccion_service import ProduccionService

def inspect():
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    if not username or not password:
        print("Error: No se encontraron credenciales ODOO_USER/ODOO_PASSWORD")
        return

    service = ProduccionService(username=username, password=password)
    
    print("--- Buscando valores únicos de x_studio_sala_de_proceso ---")
    # Buscamos en mrp.production
    prods = service.odoo.search_read(
        'mrp.production',
        [('x_studio_sala_de_proceso', '!=', False)],
        ['x_studio_sala_de_proceso'],
        limit=100
    )
    
    salas_encontradas = set()
    for p in prods:
        salas_encontradas.add(p['x_studio_sala_de_proceso'])
    
    print(f"Salas encontradas en las últimas 100 producciones: {list(salas_encontradas)}")
    
    # Probar búsqueda ilike con 'Sala 2'
    test_search = service.odoo.search('mrp.production', [('x_studio_sala_de_proceso', 'ilike', 'Sala 2')])
    print(f"Búsqueda ilike 'Sala 2' encontró {len(test_search)} registros.")
    
    # Probar búsqueda ilike con 'Sala 2 - Linea Granel'
    test_search_full = service.odoo.search('mrp.production', [('x_studio_sala_de_proceso', 'ilike', 'Sala 2 - Linea Granel')])
    print(f"Búsqueda ilike 'Sala 2 - Linea Granel' encontró {len(test_search_full)} registros.")

if __name__ == "__main__":
    inspect()
