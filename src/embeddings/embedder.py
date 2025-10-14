from fastembed import TextEmbedding
from typing import List
import numpy as np

class EmbeddingService:
    """Servicio para generar embeddings de texto usando FastEmbed"""
    
    def __init__(self, model_name: str):
        """
        Inicializa el servicio de embeddings
        
        Args:
            model_name: Nombre del modelo de embeddings a usar
        """
        print(f"Inicializando modelo de embeddings: {model_name}")
        self.model = TextEmbedding(model_name=model_name)
        print("✓ Modelo cargado correctamente")
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Genera embeddings para una lista de textos
        
        Args:
            texts: Lista de textos a embedear
            
        Returns:
            Lista de arrays numpy con los embeddings
        """
        embeddings = list(self.model.embed(texts))
        return [np.array(emb) for emb in embeddings]
    
    def embed_single(self, text: str) -> np.ndarray:
        """
        Genera embedding para un solo texto
        
        Args:
            text: Texto a embedear
            
        Returns:
            Array numpy con el embedding
        """
        embedding = list(self.model.embed([text]))[0]
        return np.array(embedding)
