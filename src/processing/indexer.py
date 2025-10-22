# src/processing/indexer.py - Indexador de documentos
"""
Indexador de documentos para Minerva.
Conecta el procesador con Qdrant y SQLite.
"""

from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
from datetime import datetime
import uuid

from .document_processor import DocumentProcessor, DocumentChunk
from src.embeddings import EmbeddingService
from src.memory import VectorMemory
from src.database import DatabaseManager


class DocumentIndexer:
    """
    Indexa documentos en Qdrant y SQLite.
    
    Pipeline:
    1. Procesa documento → chunks
    2. Genera embeddings para cada chunk
    3. Guarda en Qdrant
    4. Registra en SQLite
    """
    
    def __init__(
        self,
        vector_memory: VectorMemory,
        db_manager: DatabaseManager,
        embedding_service: EmbeddingService,
        chunk_size: int = 500,
        chunk_overlap: int = 50
    ):
        """
        Inicializa el indexador.
        
        Args:
            vector_memory: Servicio de memoria vectorial
            db_manager: Gestor de base de datos
            embedding_service: Servicio de embeddings
            chunk_size: Tamaño de chunks
            chunk_overlap: Solapamiento entre chunks
        """
        self.vector_memory = vector_memory
        self.db_manager = db_manager
        self.embedding_service = embedding_service
        
        self.processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        
        self.logger = logging.getLogger("minerva.indexer")
    
    def index_document(
        self,
        file_path: Path,
        collection_name: str = None
    ) -> Dict[str, Any]:
        """
        Indexa un documento completo.
        
        Args:
            file_path: Ruta al documento
            collection_name: Nombre de la colección en Qdrant
            
        Returns:
            Diccionario con información del indexado
        """
        # Usar colección por defecto si no se especifica
        if collection_name is None:
            collection_name = self.vector_memory.collection_name
            
        file_path = Path(file_path)
        start_time = datetime.now()
        
        self.logger.info(f"Iniciando indexado de {file_path.name}")
        
        try:
            # 1. Procesar documento
            chunks = self.processor.process_file(file_path)
            self.logger.info(f"Documento dividido en {len(chunks)} chunks")
            
            # 2. Generar embeddings
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.embed_batch(chunk_texts)
            self.logger.info(f"Embeddings generados: {len(embeddings)}")
            
            # 3. Preparar payloads para Qdrant
            payloads = []
            for chunk in chunks:
                payload = {
                    'text': chunk.text,
                    'filename': chunk.source_file,
                    'file_type': Path(chunk.source_file).suffix[1:],
                    'chunk_index': chunk.chunk_index,
                    'collection': collection_name,
                    'indexed_at': datetime.now().isoformat()
                }
                if chunk.metadata:
                    payload.update(chunk.metadata)
                payloads.append(payload)
            
            # 4. Generar IDs únicos para Qdrant
            qdrant_ids = [str(uuid.uuid4()) for _ in chunks]
            
            # 5. Guardar en Qdrant
            self.vector_memory.add_texts(
                texts=chunk_texts,
                embeddings=embeddings,
                payloads=payloads,
                ids=qdrant_ids
            )
            self.logger.info(f"Chunks guardados en Qdrant (colección: {collection_name})")
            
            # 6. Registrar en SQLite
            doc_record = self.db_manager.add_document(
                filename=file_path.name,
                file_type=file_path.suffix[1:],  # sin el punto
                file_size=file_path.stat().st_size,
                original_path=str(file_path),
                chunk_count=len(chunks),
                qdrant_collection=collection_name,
                qdrant_ids=qdrant_ids,
                metadata={
                    'total_chars': sum(len(c.text) for c in chunks),
                    'processing_time_seconds': (datetime.now() - start_time).total_seconds()
                }
            )
            self.logger.info(f"Documento registrado en SQLite (ID: {doc_record.id})")
            
            # 7. Calcular estadísticas
            duration = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'document_id': doc_record.id,
                'filename': file_path.name,
                'chunks_created': len(chunks),
                'qdrant_ids': qdrant_ids,
                'collection': collection_name,
                'processing_time_seconds': duration
            }
            
            self.logger.info(
                f"Indexado completado: {file_path.name} "
                f"({len(chunks)} chunks en {duration:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error indexando {file_path.name}: {e}", exc_info=True)
            return {
                'success': False,
                'filename': file_path.name,
                'error': str(e)
            }
    
    def search_documents(
        self,
        query: str,
        collection_name: str = None,
        limit: int = 5,
        score_threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Busca en documentos indexados.
        
        Args:
            query: Consulta del usuario
            collection_name: Colección donde buscar
            limit: Número máximo de resultados
            score_threshold: Umbral mínimo de similitud
            
        Returns:
            Lista de resultados con chunks relevantes
        """
        # Usar colección por defecto si no se especifica
        if collection_name is None:
            collection_name = self.vector_memory.collection_name
            
        self.logger.info(f"Buscando: '{query}' en colección '{collection_name}'")
        
        try:
            # Generar embedding de la consulta
            query_embedding = self.embedding_service.embed_text(query)
            
            # Buscar en Qdrant
            results = self.vector_memory.search(
                query_embedding=query_embedding,
                limit=limit
            )
            
            # Filtrar por score
            filtered_results = [
                r for r in results
                if r['score'] >= score_threshold
            ]
            
            self.logger.info(
                f"Encontrados {len(filtered_results)} resultados "
                f"(umbral: {score_threshold})"
            )
            
            return filtered_results
            
        except Exception as e:
            self.logger.error(f"Error en búsqueda: {e}", exc_info=True)
            return []
    
    def get_document_context(
        self,
        query: str,
        collection_name: str = None,
        max_chunks: int = 3
    ) -> str:
        """
        Obtiene contexto relevante de documentos para una consulta.
        
        Args:
            query: Consulta del usuario
            collection_name: Colección donde buscar
            max_chunks: Máximo número de chunks a incluir
            
        Returns:
            String con contexto formateado
        """
        # Usar colección por defecto si no se especifica
        if collection_name is None:
            collection_name = self.vector_memory.collection_name
            
        results = self.search_documents(
            query=query,
            collection_name=collection_name,
            limit=max_chunks
        )
        
        if not results:
            return ""
        
        # Formatear contexto
        context_parts = []
        
        for i, result in enumerate(results, 1):
            payload = result.get('payload', {})
            score = result.get('score', 0)
            text = result.get('text', payload.get('text', ''))
            filename = payload.get('filename', 'unknown')
            
            context_parts.append(
                f"[Fuente {i}: {filename} - "
                f"Relevancia: {score:.2f}]\n"
                f"{text}\n"
            )
        
        context = "\n---\n".join(context_parts)
        
        self.logger.info(f"Contexto generado: {len(context)} chars de {len(results)} chunks")
        
        return context
    # src/processing/indexer.py - Agregar este método a la clase DocumentIndexer

    def has_documents(self, collection_name: str = None) -> bool:
        """
        Verifica si hay documentos indexados en la colección.
        
        Args:
            collection_name: Colección a verificar (usa default si no se especifica)
            
        Returns:
            True si hay documentos indexados, False si no
        """
        # Usar colección por defecto si no se especifica
        if collection_name is None:
            collection_name = self.vector_memory.collection_name
        
        try:
            # Opción 1: Verificar en Qdrant directamente
            collection_info = self.vector_memory.client.get_collection(
                collection_name=collection_name
            )
            has_vectors = collection_info.points_count > 0
            
            self.logger.debug(
                f"Colección '{collection_name}': {collection_info.points_count} vectores"
            )
            
            return has_vectors
            
        except Exception as e:
            # Si la colección no existe o hay error, no hay documentos
            self.logger.debug(f"Error verificando documentos: {e}")
            return False

    def delete_document(
        self,
        document_id: int,
        collection_name: str = None
    ) -> bool:
        """
        Elimina un documento del índice.
        
        Args:
            document_id: ID del documento en SQLite
            collection_name: Colección de Qdrant
            
        Returns:
            True si se eliminó correctamente
        """
        # Usar colección por defecto si no se especifica
        if collection_name is None:
            collection_name = self.vector_memory.collection_name
            
        try:
            # Obtener IDs de Qdrant desde SQLite
            doc = self.db_manager.get_document(document_id)
            
            if not doc:
                self.logger.warning(f"Documento {document_id} no encontrado")
                return False
            
            # Eliminar de Qdrant
            if doc.qdrant_ids:
                for qdrant_id in doc.qdrant_ids:
                    self.vector_memory.delete_point(point_id=qdrant_id)
            
            # Marcar como no indexado en SQLite
            doc.is_indexed = False
            
            self.logger.info(f"Documento {document_id} eliminado del índice")
            return True
            
        except Exception as e:
            self.logger.error(f"Error eliminando documento {document_id}: {e}")
            return False