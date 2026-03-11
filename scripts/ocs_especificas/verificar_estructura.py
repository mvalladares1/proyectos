"""
Verificador de Estructura del Sistema OCs
==========================================

Verifica que todos los archivos y directorios estén correctamente organizados.

Autor: Sistema de Corrección OCs
Fecha: 11 de Marzo, 2026
"""

import os
from pathlib import Path

def verificar_estructura():
    """Verifica la estructura del proyecto"""
    
    print("=" * 70)
    print("🔍 VERIFICACIÓN DE ESTRUCTURA - Sistema de Corrección OCs")
    print("=" * 70)
    print()
    
    # Directorio base
    base_dir = Path(__file__).parent
    
    # Estructura esperada
    estructura = {
        'docs': {
            'archivos': [
                'README.md',
                'GUIA_RAPIDA.md',
                'FLUJO_CORRECCION_OCS.md'
            ]
        },
        'templates': {
            'archivos': [
                'TEMPLATE_1_analizar_oc.py',
                'TEMPLATE_2_corregir_oc_cadena.py'
            ]
        },
        'utils': {
            'archivos': [
                'verificar_propagacion_precios.py',
                'verificar_estado_general.py',
                'REPORTE_COMPLETO_ocs_corregidas.py',
                'leer_check1_check2_completo.py'
            ]
        },
        'ejecuciones': {
            'tipo': 'scripts de ejecución',
            'patron': 'EJECUTAR_*.py'
        },
        'analisis': {
            'tipo': 'scripts de análisis',
            'patron': 'analizar_*.py'
        }
    }
    
    archivos_raiz = ['README.md', 'INDICE.md']
    
    # Verificar archivos raíz
    print("📋 ARCHIVOS EN RAÍZ:")
    print("-" * 70)
    for archivo in archivos_raiz:
        path = base_dir / archivo
        if path.exists():
            size = path.stat().st_size / 1024  # KB
            print(f"  ✅ {archivo:<30} ({size:.1f} KB)")
        else:
            print(f"  ❌ {archivo:<30} [FALTANTE]")
    print()
    
    # Verificar directorios y archivos
    total_archivos = 0
    total_directorios = 0
    
    for directorio, config in estructura.items():
        dir_path = base_dir / directorio
        
        print(f"📁 {directorio.upper()}:")
        print("-" * 70)
        
        if not dir_path.exists():
            print(f"  ❌ Directorio no existe")
            continue
        
        total_directorios += 1
        
        # Si tiene lista específica de archivos
        if 'archivos' in config:
            for archivo in config['archivos']:
                file_path = dir_path / archivo
                if file_path.exists():
                    size = file_path.stat().st_size / 1024
                    print(f"  ✅ {archivo:<40} ({size:.1f} KB)")
                    total_archivos += 1
                else:
                    print(f"  ❌ {archivo:<40} [FALTANTE]")
        
        # Si es un directorio con patrón (ejecuciones, analisis)
        elif 'patron' in config:
            archivos = list(dir_path.glob('*.py'))
            print(f"  📊 Archivos encontrados: {len(archivos)}")
            total_archivos += len(archivos)
            
            # Mostrar primeros 5
            for archivo in sorted(archivos)[:5]:
                size = archivo.stat().st_size / 1024
                print(f"     • {archivo.name:<40} ({size:.1f} KB)")
            
            if len(archivos) > 5:
                print(f"     ... y {len(archivos) - 5} más")
        
        print()
    
    # Resumen
    print("=" * 70)
    print("📊 RESUMEN:")
    print("-" * 70)
    print(f"  Directorios verificados:  {total_directorios}/5")
    print(f"  Archivos encontrados:     {total_archivos}")
    print(f"  Estado:                   {'✅ CORRECTO' if total_directorios == 5 else '❌ REVISAR'}")
    print("=" * 70)
    print()
    
    # Verificar que README.md tiene enlace a INDICE.md
    readme_path = base_dir / 'README.md'
    if readme_path.exists():
        contenido = readme_path.read_text(encoding='utf-8')
        tiene_indice = 'INDICE.md' in contenido or 'ÍNDICE' in contenido
        
        print("🔗 ENLACES:")
        print("-" * 70)
        print(f"  README.md → INDICE.md:    {'✅' if tiene_indice else '❌'}")
        print("=" * 70)
        print()
    
    # Guía rápida
    print("🚀 PRÓXIMOS PASOS:")
    print("-" * 70)
    print("  1. Consultar guía rápida: docs/GUIA_RAPIDA.md")
    print("  2. Ver índice completo:   INDICE.md")
    print("  3. Copiar templates:      templates/TEMPLATE_*.py")
    print("=" * 70)

if __name__ == '__main__':
    verificar_estructura()
