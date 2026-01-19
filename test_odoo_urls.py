"""
Script para verificar el formato correcto de URLs de Odoo
"""

def test_url_format():
    # Simular la URL base de Odoo
    odoo_url = "https://riofuturo.server98c6e.oerpondemand.net"
    
    # IDs de ejemplo
    test_ids = [1234, 5678, 9999]
    
    print("=" * 80)
    print("VERIFICACIÓN DE FORMATO DE URLs DE ODOO")
    print("=" * 80)
    print()
    
    print("URLs generadas:")
    print()
    
    for item_id in test_ids:
        # Formato que estamos usando
        url = f"{odoo_url}/web#model=stock.picking&id={item_id}"
        print(f"ID {item_id}: {url}")
    
    print()
    print("=" * 80)
    print("INSTRUCCIONES PARA PROBAR:")
    print("=" * 80)
    print()
    print("1. Copia una de las URLs de arriba")
    print("2. Pégala en tu navegador (asegúrate de estar logueado en Odoo)")
    print("3. Debería abrir el formulario del picking con ese ID")
    print()
    print("Si aún hay problemas, podemos usar un formato alternativo:")
    print()
    
    # Formatos alternativos
    for item_id in test_ids:
        alt_url = f"{odoo_url}/web#menu_id=&action=&model=stock.picking&view_type=form&id={item_id}"
        print(f"Alternativa para ID {item_id}:")
        print(f"  {alt_url}")
        print()

if __name__ == "__main__":
    test_url_format()
