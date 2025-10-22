# src/tools/date_normalizer.py - v1.0.0
"""
Normaliza referencias temporales en español a fechas absolutas.
Ejemplo: "hoy" → "2025-01-16", "próximo miércoles" → "2025-01-22"
"""

from __future__ import annotations
from datetime import datetime, timedelta
import re


class DateNormalizer:
    """
    Normaliza expresiones temporales relativas a fechas absolutas.
    """
    
    # Mapa de días de la semana
    _WEEKMAP = {
        "lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
        "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6
    }
    
    @staticmethod
    def _now_local() -> datetime:
        """Retorna datetime actual en timezone local."""
        return datetime.now().astimezone()
    
    @staticmethod
    def _absdate(dt: datetime) -> str:
        """Convierte datetime a string YYYY-MM-DD."""
        return dt.strftime("%Y-%m-%d")
    
    @staticmethod
    def _rel_day(base: datetime, delta_days: int) -> str:
        """Retorna fecha relativa a base + delta_days."""
        return DateNormalizer._absdate(base + timedelta(days=delta_days))
    
    @staticmethod
    def _nearest_weekday(base: datetime, target_weekday: int, direction: int) -> str:
        """
        Encuentra el día de la semana más cercano.
        
        Args:
            base: Fecha base
            target_weekday: Día objetivo (0=lunes, 6=domingo)
            direction: +1 para próximo, -1 para pasado
            
        Returns:
            Fecha en formato YYYY-MM-DD
        """
        cur = base.weekday()
        if direction == +1:  # próximo
            delta = (target_weekday - cur) % 7
            delta = 7 if delta == 0 else delta
        else:  # pasado
            delta = -((cur - target_weekday) % 7)
            delta = -7 if delta == 0 else delta
        return DateNormalizer._absdate(base + timedelta(days=delta))
    
    @classmethod
    def normalizar_fechas(cls, query: str, base_dt: datetime | None = None) -> str:
        """
        Normaliza todas las expresiones temporales en el query.
        
        Args:
            query: Query con expresiones temporales
            base_dt: Fecha base (default: ahora)
            
        Returns:
            Query con fechas absolutas
        """
        base = base_dt or cls._now_local()
        q = query
        
        # Expresiones compuestas
        comp = {
            r"\bpasado\s+mañana\b": cls._rel_day(base, +2),
            r"\banteayer\b": cls._rel_day(base, -2),
            r"\bante\s*ayer\b": cls._rel_day(base, -2),
            r"\bfin\s+de\s+mes\b": cls._absdate(
                (base.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            ),
            r"\bfin\s+de\s+semana\b": cls._absdate(
                base + timedelta(days=(5 - base.weekday()) % 7)
            ),
        }
        
        for pat, repl in comp.items():
            q = re.sub(pat, repl, q, flags=re.IGNORECASE)
        
        # Expresiones simples
        simples = {
            r"\bhoy\b": cls._absdate(base),
            r"\bayer\b": cls._rel_day(base, -1),
            r"\bayer\s+mismo\b": cls._rel_day(base, -1),
            r"\bmañana\b": cls._rel_day(base, +1),
        }
        
        for pat, repl in simples.items():
            q = re.sub(pat, repl, q, flags=re.IGNORECASE)
        
        # Días de la semana con modificador
        def _weekday_repl(m: re.Match) -> str:
            mod = (m.group("mod") or "").lower()
            wd = (m.group("wd") or "").lower()
            wd = "miércoles" if wd in ("miercoles",) else wd
            
            if wd not in cls._WEEKMAP:
                return m.group(0)
            
            direction = +1 if mod in ("proximo", "próximo") else -1
            return cls._nearest_weekday(base, cls._WEEKMAP[wd], direction)
        
        # Patrón: "el jueves próximo" o "jueves próximo"
        q = re.sub(
            r"\b(?:el\s+)?(?P<wd>lunes|martes|mi[eé]rcoles|jueves|viernes|s[áa]bado|domingo)\s+(?P<mod>pasado|pr[oó]ximo|ultimo|último)\b",
            _weekday_repl, q, flags=re.IGNORECASE
        )
        
        # Patrón: "próximo jueves"
        q = re.sub(
            r"\b(?P<mod>pasado|pr[oó]ximo|ultimo|último)\s+(?P<wd>lunes|martes|mi[eé]rcoles|jueves|viernes|s[áa]bado|domingo)\b",
            _weekday_repl, q, flags=re.IGNORECASE
        )
        
        return q
    
    @classmethod
    def preparar_query_finanzas(cls, q: str, forzar_argentina: bool = True) -> str:
        """
        Prepara query de finanzas con normalizaciones específicas.
        
        Args:
            q: Query original
            forzar_argentina: Agregar "argentina" si no está
            
        Returns:
            Query optimizado para finanzas argentinas
        """
        # Normalizar fechas primero
        qn = cls.normalizar_fechas(q)
        
        # Agregar "argentina" si no está
        if forzar_argentina and "argentina" not in qn.lower():
            qn += " argentina"
        
        # Si pregunta por dólar sin especificar tipo, agregar ambos
        if "dólar" in qn.lower() or "dolar" in qn.lower():
            if not any(w in qn.lower() for w in ["blue", "oficial", "mep", "ccl", "bolsa", "solidario", "tarjeta"]):
                qn += " oficial blue"
        
        return qn


# Para testing
if __name__ == "__main__":
    normalizer = DateNormalizer()
    
    tests = [
        "cotización dólar hoy",
        "clima mañana",
        "noticias del próximo miércoles",
        "partido de ayer",
        "eventos fin de semana",
    ]
    
    print("=== TEST: Date Normalizer ===\n")
    for test in tests:
        normalized = normalizer.normalizar_fechas(test)
        print(f"Original:    {test}")
        print(f"Normalizado: {normalized}\n")
    
    print("=== TEST: Finanzas ===\n")
    finance_test = "precio dólar hoy"
    prepared = normalizer.preparar_query_finanzas(finance_test)
    print(f"Original: {finance_test}")
    print(f"Preparado: {prepared}")