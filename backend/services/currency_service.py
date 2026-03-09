"""
Servicio de Tipos de Cambio - Conversión USD/UF a CLP
Utiliza tipo de cambio oficial BCCh (Dólar observado y UF) vía mindicador.cl con caché.
"""
import time
import requests
from typing import Optional
from datetime import datetime, timezone, timedelta


class CurrencyService:
    """
    Servicio para obtener tipos de cambio USD/UF → CLP.
    
    Características:
    - Usa Dólar observado y UF oficial BCCh (serie pública de mindicador.cl)
    - Prioriza tasa del día actual (hora Chile)
    - Si hoy no está publicado (feriado/no hábil), usa último dato disponible
    - Caché en memoria por 1 hora para evitar llamadas excesivas
    - Fallback a valor por defecto si la API falla
    """
    
    # Caché de clase (compartido entre instancias)
    _cache_rate: Optional[float] = None
    _cache_time: Optional[float] = None
    _cache_uf_rate: Optional[float] = None
    _cache_uf_time: Optional[float] = None
    _cache_ttl: int = 3600  # 1 hora de caché
    
    # Valor de fallback si la API falla
    FALLBACK_RATE: float = 950.0
    FALLBACK_UF_RATE: float = 38500.0  # Aprox valor UF marzo 2026
    
    # URLs serie pública del dólar observado y UF (fuente BCCh)
    API_URL: str = "https://mindicador.cl/api/dolar"
    API_UF_URL: str = "https://mindicador.cl/api/uf"
    
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
        
        # Consultar serie oficial
        try:
            response = requests.get(cls.API_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            serie = data.get('serie', []) if isinstance(data, dict) else []

            if not serie:
                print("[CurrencyService] Serie de dólar vacía, usando fallback")
                return cls.FALLBACK_RATE

            # Fecha actual en Chile (UTC-3/UTC-4 aproximado para comparación de día)
            chile_tz = timezone(timedelta(hours=-3))
            hoy_chile = datetime.now(chile_tz).date()

            # Buscar valor del día actual
            rate = None
            for item in serie:
                fecha_str = item.get('fecha', '')
                valor = item.get('valor')
                if not fecha_str or valor is None:
                    continue
                try:
                    fecha_item = datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
                except Exception:
                    continue

                if fecha_item == hoy_chile:
                    rate = float(valor)
                    break

            # Si hoy no está disponible (feriado/no hábil), usar el último disponible
            if rate is None:
                primer = serie[0] if serie else {}
                valor_ultimo = primer.get('valor')
                if valor_ultimo is not None:
                    rate = float(valor_ultimo)
                    print(f"[CurrencyService] Tasa de hoy no disponible, usando último valor BCCh: {rate}")

            if rate and rate > 0:
                # Guardar en caché
                cls._cache_rate = rate
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
    def get_uf_to_clp_rate(cls) -> float:
        """
        Obtiene el tipo de cambio UF → CLP.
        
        Returns:
            float: Tipo de cambio (cuántos CLP por 1 UF)
        
        Ejemplo:
            >>> rate = CurrencyService.get_uf_to_clp_rate()
            >>> print(rate)  # 38500.12
        """
        # Verificar si hay caché válido
        if cls._cache_uf_rate is not None and cls._cache_uf_time is not None:
            elapsed = time.time() - cls._cache_uf_time
            if elapsed < cls._cache_ttl:
                return cls._cache_uf_rate
        
        # Consultar serie oficial
        try:
            response = requests.get(cls.API_UF_URL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            serie = data.get('serie', []) if isinstance(data, dict) else []

            if not serie:
                print("[CurrencyService] Serie de UF vacía, usando fallback")
                return cls.FALLBACK_UF_RATE

            # Fecha actual en Chile (UTC-3/UTC-4 aproximado para comparación de día)
            chile_tz = timezone(timedelta(hours=-3))
            hoy_chile = datetime.now(chile_tz).date()

            # Buscar valor del día actual
            rate = None
            for item in serie:
                fecha_str = item.get('fecha', '')
                valor = item.get('valor')
                if not fecha_str or valor is None:
                    continue
                try:
                    fecha_item = datetime.fromisoformat(fecha_str.replace('Z', '+00:00')).date()
                except Exception:
                    continue

                if fecha_item == hoy_chile:
                    rate = float(valor)
                    break

            # Si hoy no está disponible (feriado/no hábil), usar el último disponible
            if rate is None:
                primer = serie[0] if serie else {}
                valor_ultimo = primer.get('valor')
                if valor_ultimo is not None:
                    rate = float(valor_ultimo)
                    print(f"[CurrencyService] Tasa UF de hoy no disponible, usando último valor BCCh: {rate}")

            if rate and rate > 0:
                # Guardar en caché
                cls._cache_uf_rate = rate
                cls._cache_uf_time = time.time()
                return cls._cache_uf_rate
            else:
                # Tasa no encontrada, usar fallback
                return cls.FALLBACK_UF_RATE
                
        except Exception as e:
            # Error en la API, usar fallback
            print(f"[CurrencyService] Error obteniendo tipo de cambio UF: {e}")
            return cls.FALLBACK_UF_RATE
    
    @classmethod
    def convert_uf_to_clp(cls, amount_uf: float) -> float:
        """
        Convierte un monto de UF a CLP.
        
        Args:
            amount_uf: Monto en Unidades de Fomento (CLF)
            
        Returns:
            float: Monto equivalente en pesos chilenos
        """
        rate = cls.get_uf_to_clp_rate()
        return amount_uf * rate
    
    @classmethod
    def clear_cache(cls):
        """Limpia el caché de tipos de cambio (USD y UF)."""
        cls._cache_rate = None
        cls._cache_time = None
        cls._cache_uf_rate = None
        cls._cache_uf_time = None
    
    @classmethod
    def get_cache_info(cls) -> dict:
        """
        Retorna información sobre el estado del caché.
        
        Returns:
            dict con 'usd_rate', 'uf_rate', 'age_seconds', 'is_valid'
        """
        result = {
            'usd_rate': None,
            'uf_rate': None,
            'usd_age_seconds': None,
            'uf_age_seconds': None,
            'usd_is_valid': False,
            'uf_is_valid': False
        }
        
        if cls._cache_rate is not None and cls._cache_time is not None:
            age = time.time() - cls._cache_time
            result['usd_rate'] = cls._cache_rate
            result['usd_age_seconds'] = round(age, 1)
            result['usd_is_valid'] = age < cls._cache_ttl
        
        if cls._cache_uf_rate is not None and cls._cache_uf_time is not None:
            age = time.time() - cls._cache_uf_time
            result['uf_rate'] = cls._cache_uf_rate
            result['uf_age_seconds'] = round(age, 1)
            result['uf_is_valid'] = age < cls._cache_ttl
        
        return result
