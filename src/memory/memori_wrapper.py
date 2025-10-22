# src/memory/memori_wrapper.py
"""
Wrapper para Memori que mantiene compatibilidad con la interfaz de Minerva.
"""

from typing import List, Dict, Any, Optional
import logging

try:
    from memori import Memori
    MEMORI_AVAILABLE = True
except ImportError:
    MEMORI_AVAILABLE = False
    logging.warning("⚠️ memorisdk no está instalado. Instala con: pip install memorisdk")


class MemoriWrapper:
    """
    Wrapper que adapta Memori a la interfaz de Minerva.
    
    Proporciona API compatible con SimpleMemoryService pero usando Memori internamente.
    """
    
    def __init__(
        self,
        embedding_service=None,
        vector_memory=None,
        db_manager=None,
        database_path: str = "data/sqlite/minerva_memory.db"
    ):
        """
        Inicializa el wrapper de Memori.
        
        Args:
            embedding_service: Servicio de embeddings (compatibilidad)
            vector_memory: VectorMemory (compatibilidad)
            db_manager: Database manager (compatibilidad)
            database_path: Ruta a la base de datos SQLite
        """
        self.logger = logging.getLogger("minerva.memori_wrapper")
        self.embedding_service = embedding_service
        self.vector_memory = vector_memory
        self.db_manager = db_manager
        
        if not MEMORI_AVAILABLE:
            self.logger.error("❌ memorisdk no disponible")
            self.memori = None
            return
        
        try:
            # Inicializar Memori con SQLite
            self.memori = Memori(
                database_connect=f"sqlite:///{database_path}",
                conscious_ingest=True,  # Memoria esencial persistente
                auto_ingest=False,  # Sin búsqueda dinámica (para simplificar)
                namespace="minerva",
                verbose=False
            )
            
            # NO llamar enable() aquí porque intercepta todas las llamadas LLM
            # En su lugar, grabaremos manualmente las conversaciones
            
            self.logger.info("✅ MemoriWrapper inicializado correctamente")
            
        except Exception as e:
            self.logger.error(f"❌ Error inicializando Memori: {e}")
            import traceback
            traceback.print_exc()
            self.memori = None
    
    def add_memory(
        self,
        text: str,
        user_id: str = "default_user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agrega información a la memoria.
        
        Args:
            text: Texto a memorizar
            user_id: ID del usuario
            metadata: Metadata adicional
            
        Returns:
            Resultado de la operación
        """
        if not self.memori:
            return {'success': False, 'error': 'Memori no disponible'}
        
        try:
            self.logger.info(f"💾 Guardando en memoria: {text[:100]}...")
            
            # Guardar en memoria de Memori
            # Usar add_memory para agregar memoria explícita
            result = self.memori.add_memory(
                content=text,
                category="interaction",
                importance=0.7,
                metadata=metadata or {}
            )
            
            return {
                'success': True,
                'message': 'Memoria guardada',
                'memory_id': result.get('id') if result else None
            }
            
        except Exception as e:
            self.logger.error(f"Error en add_memory: {e}")
            return {'success': False, 'error': str(e)}
    
    def record_conversation(
        self,
        user_input: str,
        ai_output: str,
        conversation_id: Optional[int] = None
    ):
        """
        Graba una conversación completa en Memori.
        
        Args:
            user_input: Mensaje del usuario
            ai_output: Respuesta de Minerva
            conversation_id: ID de conversación (opcional)
        """
        if not self.memori:
            return
        
        try:
            self.logger.info("💾 Grabando conversación en Memori...")
            
            # Grabar conversación en Memori
            self.memori.record_conversation(
                user_input=user_input,
                ai_output=ai_output,
                model="phi3",
                metadata={
                    'conversation_id': conversation_id,
                    'agent': 'minerva'
                }
            )
            
            self.logger.info("✅ Conversación grabada")
            
        except Exception as e:
            self.logger.error(f"Error grabando conversación: {e}")
    
    def get_memory_context(
        self,
        query: str,
        user_id: str = "default_user",
        limit: int = 3
    ) -> str:
        """
        Obtiene contexto de memoria relevante.
        
        Args:
            query: Consulta del usuario
            user_id: ID del usuario
            limit: Número de memorias
            
        Returns:
            Contexto formateado
        """
        if not self.memori:
            return ""
        
        try:
            self.logger.info(f"🔍 Buscando memorias relevantes para: {query[:50]}...")
            
            # Buscar memorias relevantes
            memories = self.memori.retrieve_context(
                query=query,
                limit=limit
            )
            
            if not memories:
                return ""
            
            # Formatear contexto
            context_parts = ["--- MEMORIA PERSISTENTE ---"]
            
            for mem in memories:
                if isinstance(mem, dict):
                    content = mem.get('content', mem.get('memory', str(mem)))
                    context_parts.append(f"• {content}")
                else:
                    context_parts.append(f"• {str(mem)}")
            
            context_parts.append("---")
            
            context = "\n".join(context_parts)
            self.logger.info(f"✅ Encontradas {len(memories)} memorias relevantes")
            
            return context
            
        except Exception as e:
            self.logger.error(f"Error en get_memory_context: {e}")
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
        if not self.memori:
            return []
        
        try:
            self.logger.info("📋 Obteniendo todas las memorias...")
            
            # Obtener estadísticas de memoria
            stats = self.memori.get_memory_stats()
            
            memories = []
            memories.append(f"Total de conversaciones: {stats.get('total_chats', 0)}")
            memories.append(f"Memoria de corto plazo: {stats.get('short_term_memories', 0)}")
            memories.append(f"Memoria de largo plazo: {stats.get('long_term_memories', 0)}")
            
            return memories
            
        except Exception as e:
            self.logger.error(f"Error en get_all_memories: {e}")
            return []


# Singleton
_memori_wrapper = None


def get_memory_service(
    embedding_service=None,
    vector_memory=None,
    db_manager=None,
    database_path: str = "data/sqlite/minerva_memory.db"
) -> Optional[MemoriWrapper]:
    """
    Obtiene la instancia singleton del Memori wrapper.
    
    Args:
        embedding_service: Servicio de embeddings
        vector_memory: Vector memory
        db_manager: Database manager
        database_path: Ruta a la base de datos
        
    Returns:
        Instancia de MemoriWrapper o None si falla
    """
    global _memori_wrapper
    
    if _memori_wrapper is None:
        _memori_wrapper = MemoriWrapper(
            embedding_service=embedding_service,
            vector_memory=vector_memory,
            db_manager=db_manager,
            database_path=database_path
        )
        
        # Verificar que se inicializó correctamente
        if _memori_wrapper.memori is None:
            logging.error("❌ No se pudo inicializar Memori")
            return None
    
    return _memori_wrapper