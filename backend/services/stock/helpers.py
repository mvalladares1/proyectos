"""
Funciones auxiliares para el módulo de Stock.
Incluye detección de tipo de fruta (DRY - evitar duplicación).
"""
from typing import Dict, Optional

from .constants import CATEGORIAS_EXCLUIDAS


def detect_fruit_type(prod_name: str, cat_name: str = "") -> str:
    """
    Detecta el tipo de fruta basado en nombre del producto y categoría.
    
    Args:
        prod_name: Nombre del producto (se convertirá a mayúsculas)
        cat_name: Nombre de categoría (se convertirá a mayúsculas)
        
    Returns:
        Tipo de fruta: Arándano, Frambuesa, Frutilla, Mora, Cereza, Mix, o Otro
    """
    prod_upper = prod_name.upper() if prod_name else ""
    cat_upper = cat_name.upper() if cat_name else ""
    
    # Primero buscar por código de producto (AR, FB, FR, FT, MO, CR, MIX)
    if " AR " in f" {prod_upper} " or "AR_" in prod_upper or prod_upper.startswith("AR ") or "ARANDANO" in prod_upper or "ARÁNDANO" in prod_upper or "ARANDANO" in cat_upper:
        return "Arándano"
    elif " FB " in f" {prod_upper} " or "FB_" in prod_upper or prod_upper.startswith("FB ") or "FRAMBUESA" in prod_upper or "FRAMBUESA" in cat_upper:
        return "Frambuesa"
    elif " FR " in f" {prod_upper} " or "FR_" in prod_upper or prod_upper.startswith("FR ") or " FT " in f" {prod_upper} " or "FT_" in prod_upper or prod_upper.startswith("FT ") or "FRUTILLA" in prod_upper or "FRUTILLA" in cat_upper:
        return "Frutilla"
    elif " MO " in f" {prod_upper} " or "MO_" in prod_upper or prod_upper.startswith("MO ") or "MORA" in prod_upper or "MORA" in cat_upper:
        return "Mora"
    elif " CR " in f" {prod_upper} " or "CR_" in prod_upper or prod_upper.startswith("CR ") or "CEREZA" in prod_upper or "CEREZA" in cat_upper:
        return "Cereza"
    elif "MIX" in prod_upper or "MIXED" in prod_upper or "CREATIVE" in prod_upper:
        return "Mix"
    
    return "Otro"


def detect_manejo(manejo_raw: Optional[str]) -> str:
    """
    Detecta manejo (Orgánico/Convencional) desde campo x_studio_categora_tipo_de_manejo.
    
    Args:
        manejo_raw: Valor del campo manejo
        
    Returns:
        "Orgánico" o "Convencional"
    """
    if manejo_raw and isinstance(manejo_raw, str):
        return "Orgánico" if "org" in manejo_raw.lower() else "Convencional"
    return "Convencional"


def is_excluded_category(cat_name: str) -> bool:
    """
    Verifica si una categoría debe ser excluida del stock de frutas.
    
    Args:
        cat_name: Nombre de la categoría
        
    Returns:
        True si debe excluirse
    """
    cat_upper = cat_name.upper() if cat_name else ""
    return any(excl in cat_upper for excl in CATEGORIAS_EXCLUIDAS)
