import json
import os
from pathlib import Path
from typing import List, Set

# Ruta del archivo de aprobaciones
BASE_DIR = Path(__file__).resolve().parents[2]
SHARED_DIR = BASE_DIR / "shared"
APROBACIONES_FILE = SHARED_DIR / "aprobaciones.json"

def _ensure_shared_dir():
    if not SHARED_DIR.exists():
        SHARED_DIR.mkdir(parents=True, exist_ok=True)

def get_aprobaciones() -> List[str]:
    """Retorna lista de IDs (nombres) de recepciones aprobadas."""
    _ensure_shared_dir()
    if not APROBACIONES_FILE.exists():
        return []
    
    try:
        with open(APROBACIONES_FILE, 'r') as f:
            data = json.load(f)
            return data.get("recepciones", [])
    except Exception as e:
        print(f"Error leyendo aprobaciones: {e}")
        return []

def save_aprobaciones(nuevos_ids: List[str]):
    """Guarda nuevos IDs en el archivo de aprobaciones, manteniendo los existentes."""
    _ensure_shared_dir()
    
    actuales = set(get_aprobaciones())
    actuales.update(nuevos_ids)
    
    try:
        with open(APROBACIONES_FILE, 'w') as f:
            json.dump({"recepciones": list(actuales)}, f, indent=4)
        return True
    except Exception as e:
        print(f"Error guardando aprobaciones: {e}")
        return False

def remove_aprobaciones(ids_to_remove: List[str]):
    """Elimina IDs de la lista de aprobaciones."""
    _ensure_shared_dir()
    
    actuales = set(get_aprobaciones())
    for id_rem in ids_to_remove:
        actuales.discard(id_rem)
        
    try:
        with open(APROBACIONES_FILE, 'w') as f:
            json.dump({"recepciones": list(actuales)}, f, indent=4)
        return True
    except Exception as e:
        print(f"Error eliminando aprobaciones: {e}")
        return False
