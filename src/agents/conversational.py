# src/agents/conversational.py - v6.1.0 - Con mem0 integrado (CORREGIDO)
"""
Agente conversacional de Minerva CON MEMORIA PERSISTENTE (mem0).
Usa LangChain SQLChatMessageHistory para historial + mem0 para memoria a largo plazo.
FIX: Eliminado código duplicado, guardado de mem0 funcional
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import requests
import time
from datetime import datetime
import locale
import logging

from .base_agent import BaseAgent, AgentExecutionError
from config.settings import settings

logger = logging.getLogger(__name__)


class ConversationalAgent(BaseAgent):
    """
    Agente para conversación general CON MEMORIA PERSISTENTE (mem0).
    
    Características:
    - LangChain SQLChatMessageHistory para historial de la conversación actual
    - mem0 para memoria persistente entre conversaciones
    - Fecha actual siempre actualizada en el contexto
    - Extracción automática de información relevante
    """
    
    def __init__(
        self,
        model_name: str = "phi3",
        temperature: float = 0.3,
        log_dir: Optional[Path] = None,
        db_manager = None,
        embedding_service = None,
        vector_memory = None,
        memory_service = None  # ← mem0 service
    ):
        """
        Inicializa el agente conversacional con memoria.
        
        Args:
            model_name: Modelo de Ollama
            temperature: Creatividad (0.0-1.0)
            log_dir: Directorio de logs
            db_manager: Gestor de base de datos
            embedding_service: Servicio de embeddings (legacy, ignorado)
            vector_memory: Almacenamiento vectorial (legacy, ignorado)
            memory_service: Servicio de memoria (mem0) - NUEVO
        """
        super().__init__(
            name="conversational_agent",
            agent_type="conversational",
            log_dir=log_dir
        )
        
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = settings.OLLAMA_BASE_URL
        self.db_manager = db_manager
        
        # Sistema de memoria con mem0
        self.memory_service = memory_service
        
        if self.memory_service:
            self.logger.info("✅ mem0 disponible para memoria persistente")
        else:
            self.logger.warning("⚠️ Sin memory_service, memoria persistente deshabilitada")
        
        # Cargar prompts desde DB
        self._load_prompts()
        
        self.logger.info(f"LLM configurado: {model_name}")
    
    def _load_prompts(self):
        """Carga prompts desde la base de datos."""
        if not self.db_manager:
            error_msg = "❌ CRITICAL: No hay db_manager disponible"
            self.logger.error(error_msg)
            raise AgentExecutionError(error_msg)
        
        try:
            from src.database.prompt_manager import PromptManager
            prompt_manager = PromptManager(self.db_manager)
            
            self.system_prompt = prompt_manager.get_active_prompt(
                agent_type='conversational',
                prompt_name='system_prompt'
            )
            
            if not self.system_prompt:
                error_msg = "❌ CRITICAL: No se encontró 'system_prompt'"
                self.logger.error(error_msg)
                raise AgentExecutionError(error_msg)
            
            # LOG: Mostrar qué prompt se cargó
            history = prompt_manager.get_prompt_history('conversational', 'system_prompt', limit=1)
            version_num = history[0].version if history else "?"
            
            self.logger.info("=" * 60)
            self.logger.info(f"📝 PROMPT: conversational/system_prompt v{version_num}")
            self.logger.info("=" * 60)
            
        except AgentExecutionError:
            raise
        except Exception as e:
            error_msg = f"❌ CRITICAL: Error cargando prompts: {e}"
            self.logger.error(error_msg)
            raise AgentExecutionError(error_msg)
    
    def _get_langchain_memory(self, conversation_id: int):
        """
        Obtiene o crea LangChain memory para esta conversación.
        
        Args:
            conversation_id: ID de la conversación
            
        Returns:
            LangChainMemoryWrapper
        """
        from src.memory.langchain_memory import LangChainMemoryWrapper
        
        return LangChainMemoryWrapper(
            db_path=str(settings.SQLITE_PATH),
            conversation_id=conversation_id
        )
    
    def _get_current_date_context(self) -> str:
        """
        Genera el contexto de fecha actual en formato legible.
        
        Returns:
            String con fecha actual formateada
        """
        now = datetime.now()
        
        # Intentar usar locale español
        try:
            locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
        except:
            try:
                locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
            except:
                pass  # Usar default si falla
        
        # Nombres de días y meses en español (fallback)
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
                'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
        
        dia_semana = dias[now.weekday()]
        mes = meses[now.month - 1]
        
        fecha_context = f"""
CONTEXTO TEMPORAL (CRÍTICO - USAR SIEMPRE):
- Fecha actual: {dia_semana} {now.day} de {mes} de {now.year}
- Año actual: {now.year}
- Hora actual: {now.strftime('%H:%M')}

IMPORTANTE: Esta es la fecha REAL de hoy. Úsala para cualquier cálculo temporal.
"""
        return fecha_context
    
    def _get_mem0_context(self, query: str) -> str:
        """
        Obtiene contexto relevante desde mem0.
        
        Args:
            query: Query del usuario
            
        Returns:
            String con contexto formateado (vacío si no hay memoria)
        """
        if not self.memory_service:
            return ""
        
        try:
            # Buscar memorias relevantes en mem0
            memories = self.memory_service.search(query=query, limit=3)
            
            if not memories:
                return ""
            
            # Formatear memorias - FIX: manejar strings y dicts
            context_parts = []
            for i, mem in enumerate(memories, 1):
                if isinstance(mem, dict):
                    memory_text = mem.get('memory', mem.get('text', str(mem)))
                else:
                    memory_text = str(mem)
                context_parts.append(f"{i}. {memory_text}")
            
            context = "\n".join(context_parts)
            
            return f"""
--- MEMORIA PERSISTENTE (mem0) ---
{context}
---
"""
        except Exception as e:
            self.logger.error(f"Error obteniendo contexto de mem0: {e}")
            return ""
    
    def _build_prompt_with_memory(
        self,
        user_message: str,
        history_text: str,
        mem0_context: str
    ) -> str:
        """
        Construye prompt con historial reciente + memoria persistente + FECHA ACTUAL.
        
        Args:
            user_message: Mensaje actual
            history_text: Historial formateado
            mem0_context: Contexto de mem0
            
        Returns:
            Prompt completo
        """
        prompt_parts = []
        
        # 1. SYSTEM PROMPT
        prompt_parts.append(self.system_prompt)
        
        # 2. FECHA ACTUAL (CRÍTICO)
        prompt_parts.append(self._get_current_date_context())
        
        # 3. MEMORIA PERSISTENTE (mem0) - Si existe
        if mem0_context:
            prompt_parts.append(mem0_context)
            self.logger.info("✅ Contexto de mem0 agregado")
        
        # 4. HISTORIAL reciente (de esta conversación)
        if history_text:
            prompt_parts.append(history_text)
        
        # 5. MENSAJE actual
        prompt_parts.append(f"\nUsuario: {user_message}\n\nMinerva:")
        
        return "\n".join(prompt_parts)
    
    def chat(
        self,
        user_message: str,
        context: Optional[str] = None,
        conversation_id: Optional[int] = None
    ) -> str:
        """
        Procesa mensaje con memoria persistente completa (LangChain + mem0) + fecha actual.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (ignorado)
            conversation_id: ID de conversación
            
        Returns:
            Respuesta generada
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Procesando: {user_message[:100]}...")
            
            # Validar conversation_id
            if not conversation_id:
                raise AgentExecutionError("conversation_id es requerido")
            
            # 1. Inicializar LangChain memory para esta conversación
            langchain_mem = self._get_langchain_memory(conversation_id)
            
            # 2. Obtener contexto de mem0 (memoria persistente entre conversaciones)
            mem0_context = self._get_mem0_context(user_message)
            
            # 3. Obtener historial reciente (de esta conversación)
            history_text = langchain_mem.get_formatted_history(limit=10)
            
            # 4. Construir prompt con memoria completa + FECHA ACTUAL
            prompt = self._build_prompt_with_memory(
                user_message=user_message,
                history_text=history_text,
                mem0_context=mem0_context
            )
            
            # 5. Generar respuesta con Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": False
                },
                timeout=120
            )
            
            response.raise_for_status()
            result = response.json()
            answer = result.get('response', '').strip()
            
            if not answer:
                raise AgentExecutionError("El modelo no generó respuesta")
            
            # 6. Guardar en LangChain memory (historial de esta conversación)
            langchain_mem.add_user_message(user_message)
            langchain_mem.add_ai_message(answer)
            
            # 7. Actualizar mem0 (memoria persistente)
            # mem0 extrae automáticamente hechos relevantes
            if self.memory_service:
                try:
                    self.memory_service.update_from_conversation(
                        user_message=user_message,
                        assistant_message=answer,
                        conversation_id=conversation_id
                    )
                    self.logger.info("✅ Memoria persistente (mem0) actualizada")
                except Exception as e:
                    self.logger.error(f"Error actualizando mem0: {e}")
            
            # 8. Logging
            duration = time.time() - start_time
            self.log_interaction(
                input_text=user_message,
                output_text=answer,
                metadata={
                    'model': self.model_name,
                    'duration_seconds': duration,
                    'used_mem0': bool(mem0_context),
                    'message_count': langchain_mem.get_message_count(),
                    'current_date': datetime.now().isoformat()
                }
            )
            
            self.logger.info(f"✅ Respuesta generada ({duration:.2f}s)")
            return answer
            
        except requests.RequestException as e:
            error_msg = f"Error conectando con Ollama: {e}"
            self.logger.error(error_msg)
            raise AgentExecutionError(error_msg)
        
        except Exception as e:
            error_msg = f"Error procesando mensaje: {e}"
            self.logger.error(error_msg)
            raise AgentExecutionError(error_msg)