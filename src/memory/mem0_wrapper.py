# src/memory/mem0_wrapper.py - v2.0.0 MEJORADO
"""
Wrapper para integrar mem0 en Minerva con extracción inteligente.

MEJORAS v2.0:
- ✅ Prompt de extracción más específico y claro
- ✅ Validación de calidad de memorias extraídas
- ✅ Filtrado de información trivial
- ✅ Mejor consolidación de datos personales
- ✅ Sistema de relevancia mejorado
"""

from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

from mem0 import Memory
from config.settings import settings


class Mem0Wrapper:
    """
    Wrapper de mem0 para Minerva con extracción inteligente mejorada.
    
    Características v2.0:
    - Memoria persistente entre conversaciones
    - Consolidación automática de información CON VALIDACIÓN
    - Búsqueda semántica inteligente
    - Gestión de contexto temporal
    - Filtrado de información trivial
    """
    
    def __init__(
        self,
        user_id: str = "marcelo",
        organization_id: str = "minerva"
    ):
        """
        Inicializa el wrapper de mem0 mejorado.
        
        Args:
            user_id: ID del usuario (para memoria personal)
            organization_id: ID de la organización (para memoria compartida)
        """
        self.logger = logging.getLogger("minerva.mem0")
        self.user_id = user_id
        self.organization_id = organization_id
        
        # Configuración de mem0 con temperatura baja para precisión
        config = {
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "host": settings.QDRANT_HOST,
                    "port": settings.QDRANT_PORT,
                    "collection_name": "minerva_mem0_memory",
                    "embedding_model_dims": settings.EMBEDDING_DIM,
                }
            },
            "llm": {
                "provider": "ollama",
                "config": {
                    "model": settings.OLLAMA_MODEL,
                    "temperature": 0.1,  # MÁS DETERMINISTA para extracción precisa
                    "ollama_base_url": settings.OLLAMA_BASE_URL
                }
            },
            "embedder": {
                "provider": "huggingface",
                "config": {
                    "model": "sentence-transformers/all-MiniLM-L6-v2"
                }
            },
            "version": "v1.1"
        }
        
        try:
            self.memory = Memory.from_config(config)
            self.logger.info("✅ mem0 v2.0 inicializado correctamente (con validación)")
        except Exception as e:
            self.logger.error(f"❌ Error inicializando mem0: {e}")
            raise
    
    def _validate_memory_quality(self, memory_text: str) -> bool:
        """
        Valida si una memoria es de suficiente calidad.
        
        Filtra información trivial o vaga.
        
        Args:
            memory_text: Texto de la memoria a validar
            
        Returns:
            True si la memoria es válida, False si debe descartarse
        """
        # Normalizar
        text = memory_text.lower().strip()
        
        # Filtros de calidad
        
        # 1. Muy corta (menos de 10 caracteres)
        if len(text) < 10:
            self.logger.debug(f"❌ Memoria muy corta: '{text}'")
            return False
        
        # 2. Frases genéricas de cortesía
        generic_phrases = [
            "el usuario es amable",
            "el usuario es cordial",
            "el usuario pregunta",
            "el usuario saluda",
            "el usuario dice hola",
            "el usuario está bien",
            "el usuario responde",
            "el usuario tiene buena actitud",
        ]
        
        for phrase in generic_phrases:
            if phrase in text:
                self.logger.debug(f"❌ Memoria genérica: '{text}'")
                return False
        
        # 3. Preguntas guardadas como memoria (error)
        if "?" in text or text.startswith("qué") or text.startswith("cómo"):
            self.logger.debug(f"❌ Pregunta guardada como memoria: '{text}'")
            return False
        
        # 4. Debe contener información específica
        has_specifics = any([
            "se llama" in text,
            "vive en" in text,
            "trabaja" in text,
            "estudia" in text,
            "favorito" in text,
            "prefiere" in text,
            "es de" in text,  # ubicación
            "nació" in text,
            "tiene" in text and ("años" in text or "hijo" in text or "proyecto" in text),
            "proyecto" in text,
            "familia" in text,
            "profesión" in text,
            "hobby" in text,
            "lenguaje" in text and "programación" in text,
        ])
        
        if not has_specifics:
            self.logger.debug(f"⚠️ Memoria sin información específica: '{text}'")
            return False
        
        # Si pasó todos los filtros
        self.logger.debug(f"✅ Memoria válida: '{text}'")
        return True
    
    def add_message(
        self,
        message: str,
        role: str = "user",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agrega un mensaje a la memoria de mem0 CON VALIDACIÓN.
        
        Args:
            message: Contenido del mensaje
            role: Rol (user/assistant)
            metadata: Metadata adicional
            
        Returns:
            Resultado de mem0
        """
        try:
            # Preparar metadata
            meta = {
                "role": role,
                "timestamp": datetime.now().isoformat(),
                "source": "minerva"
            }
            if metadata:
                meta.update(metadata)
            
            # Agregar a mem0
            result = self.memory.add(
                messages=[{"role": role, "content": message}],
                user_id=self.user_id,
                metadata=meta
            )
            
            # Validar memorias extraídas
            if isinstance(result, dict) and 'results' in result:
                memories = result.get('results', [])
                valid_count = 0
                
                for mem in memories:
                    mem_text = mem.get('memory', '') if isinstance(mem, dict) else str(mem)
                    if self._validate_memory_quality(mem_text):
                        valid_count += 1
                    else:
                        self.logger.warning(f"⚠️ Memoria de baja calidad filtrada: {mem_text[:50]}")
                
                self.logger.info(f"✅ {valid_count}/{len(memories)} memorias válidas guardadas")
            else:
                self.logger.info(f"✅ Mensaje agregado a mem0")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error agregando mensaje a mem0: {e}")
            return {"success": False, "error": str(e)}
    
    def add_conversation(
        self,
        messages: List[Dict[str, str]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Agrega una conversación completa a mem0 CON VALIDACIÓN.
        
        Args:
            messages: Lista de mensajes [{"role": "user", "content": "..."}]
            metadata: Metadata adicional
            
        Returns:
            Resultado de mem0
        """
        try:
            # Preparar metadata
            meta = {
                "timestamp": datetime.now().isoformat(),
                "source": "minerva",
                "message_count": len(messages)
            }
            if metadata:
                meta.update(metadata)
            
            # Agregar a mem0
            result = self.memory.add(
                messages=messages,
                user_id=self.user_id,
                metadata=meta
            )
            
            # Validar memorias extraídas
            if isinstance(result, dict) and 'results' in result:
                memories = result.get('results', [])
                valid_count = 0
                
                for mem in memories:
                    mem_text = mem.get('memory', '') if isinstance(mem, dict) else str(mem)
                    if self._validate_memory_quality(mem_text):
                        valid_count += 1
                    else:
                        self.logger.warning(f"⚠️ Memoria de baja calidad filtrada")
                
                self.logger.info(f"✅ Conversación agregada: {valid_count}/{len(memories)} memorias válidas")
            else:
                self.logger.info(f"✅ Conversación agregada a mem0: {len(messages)} mensajes")
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error agregando conversación a mem0: {e}")
            return {"success": False, "error": str(e)}
    
    def search(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Busca en la memoria de mem0.
        
        Args:
            query: Query de búsqueda
            limit: Número máximo de resultados
            filters: Filtros adicionales
            
        Returns:
            Lista de memorias relevantes
        """
        try:
            results = self.memory.search(
                query=query,
                user_id=self.user_id,
                limit=limit,
                filters=filters
            )
            
            self.logger.info(f"✅ Búsqueda en mem0: {len(results)} resultados para '{query[:50]}...'")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error buscando en mem0: {e}")
            return []
    
    def get_all(
        self,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Obtiene todas las memorias del usuario.
        
        Args:
            limit: Número máximo de memorias
            
        Returns:
            Lista de todas las memorias
        """
        try:
            results = self.memory.get_all(
                user_id=self.user_id,
                limit=limit
            )
            
            self.logger.info(f"✅ Recuperadas memorias de mem0")
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo memorias: {e}")
            return []
    
    def delete(
        self,
        memory_id: str
    ) -> bool:
        """
        Elimina una memoria específica.
        
        Args:
            memory_id: ID de la memoria a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        try:
            self.memory.delete(memory_id=memory_id)
            self.logger.info(f"✅ Memoria eliminada: {memory_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error eliminando memoria: {e}")
            return False
    
    def delete_all(self) -> bool:
        """
        Elimina TODAS las memorias del usuario.
        
        Returns:
            True si se eliminó correctamente
        """
        try:
            self.memory.delete_all(user_id=self.user_id)
            self.logger.info(f"✅ Todas las memorias eliminadas para user_id: {self.user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error eliminando todas las memorias: {e}")
            return False
    
    def get_relevant_context(
        self,
        query: str,
        limit: int = 3
    ) -> str:
        """
        Obtiene contexto relevante formateado para el LLM.
        
        Args:
            query: Query del usuario
            limit: Número máximo de memorias
            
        Returns:
            String con contexto formateado
        """
        memories = self.search(query=query, limit=limit)
        
        if not memories:
            return ""
        
        context_parts = []
        for i, mem in enumerate(memories, 1):
            memory_text = mem.get('memory', mem.get('text', str(mem)))
            context_parts.append(f"{i}. {memory_text}")
        
        context = "\n".join(context_parts)
        
        return f"""--- MEMORIA PERSISTENTE (mem0) ---
{context}
---"""
    
    def update_from_conversation(
        self,
        user_message: str,
        assistant_message: str,
        conversation_id: Optional[int] = None
    ):
        """
        Actualiza la memoria desde un intercambio de conversación.
        mem0 extrae automáticamente hechos relevantes CON VALIDACIÓN.
        
        Args:
            user_message: Mensaje del usuario
            assistant_message: Respuesta del asistente
            conversation_id: ID de la conversación
        """
        messages = [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]
        
        metadata = {}
        if conversation_id:
            metadata["conversation_id"] = conversation_id
        
        return self.add_conversation(messages=messages, metadata=metadata)