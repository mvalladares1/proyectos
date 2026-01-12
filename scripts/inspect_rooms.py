
import os
from dotenv import load_dotenv
import sys

# Forzar encoding UTF-8 para evitar errores de consola windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from backend.services.produccion_service import ProduccionService

def inspect_production_rooms():
    load_dotenv()
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    if not username or not password:
        print("ERROR: ODOO_USER or ODOO_PASSWORD not found in .env")
        return

    service = ProduccionService(username=username, password=password)
    
    print("Buscando ultimas producciones con sala asignada...")
    try:
        # Buscamos en mrp.production
        productions = service.odoo.search_read(
            'mrp.production',
            [('x_studio_sala_de_proceso', '!=', False)],
            ['name', 'x_studio_sala_de_proceso', 'date_planned_start'],
            limit=30,
            order='id desc'
        )
        
        if not productions:
            print("No se encontraron producciones con el campo x_studio_sala_de_proceso lleno.")
            # Buscar una sin filtro solo para ver los campos disponibles
            print("\nProbando buscar cualquier produccion para ver campos...")
            any_p = service.odoo.search_read('mrp.production', [], ['name'], limit=1)
            print(f"Encontrada: {any_p}")
        else:
            print("\nUltimas producciones encontradas:")
            for p in productions:
                print(f"ID: {p['id']} | Name: {p['name']} | Sala (Technical): '{p['x_studio_sala_de_proceso']}' | Fecha: {p['date_planned_start']}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    inspect_production_rooms()
