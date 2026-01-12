
import os
from dotenv import load_dotenv
from backend.services.produccion_service import ProduccionService

def get_unique_rooms():
    load_dotenv()
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    if not username or not password:
        print("❌ Error: ODOO_USER or ODOO_PASSWORD not found in .env")
        return

    service = ProduccionService(username=username, password=password)
    
    # Vamos a buscar en los últimos 60 días para tener una buena muestra
    from datetime import datetime, timedelta
    fecha_fin = datetime.now().strftime("%Y-%m-%d")
    fecha_inicio = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
    
    print(f"Buscando salas únicas entre {fecha_inicio} y {fecha_fin}...")
    
    try:
        # Buscamos registros de mrp.production en el periodo
        domain = [
            ('date_planned_start', '>=', fecha_inicio + ' 00:00:00'),
            ('date_planned_start', '<=', fecha_fin + ' 23:59:59')
        ]
        
        productions = service.odoo.search_read(
            'mrp.production',
            domain,
            ['x_studio_sala_de_proceso']
        )
        
        salas = set()
        for p in productions:
            sala = p.get('x_studio_sala_de_proceso')
            if sala:
                salas.add(sala.strip())
        
        if not salas:
            print("No se encontraron salas registradas en este periodo.")
        else:
            print("\nSalas encontradas en los últimos 60 días:")
            for s in sorted(list(salas)):
                print(f"- {s}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    get_unique_rooms()
