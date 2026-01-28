"""
Script para analizar TODOS los campos x_studio disponibles en los modelos de Odoo.
Esto nos ayudará a encontrar los nombres correctos de los campos.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

# Configurar credenciales
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 100)
print("ANÁLISIS COMPLETO DE CAMPOS X_STUDIO EN ODOO")
print("=" * 100)

# Conectar a Odoo
print("\nConectando a Odoo...")
odoo = OdooClient(username=USERNAME, password=PASSWORD)
print("✅ Conectado exitosamente\n")

# Modelos a analizar
modelos = [
    'stock.picking',
    'product.template',
    'quality.check'
]

for modelo in modelos:
    print("=" * 100)
    print(f"MODELO: {modelo}")
    print("=" * 100)
    
    campos = odoo.execute(modelo, 'fields_get', [], {'attributes': ['string', 'type', 'relation']})
    
    # Filtrar solo campos x_studio
    campos_x_studio = {k: v for k, v in campos.items() if k.startswith('x_studio')}
    
    print(f"\nTotal de campos x_studio: {len(campos_x_studio)}\n")
    
    # Mostrar TODOS los campos x_studio ordenados alfabéticamente
    for campo, info in sorted(campos_x_studio.items()):
        tipo = info.get('type', 'unknown')
        descripcion = info.get('string', 'N/A')
        relacion = info.get('relation', '')
        
        if relacion:
            print(f"  {campo:50s} | {tipo:15s} | {descripcion:40s} | -> {relacion}")
        else:
            print(f"  {campo:50s} | {tipo:15s} | {descripcion}")
    
    print("\n")

print("=" * 100)
print("BÚSQUEDA DE CAMPOS ESPECÍFICOS")
print("=" * 100)

# Buscar campos específicos que necesitamos
palabras_clave = {
    'stock.picking': ['guia', 'despacho', 'categoria', 'tipo'],
    'product.template': ['variedad', 'calibre', 'categoria', 'manejo', 'tipo'],
    'quality.check': ['pallet', 'palet', 'clasificacion', 'calificacion', 'defecto', 'temperatura',
                      'hongos', 'inmadura', 'sobremadura', 'deshidratado', 'crumble',
                      'mecanico', 'insecto', 'deformes', 'verde', 'herida', 'partida']
}

for modelo, palabras in palabras_clave.items():
    print(f"\n{modelo}:")
    print("-" * 100)
    
    campos = odoo.execute(modelo, 'fields_get', [], {'attributes': ['string', 'type']})
    
    for palabra in palabras:
        print(f"\n  Campos con '{palabra}':")
        encontrados = {k: v for k, v in campos.items() if palabra.lower() in k.lower() or palabra.lower() in str(v.get('string', '')).lower()}
        
        if encontrados:
            for campo, info in sorted(encontrados.items()):
                descripcion = info.get('string', 'N/A')
                print(f"    - {campo:50s} | {descripcion}")
        else:
            print(f"    (ninguno)")

print("\n" + "=" * 100)
print("✅ ANÁLISIS COMPLETADO")
print("=" * 100)
