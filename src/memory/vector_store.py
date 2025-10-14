from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from typing import List, Dict, Optional
import uuid
import numpy as np

class VectorMemory:
    """Gestión de memoria vectorial usando Qdrant"""
    
    def __init__(self, path: str, collection_name: str, vector_size: int):
        print(f"Inicializando Qdrant en: {path}")
        self.client = QdrantClient(path=path)
        self.collection_name = collection_name
        self._ensure_collection(vector_size)
        print(f"✓ Colección '{collection_name}' lista")
    
    def _ensure_collection(self, vector_size: int):
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        
        if not exists:
            print(f"Creando colección '{self.collection_name}'...")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=Distance.COSINE
                )
            )
    
    def add_texts(
        self, 
        texts: List[str], 
        embeddings: List[np.ndarray], 
        metadata: List[Dict]
    ) -> List[str]:
        ids = [str(uuid.uuid4()) for _ in texts]
        
        points = [
            PointStruct(
                id=id_,
                vector=embedding.tolist(),
                payload={"text": text, **meta}
            )
            for id_, text, embedding, meta in zip(ids, texts, embeddings, metadata)
        ]
        
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        return ids
    
    def search(
        self, 
        query_embedding: np.ndarray, 
        top_k: int = 5, 
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=top_k,
            query_filter=filters
        )
        
        return [
            {
                "id": hit.id,
                "score": hit.score,
                "text": hit.payload.get("text"),
                "metadata": {k: v for k, v in hit.payload.items() if k != "text"}
            }
            for hit in results
        ]
    
    def delete_collection(self):
        self.client.delete_collection(collection_name=self.collection_name)
        print(f"✓ Colección '{self.collection_name}' eliminada")