"""
Gestor de memoria vectorial usando Qdrant con patrón Singleton.
"""

from typing import List, Dict, Any, Optional
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct


class VectorMemory:
    """
    Gestor de memoria vectorial con Qdrant (Singleton).
    
    Funcionalidades:
    - Almacenar embeddings con metadata
    - Buscar por similitud semántica
    - Gestionar colecciones
    - Una sola instancia de QdrantClient para evitar locks
    """
    
    _instance = None
    _client = None
    _initialized = False
    
    def __new__(cls, path: str = None, collection_name: str = None, vector_size: int = 384):
        """Patrón Singleton - Solo una instancia."""
        if cls._instance is None:
            cls._instance = super(VectorMemory, cls).__new__(cls)
        return cls._instance
    
    def __init__(
        self,
        path: str,
        collection_name: str,
        vector_size: int = 384
    ):
        """
        Inicializa el gestor de memoria vectorial.
        
        Args:
            path: Ruta para almacenamiento local de Qdrant
            collection_name: Nombre de la colección por defecto
            vector_size: Dimensión de los vectores
        """
        # Solo inicializar una vez
        if VectorMemory._initialized:
            return
        
        VectorMemory._client = QdrantClient(path=path)
        self.client = VectorMemory._client
        self.collection_name = collection_name
        self.vector_size = vector_size
        
        # Crear colección si no existe
        self._ensure_collection()
        
        VectorMemory._initialized = True
    
    def _ensure_collection(self, collection_name: Optional[str] = None):
        """Asegura que la colección existe."""
        col_name = collection_name or self.collection_name
        
        collections = self.client.get_collections().collections
        collection_names = [col.name for col in collections]
        
        if col_name not in collection_names:
            self.client.create_collection(
                collection_name=col_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def add_texts(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        payloads: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
        collection_name: Optional[str] = None
    ):
        """
        Agrega textos con sus embeddings a la memoria.
        
        Args:
            texts: Lista de textos
            embeddings: Lista de embeddings
            payloads: Metadata adicional para cada texto (opcional)
            ids: IDs personalizados para los puntos (opcional)
            collection_name: Nombre de colección (usa default si no se especifica)
        """
        col_name = collection_name or self.collection_name
        self._ensure_collection(col_name)
        
        # Preparar payloads
        if payloads is None:
            payloads = [{'text': text} for text in texts]
        else:
            # Asegurar que el texto esté en el payload
            for i, payload in enumerate(payloads):
                if 'text' not in payload:
                    payload['text'] = texts[i]
        
        # Generar IDs si no se proporcionan
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in texts]
        
        # Crear puntos
        points = [
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            for point_id, embedding, payload in zip(ids, embeddings, payloads)
        ]
        
        # Subir a Qdrant
        self.client.upsert(
            collection_name=col_name,
            points=points
        )
    
    def search(
        self,
        query_text: str = None,
        query_embedding: List[float] = None,
        limit: int = 5,
        collection_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca vectores similares.
        
        Args:
            query_text: Texto de consulta (se ignora, se usa query_embedding)
            query_embedding: Embedding de la consulta
            limit: Número máximo de resultados
            collection_name: Nombre de colección
            
        Returns:
            Lista de resultados con score y payload
        """
        col_name = collection_name or self.collection_name
        
        if query_embedding is None:
            raise ValueError("query_embedding es requerido")
        
        results = self.client.search(
            collection_name=col_name,
            query_vector=query_embedding,
            limit=limit
        )
        
        return [
            {
                'id': result.id,
                'score': result.score,
                'payload': result.payload
            }
            for result in results
        ]
    
    def delete_point(
        self,
        point_id: str,
        collection_name: Optional[str] = None
    ):
        """
        Elimina un punto por su ID.
        
        Args:
            point_id: ID del punto
            collection_name: Nombre de colección
        """
        col_name = collection_name or self.collection_name
        
        self.client.delete(
            collection_name=col_name,
            points_selector=[point_id]
        )
    
    def delete_collection(self, collection_name: Optional[str] = None):
        """
        Elimina una colección completa.
        
        Args:
            collection_name: Nombre de la colección (usa default si no se especifica)
        """
        col_name = collection_name or self.collection_name
        self.client.delete_collection(collection_name=col_name)
    
    def get_collection_info(self, collection_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Obtiene información sobre una colección.
        
        Args:
            collection_name: Nombre de colección
            
        Returns:
            Diccionario con información de la colección
        """
        col_name = collection_name or self.collection_name
        
        info = self.client.get_collection(collection_name=col_name)
        
        return {
            'name': col_name,
            'vectors_count': info.vectors_count,
            'points_count': info.points_count,
            'status': info.status
        }