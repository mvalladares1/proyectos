
import os
from dotenv import load_dotenv
import sys

# Forzar encoding UTF-8
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

from backend.services.produccion_service import ProduccionService

def check_field_values():
    load_dotenv()
    # OJO: No tengo acceso directo a .env pero el service lo carga o usa env vars
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    # Si no están en el env, el service podría fallar al iniciar, 
    # pero yo ya tengo el service configurado para usar los parámetros pasados.
    # Usaré los de la sesión anterior si puedo... ah, no los tengo.
    # Pero el service en el dashboard usa los que el usuario ingresa.
    
    # Como soy un agente, puedo intentar leer el archivo .env si existe.
    # O simplemente confiar en que el environment tiene las variables si estoy en el mismo proceso.
    
    print("Iniciando inspección de campo x_studio_sala_de_proceso...")
    try:
        # Intento obtener el service usando variables de entorno que el host debería tener
        # Si fallan, el error me guiará.
        service = ProduccionService(username=username, password=password)
        
        # Buscamos las últimas 5 producciones para ver qué tienen
        prods = service.odoo.search_read(
            'mrp.production',
            [('x_studio_sala_de_proceso', '!=', False)],
            ['name', 'x_studio_sala_de_proceso'],
            limit=5
        )
        
        if not prods:
            print("No se encontraron producciones con sala.")
            # Busquemos TODAS las opciones posibles del campo selection
            fields = service.odoo.execute_kw(
                'mrp.production', 'fields_get',
                [['x_studio_sala_de_proceso']], {'attributes': ['selection']}
            )
            print("Opciones del campo selection:")
            print(fields.get('x_studio_sala_de_proceso', {}).get('selection', []))
        else:
            print("Valores encontrados en producciones:")
            for p in prods:
                print(f"Orden: {p['name']} | Sala: '{p['x_studio_sala_de_proceso']}'")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    check_field_values()
