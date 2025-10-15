"""
Servicio de embeddings usando FastEmbed.
Compatible con múltiples versiones de la librería.
"""

from typing import List
import logging

# Intentar importar TextEmbedding de diferentes formas según la versión
try:
    from fastembed import TextEmbedding
except ImportError:
    try:
        from fastembed.embedding import TextEmbedding
    except ImportError:
        try:
            # Para versiones muy nuevas
            from fastembed import Embedding as TextEmbedding
        except ImportError:
            raise ImportError(
                "No se pudo importar TextEmbedding de fastembed. "
                "Intenta: pip install --upgrade fastembed"
            )

from config.settings import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Servicio para generar embeddings de texto usando FastEmbed.
    """
    
    def __init__(self, model_name: str = None):
        """
        Inicializa el servicio de embeddings.
        
        Args:
            model_name: Nombre del modelo a usar (opcional)
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self._model = None
        logger.info(f"EmbeddingService inicializado con modelo: {self.model_name}")
    
    @property
    def model(self) -> TextEmbedding:
        """Lazy loading del modelo."""
        if self._model is None:
            logger.info(f"Cargando modelo de embeddings: {self.model_name}")
            try:
                self._model = TextEmbedding(model_name=self.model_name)
            except Exception as e:
                logger.error(f"Error cargando modelo de embeddings: {e}")
                # Intentar con modelo por defecto
                logger.info("Intentando con modelo por defecto...")
                self._model = TextEmbedding()
            logger.info("✅ Modelo de embeddings cargado")
        return self._model
    
    def embed_text(self, text: str) -> List[float]:
        """
        Genera embedding para un texto.
        
        Args:
            text: Texto a embebir
            
        Returns:
            Vector de embeddings
        """
        if not text or not text.strip():
            logger.warning("Texto vacío recibido para embedding")
            return [0.0] * settings.EMBEDDING_DIM
        
        try:
            # FastEmbed retorna un generador, tomar el primer resultado
            embeddings = list(self.model.embed([text]))
            if embeddings:
                return embeddings[0].tolist()
            else:
                logger.error("No se generó embedding")
                return [0.0] * settings.EMBEDDING_DIM
        except Exception as e:
            logger.error(f"Error generando embedding: {e}")
            return [0.0] * settings.EMBEDDING_DIM
    
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Genera embeddings para múltiples textos.
        
        Args:
            texts: Lista de textos
            
        Returns:
            Lista de vectores de embeddings
        """
        if not texts:
            return []
        
        try:
            # Filtrar textos vacíos
            valid_texts = [t for t in texts if t and t.strip()]
            
            if not valid_texts:
                logger.warning("Todos los textos están vacíos")
                return [[0.0] * settings.EMBEDDING_DIM] * len(texts)
            
            # Generar embeddings
            embeddings = list(self.model.embed(valid_texts))
            result = [emb.tolist() for emb in embeddings]
            
            logger.info(f"Generados {len(result)} embeddings")
            return result
            
        except Exception as e:
            logger.error(f"Error generando embeddings batch: {e}")
            return [[0.0] * settings.EMBEDDING_DIM] * len(texts)
    
    def get_dimension(self) -> int:
        """Retorna la dimensión de los embeddings."""
        return settings.EMBEDDING_DIM


# Singleton para reutilizar el servicio
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """
    Obtiene la instancia singleton del servicio de embeddings.
    
    Returns:
        Instancia de EmbeddingService
    """
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service