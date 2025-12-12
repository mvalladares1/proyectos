"""
Servicio de Tipos de Cambio - Conversión USD a CLP
Utiliza la API gratuita de ExchangeRate-API con caché en memoria.
"""
import time
import requests
from typing import Optional


class CurrencyService:
    """
    Servicio para obtener tipos de cambio USD → CLP.
    
    Características:
    - Caché en memoria por 1 hora para evitar llamadas excesivas
    - Fallback a valor por defecto si la API falla
    - API gratuita sin necesidad de API key
    """
    
    # Caché de clase (compartido entre instancias)
    _cache_rate: Optional[float] = None
    _cache_time: Optional[float] = None
    _cache_ttl: int = 3600  # 1 hora de caché
    
    # Valor de fallback si la API falla
    FALLBACK_RATE: float = 950.0
    
    # URL de la API
    API_URL: str = "https://api.exchangerate-api.com/v4/latest/USD"
    
    @classmethod
    def get_usd_to_clp_rate(cls) -> float:
        """
        Obtiene el tipo de cambio USD → CLP.
        
        Returns:
            float: Tipo de cambio (cuántos CLP por 1 USD)
        
        Ejemplo:
            >>> rate = CurrencyService.get_usd_to_clp_rate()
            >>> print(rate)  # 922.29
        """
        # Verificar si hay caché válido
        if cls._cache_rate is not None and cls._cache_time is not None:
            elapsed = time.time() - cls._cache_time
            if elapsed < cls._cache_ttl:
                return cls._cache_rate
        
        # Consultar API externa
        try:
            response = requests.get(cls.API_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            rate = data.get('rates', {}).get('CLP')
            
            if rate and rate > 0:
                # Guardar en caché
                cls._cache_rate = float(rate)
                cls._cache_time = time.time()
                return cls._cache_rate
            else:
                # Tasa no encontrada, usar fallback
                return cls.FALLBACK_RATE
                
        except Exception as e:
            # Error en la API, usar fallback
            print(f"[CurrencyService] Error obteniendo tipo de cambio: {e}")
            return cls.FALLBACK_RATE
    
    @classmethod
    def convert_usd_to_clp(cls, amount_usd: float) -> float:
        """
        Convierte un monto de USD a CLP.
        
        Args:
            amount_usd: Monto en dólares estadounidenses
            
        Returns:
            float: Monto equivalente en pesos chilenos
        """
        rate = cls.get_usd_to_clp_rate()
        return amount_usd * rate
    
    @classmethod
    def clear_cache(cls):
        """Limpia el caché de tipos de cambio."""
        cls._cache_rate = None
        cls._cache_time = None
    
    @classmethod
    def get_cache_info(cls) -> dict:
        """
        Retorna información sobre el estado del caché.
        
        Returns:
            dict con 'rate', 'age_seconds', 'is_valid'
        """
        if cls._cache_rate is None or cls._cache_time is None:
            return {
                'rate': None,
                'age_seconds': None,
                'is_valid': False
            }
        
        age = time.time() - cls._cache_time
        return {
            'rate': cls._cache_rate,
            'age_seconds': round(age, 1),
            'is_valid': age < cls._cache_ttl
        }
