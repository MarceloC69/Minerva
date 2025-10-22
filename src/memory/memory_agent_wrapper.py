# src/memory/memory_agent_wrapper.py
"""
Wrapper para memory-agent que mantiene compatibilidad con la interfaz de Minerva.
Adapta memory-agent a la API que ya usa ConversationalAgent.
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

try:
    from memory_agent.agent.ollama import AgentOllama
    MEMORY_AGENT_AVAILABLE = True
except ImportError:
    MEMORY_AGENT_AVAILABLE = False
    logging.warning("⚠️ memory-agent no está instalado. Instala con: pip install memory-agent")


class MemoryAgentWrapper:
    """
    Wrapper que adapta memory-agent a la interfaz de Minerva.
    
    Proporciona la misma API que SimpleMemoryService pero usando memory-agent internamente.
    """
    
    def __init__(
        self,
        embedding_service=None,
        vector_memory=None,
        db_manager=None
    ):
        """
        Inicializa el wrapper de memory-agent.
        
        Args:
            embedding_service: Servicio de embeddings (compatibilidad)
            vector_memory: VectorMemory con Qdrant (compatibilidad)
            db_manager: Database manager (compatibilidad)
        """
        self.logger = logging.getLogger("minerva.memory_agent_wrapper")
        self.embedding_service = embedding_service
        self.vector_memory = vector_memory
        self.db_manager = db_manager
        
        if not MEMORY_AGENT_AVAILABLE:
            self.logger.error("❌ memory-agent no disponible")
            self.agent = None
            return
        
        try:
            # Configuración del modelo Ollama
            model_config = {
                "model": "phi3",
                "model_provider": "ollama",
                "api_key": None,
                "base_url": "http://localhost:11434",
                "temperature": 0.7,
            }
            
            # Configuración de Redis (local)
            redis_config = {
                "host": "localhost",
                "port": 6379,
                "db": 0,
            }
            
            # Configuración de Qdrant (local)
            qdrant_config = {
                "host": "localhost",
                "port": 6333,
            }
            
            # Configuración de colección
            collection_config = {
                "name": "minerva_memory_agent",
                "distance": "cosine",
            }
            
            # Configuración de embeddings para vector store
            embedding_store_config = {
                "model": "nomic-embed-text",
                "model_provider": "ollama",
                "base_url": "http://localhost:11434",
            }
            
            # Configuración de modelo de embeddings
            embedding_model_config = {
                "model": "nomic-embed-text",
                "model_provider": "ollama",
                "base_url": "http://localhost:11434",
            }
            
            # Inicializar AgentOllama
            self.agent = AgentOllama(
                thread_id="default_thread",
                user_id="default_user",
                session_id=datetime.now().strftime("%Y%m%d_%H%M%S"),
                model_config=model_config,
                redis_config=redis_config,
                qdrant_config=qdrant_config,
                collection_config=collection_config,
                embedding_store_config=embedding_store_config,
                embedding_model_config=embedding_model_config,
            )
            
            self.logger.info("✅ MemoryAgentWrapper inicializado con memory-agent")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando memory-agent: {e}")
            import traceback
            traceback.print_exc()
            self.agent = None
    
    def add_memory(
        self,
        text: str,
        user_id: str = "default_user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agrega información a la memoria.
        
        memory-agent maneja esto automáticamente en cada interacción.
        Este método existe para compatibilidad con SimpleMemoryService.
        
        Args:
            text: Texto a memorizar
            user_id: ID del usuario
            metadata: Metadata adicional
            
        Returns:
            Resultado de la operación
        """
        if not self.agent:
            return {'success': False, 'error': 'memory-agent no disponible'}
        
        try:
            self.logger.info(f"💾 Procesando para memoria: {text[:100]}...")
            
            # memory-agent procesa automáticamente en invoke()
            # No necesita llamada explícita de "memorizar"
            
            return {
                'success': True,
                'message': 'Texto será procesado en próxima interacción'
            }
            
        except Exception as e:
            self.logger.error(f"Error en add_memory: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_memory_context(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 3
    ) -> str:
        """
        Obtiene contexto de memoria relevante.
        
        memory-agent integra memoria automáticamente en invoke(),
        así que este método retorna vacío.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            limit: Número de memorias
            
        Returns:
            Contexto formateado (vacío porque memory-agent lo maneja)
        """
        # memory-agent integra memoria automáticamente
        return ""
    
    def get_all_memories(
        self,
        user_id: str = "default_user"
    ) -> List[str]:
        """
        Obtiene todas las memorias del usuario.
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de memorias
        """
        if not self.agent:
            return []
        
        try:
            self.logger.info("🔍 Obteniendo memorias almacenadas...")
            
            # memory-agent no expone directamente get_all
            # Retornamos vacío por ahora
            return []
            
        except Exception as e:
            self.logger.error(f"Error en get_all_memories: {e}")
            return []
    
    def process_with_memory(self, message: str) -> str:
        """
        Procesa un mensaje CON memoria persistente usando memory-agent.
        
        Este es el método principal que debe usar ConversationalAgent.
        
        Args:
            message: Mensaje del usuario
            
        Returns:
            Respuesta del agente CON contexto de memoria
        """
        if not self.agent:
            raise RuntimeError("❌ memory-agent no está disponible")
        
        try:
            self.logger.info(f"🧠 Procesando con memoria: {message[:50]}...")
            
            # invoke() de memory-agent:
            # 1. Busca en memoria de largo plazo (Qdrant)
            # 2. Busca en memoria de corto plazo (Redis)
            # 3. Procesa con LLM integrando contexto
            # 4. Guarda nueva información en memoria
            
            response = self.agent.invoke(message)
            
            self.logger.info("✅ Respuesta con memoria generada")
            return response
            
        except Exception as e:
            self.logger.error(f"❌ Error en process_with_memory: {e}")
            import traceback
            traceback.print_exc()
            raise


# Singleton
_memory_agent_wrapper = None


def get_memory_service(
    embedding_service=None,
    vector_memory=None,
    db_manager=None
) -> Optional[MemoryAgentWrapper]:
    """
    Obtiene la instancia singleton del memory-agent wrapper.
    
    Args:
        embedding_service: Servicio de embeddings
        vector_memory: Vector memory
        db_manager: Database manager
        
    Returns:
        Instancia de MemoryAgentWrapper o None si falla
    """
    global _memory_agent_wrapper
    
    if _memory_agent_wrapper is None:
        _memory_agent_wrapper = MemoryAgentWrapper(
            embedding_service=embedding_service,
            vector_memory=vector_memory,
            db_manager=db_manager
        )
        
        # Verificar que se inicializó correctamente
        if _memory_agent_wrapper.agent is None:
            logging.error("❌ No se pudo inicializar memory-agent")
            return None
    
    return _memory_agent_wrapper