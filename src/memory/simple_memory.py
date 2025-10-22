# src/memory/simple_memory.py
"""
Sistema de memoria persistente SIMPLE para Minerva.
100% local, sin dependencias problemáticas.

Usa:
- Ollama para extraer hechos
- EmbeddingService existente (FastEmbed)
- VectorMemory existente (Qdrant)
- SQLite para metadata
"""

from typing import List, Dict, Any, Optional
import logging
import requests
import json
from datetime import datetime
import uuid

from config.settings import settings


class SimpleMemoryService:
    """
    Servicio de memoria persistente simple y funcional.
    
    Características:
    - Extrae hechos automáticamente con Ollama
    - Almacena en Qdrant (vectores) + SQLite (metadata)
    - Búsqueda semántica
    - 100% local
    """
    
    def __init__(
        self,
        embedding_service,
        vector_memory,
        db_manager=None
    ):
        """
        Inicializa el servicio de memoria.
        
        Args:
            embedding_service: Servicio de embeddings existente
            vector_memory: VectorMemory (Qdrant) existente
            db_manager: Database manager (opcional)
        """
        self.logger = logging.getLogger("minerva.simple_memory")
        self.embedding_service = embedding_service
        self.vector_memory = vector_memory
        self.db_manager = db_manager
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.ollama_model = settings.OLLAMA_MODEL
        
        # Colección específica para memoria
        self.memory_collection = "minerva_simple_memory"
        
        self.logger.info("✅ SimpleMemoryService inicializado")
    
    def _extract_facts(self, text: str) -> List[str]:
        """
        Extrae hechos relevantes del texto usando Ollama.
        
        Args:
            text: Texto del que extraer hechos
            
        Returns:
            Lista de hechos extraídos
        """
        prompt = f"""Extrae los hechos importantes de esta conversación.
Retorna solo los hechos, uno por línea.
No agregues numeración ni explicaciones.
Si no hay hechos relevantes, retorna "NINGUNO".

Conversación:
{text}

Hechos importantes:"""
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.ollama_model,
                    "prompt": prompt,
                    "temperature": 0.1,
                    "stream": False
                },
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            facts_text = result.get('response', '').strip()
            
            # Parsear hechos
            if facts_text == "NINGUNO" or not facts_text:
                return []
            
            # Separar por líneas y limpiar
            facts = []
            for line in facts_text.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                # Eliminar numeración (1., 2., -, *, etc.)
                import re
                line = re.sub(r'^\d+\.\s*', '', line)  # 1. 2. 3.
                line = re.sub(r'^[-*•]\s*', '', line)  # - * •
                line = line.strip()
                
                if line and len(line) > 10:  # Mínimo 10 caracteres
                    facts.append(line)
            
            return facts[:5]  # Máximo 5 hechos por interacción
            
        except Exception as e:
            self.logger.error(f"Error extrayendo hechos: {e}")
            return []
    
    def remember(
        self,
        text: str,
        user_id: str = "default_user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Memoriza información del texto.
        
        Args:
            text: Texto que contiene información a memorizar
            user_id: ID del usuario
            metadata: Metadata adicional
            
        Returns:
            Resultado de la operación
        """
        try:
            self.logger.info(f"💾 Memorizando: {text[:100]}...")
            
            # 1. Extraer hechos con Ollama
            facts = self._extract_facts(text)
            
            if not facts:
                self.logger.info("ℹ️ No se encontraron hechos relevantes")
                return {
                    'success': True,
                    'facts_count': 0,
                    'message': 'No hay hechos relevantes'
                }
            
            self.logger.info(f"✅ Extraídos {len(facts)} hechos")
            
            # 2. Guardar cada hecho en Qdrant
            saved_facts = []
            for fact in facts:
                try:
                    # Generar embedding
                    embedding = self.embedding_service.embed_text(fact)
                    
                    # Generar ID único
                    fact_id = str(uuid.uuid4())
                    
                    # Payload con metadata
                    payload = {
                        'text': fact,
                        'user_id': user_id,
                        'timestamp': datetime.now().isoformat(),
                        'source': text[:200],  # Primeros 200 chars del texto original
                        **(metadata or {})
                    }
                    
                    # Guardar en Qdrant
                    self.vector_memory.add_texts(
                        texts=[fact],
                        embeddings=[embedding],
                        payloads=[payload],
                        ids=[fact_id],
                        collection_name=self.memory_collection
                    )
                    
                    saved_facts.append(fact)
                    
                    # Guardar en SQLite si está disponible
                    if self.db_manager:
                        try:
                            # Aquí podrías guardar en la tabla memory_facts
                            pass
                        except Exception as e:
                            self.logger.warning(f"No se pudo guardar en DB: {e}")
                    
                except Exception as e:
                    self.logger.error(f"Error guardando hecho '{fact}': {e}")
                    continue
            
            self.logger.info(f"✅ Guardados {len(saved_facts)} hechos en memoria")
            
            return {
                'success': True,
                'facts_count': len(saved_facts),
                'facts': saved_facts
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error en remember: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }
    
    def recall(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 5
    ) -> List[str]:
        """
        Recuerda información relevante para la query.
        
        Args:
            query: Consulta de búsqueda
            user_id: ID del usuario
            limit: Número máximo de resultados
            
        Returns:
            Lista de hechos relevantes
        """
        try:
            self.logger.info(f"🔍 Recordando: {query[:100]}...")
            
            # Generar embedding de la query
            query_embedding = self.embedding_service.embed_text(query)
            
            # Buscar en Qdrant
            results = self.vector_memory.search(
                query_embedding=query_embedding,
                limit=limit,
                collection_name=self.memory_collection
            )
            
            # Extraer textos de los resultados
            facts = []
            for result in results:
                if result['score'] > 0.5:  # Umbral de similitud
                    fact = result['payload'].get('text', '')
                    if fact:
                        facts.append(fact)
            
            if facts:
                self.logger.info(f"✅ Encontrados {len(facts)} hechos relevantes")
            else:
                self.logger.info("ℹ️ No se encontraron hechos relevantes")
            
            return facts
            
        except Exception as e:
            self.logger.error(f"❌ Error en recall: {e}")
            return []
    
    def get_all_memories(
        self,
        user_id: str = "default_user"
    ) -> List[str]:
        """
        Obtiene todas las memorias del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de todas las memorias
        """
        try:
            # Esta es una operación costosa, usar con cuidado
            # Por ahora retornamos las más recientes
            dummy_embedding = [0.0] * settings.EMBEDDING_DIM
            
            results = self.vector_memory.search(
                query_embedding=dummy_embedding,
                limit=100,
                collection_name=self.memory_collection
            )
            
            memories = [r['payload'].get('text', '') for r in results if r['payload'].get('text')]
            
            return memories
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo memorias: {e}")
            return []
    
    def get_context(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 3
    ) -> str:
        """
        Obtiene contexto de memoria formateado para el LLM.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            limit: Número de memorias a incluir
            
        Returns:
            Contexto formateado como string
        """
        facts = self.recall(query, user_id, limit)
        
        if not facts:
            return ""
        
        context = "### 🧠 INFORMACIÓN RECORDADA:\n\n"
        
        for i, fact in enumerate(facts, 1):
            context += f"{i}. {fact}\n"
        
        context += "\n---\n"
        
        return context
    
    def clear_user_memories(
        self,
        user_id: str = "default_user"
    ) -> Dict[str, Any]:
        """
        Borra todas las memorias de un usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Resultado de la operación
        """
        try:
            # Nota: Qdrant no tiene forma fácil de borrar por filtro
            # Esta funcionalidad requeriría extensión
            self.logger.warning("clear_user_memories no implementado completamente")
            return {
                'success': False,
                'message': 'Función no implementada'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Singleton
_simple_memory_service = None


def get_simple_memory_service(
    embedding_service,
    vector_memory,
    db_manager=None
) -> SimpleMemoryService:
    """
    Obtiene la instancia singleton del servicio de memoria.
    
    Args:
        embedding_service: Servicio de embeddings
        vector_memory: Vector memory (Qdrant)
        db_manager: Database manager (opcional)
    
    Returns:
        Instancia de SimpleMemoryService
    """
    global _simple_memory_service
    if _simple_memory_service is None:
        _simple_memory_service = SimpleMemoryService(
            embedding_service=embedding_service,
            vector_memory=vector_memory,
            db_manager=db_manager
        )
    return _simple_memory_service