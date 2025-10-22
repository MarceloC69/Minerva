# src/tools/web_search.py - v2.0.0
"""
Tool de búsqueda web usando Serper.dev (Google Search API).
Permite buscar información actualizada sin rate limits y con normalización de fechas.
"""

from typing import List, Dict, Optional
import logging
import requests
import os
from pathlib import Path

# Importar date normalizer
try:
    from src.tools.date_normalizer import DateNormalizer
except ImportError:
    DateNormalizer = None

logger = logging.getLogger(__name__)


class WebSearchTool:
    """
    Tool para realizar búsquedas web usando Serper.dev API.
    
    Características:
    - API de Google Search (2500 búsquedas gratis/mes)
    - Sin rate limits molestos
    - Normalización automática de fechas relativas
    - Resultados de alta calidad
    """
    
    def __init__(self, max_results: int = 5, api_key: Optional[str] = None):
        """
        Inicializa el tool de búsqueda web.
        
        Args:
            max_results: Número máximo de resultados a retornar
            api_key: API key de Serper.dev (o la toma del .env)
        """
        self.max_results = max_results
        self.logger = logging.getLogger("minerva.websearch")
        
        # Obtener API key
        self.api_key = api_key or os.getenv('SERPER_API_KEY', '3ef61ab84a2e43cd69eb1c9518f5fb79f58e335c')
        
        # URL de Serper.dev
        self.api_url = "https://google.serper.dev/search"
        
        # Inicializar date normalizer si está disponible
        self.date_normalizer = DateNormalizer() if DateNormalizer else None
    
    def _normalize_query(self, query: str) -> str:
        """
        Normaliza la query convirtiendo fechas relativas a absolutas.
        
        Args:
            query: Query original
            
        Returns:
            Query con fechas normalizadas
        """
        if self.date_normalizer:
            try:
                normalized = self.date_normalizer.normalizar_fechas(query)
                if normalized != query:
                    self.logger.info(f"📅 Query normalizada: '{query}' → '{normalized}'")
                return normalized
            except Exception as e:
                self.logger.warning(f"⚠️ Error normalizando fechas: {e}")
                return query
        return query
    
    def search(
        self, 
        query: str, 
        num_results: Optional[int] = None,
        normalize_dates: bool = True
    ) -> List[Dict[str, str]]:
        """
        Realiza una búsqueda web usando Serper.dev.
        
        Args:
            query: Consulta de búsqueda
            num_results: Número de resultados (usa max_results por defecto)
            normalize_dates: Si normalizar fechas relativas
            
        Returns:
            Lista de diccionarios con: title, snippet, link
        """
        try:
            # Normalizar query si es necesario
            search_query = self._normalize_query(query) if normalize_dates else query
            
            num = num_results or self.max_results
            
            self.logger.info(f"🔍 Buscando en Serper.dev: '{search_query}'")
            
            # Preparar request
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': search_query,
                'num': num,
                'gl': 'ar',  # Argentina
                'hl': 'es'   # Español
            }
            
            # Realizar búsqueda
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extraer resultados orgánicos
            organic_results = data.get('organic', [])
            
            # Formatear resultados
            formatted_results = []
            for i, result in enumerate(organic_results[:num], 1):
                formatted_results.append({
                    'title': result.get('title', 'Sin título'),
                    'snippet': result.get('snippet', 'Sin descripción'),
                    'link': result.get('link', ''),
                    'position': i
                })
            
            self.logger.info(f"✅ Encontrados {len(formatted_results)} resultados")
            return formatted_results
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error en request a Serper.dev: {e}")
            return []
        except Exception as e:
            self.logger.error(f"❌ Error en búsqueda web: {e}")
            return []
    
    def search_news(
        self, 
        query: str, 
        num_results: Optional[int] = None,
        normalize_dates: bool = True
    ) -> List[Dict[str, str]]:
        """
        Busca noticias recientes usando Serper News API.
        
        Args:
            query: Consulta de búsqueda
            num_results: Número de resultados
            normalize_dates: Si normalizar fechas relativas
            
        Returns:
            Lista de noticias con: title, snippet, link, date
        """
        try:
            # Normalizar query si es necesario
            search_query = self._normalize_query(query) if normalize_dates else query
            
            num = num_results or self.max_results
            
            self.logger.info(f"📰 Buscando noticias en Serper.dev: '{search_query}'")
            
            # Preparar request
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': search_query,
                'num': num,
                'gl': 'ar',  # Argentina
                'hl': 'es'   # Español
            }
            
            # Usar endpoint de noticias
            news_url = "https://google.serper.dev/news"
            
            response = requests.post(
                news_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Extraer noticias
            news_results = data.get('news', [])
            
            # Formatear resultados
            formatted_results = []
            for i, result in enumerate(news_results[:num], 1):
                formatted_results.append({
                    'title': result.get('title', 'Sin título'),
                    'snippet': result.get('snippet', 'Sin descripción'),
                    'link': result.get('link', ''),
                    'date': result.get('date', ''),
                    'position': i
                })
            
            self.logger.info(f"✅ Encontradas {len(formatted_results)} noticias")
            return formatted_results
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Error en request de noticias: {e}")
            return []
        except Exception as e:
            self.logger.error(f"❌ Error buscando noticias: {e}")
            return []
    
    def quick_answer(self, query: str) -> Optional[str]:
        """
        Intenta obtener una respuesta directa del knowledge graph.
        
        Args:
            query: Pregunta simple
            
        Returns:
            Respuesta directa si está disponible
        """
        try:
            self.logger.info(f"💡 Buscando respuesta rápida: '{query}'")
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                'q': query,
                'gl': 'ar',
                'hl': 'es'
            }
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=10
            )
            
            response.raise_for_status()
            data = response.json()
            
            # Intentar extraer answer box o knowledge graph
            answer_box = data.get('answerBox')
            if answer_box:
                answer = answer_box.get('answer') or answer_box.get('snippet')
                if answer:
                    self.logger.info("✅ Respuesta rápida encontrada")
                    return answer
            
            knowledge_graph = data.get('knowledgeGraph')
            if knowledge_graph:
                description = knowledge_graph.get('description')
                if description:
                    self.logger.info("✅ Respuesta desde Knowledge Graph")
                    return description
            
            self.logger.info("ℹ️ No hay respuesta rápida disponible")
            return None
                
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo respuesta rápida: {e}")
            return None


# Para testing directo
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Configurar logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Agregar root al path
    ROOT_DIR = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(ROOT_DIR))
    
    # Crear tool
    tool = WebSearchTool(max_results=3)
    
    # Test búsqueda general
    print("=== TEST 1: Búsqueda General ===\n")
    results = tool.search("Python programming language")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['snippet'][:100]}...")
        print(f"   {result['link']}\n")
    
    # Test con normalización de fechas
    print("\n=== TEST 2: Normalización de Fechas ===\n")
    results = tool.search("cotización dólar hoy argentina")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['link']}\n")
    
    # Test búsqueda de noticias
    print("\n=== TEST 3: Noticias ===\n")
    news = tool.search_news("tecnología argentina")
    
    for i, item in enumerate(news, 1):
        print(f"{i}. {item['title']}")
        print(f"   {item['date']}")
        print(f"   {item['link']}\n")