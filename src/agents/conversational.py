# src/agents/conversational.py - v5.0.0 - Con fecha actual dinámica
"""
Agente conversacional de Minerva CON MEMORIA PERSISTENTE REAL.
Usa LangChain SQLChatMessageHistory + extracción de hechos con Ollama.
Inyecta fecha actual en cada interacción.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import requests
import time
from datetime import datetime
import locale

from .base_agent import BaseAgent, AgentExecutionError
from config.settings import settings


class ConversationalAgent(BaseAgent):
    """
    Agente para conversación general CON MEMORIA PERSISTENTE REAL.
    
    Características:
    - LangChain SQLChatMessageHistory para historial completo
    - Extracción automática de hechos con Ollama
    - Qdrant para almacenar hechos con embeddings
    - Recuperación inteligente de contexto pasado
    - Fecha actual siempre actualizada en el contexto
    """
    
    def __init__(
        self,
        model_name: str = "phi3",
        temperature: float = 0.3,
        log_dir: Optional[Path] = None,
        db_manager = None,
        embedding_service = None,
        vector_memory = None,
        extraction_interval: int = 5,
        memory_service = None
    ):
        """
        Inicializa el agente conversacional con memoria.
        
        Args:
            model_name: Modelo de Ollama
            temperature: Creatividad (0.0-1.0)
            log_dir: Directorio de logs
            db_manager: Gestor de base de datos
            embedding_service: Servicio de embeddings
            vector_memory: Almacenamiento vectorial
            extraction_interval: Cada cuántos mensajes extraer hechos
            memory_service: IGNORADO (compatibilidad)
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
        
        # Componentes de memoria
        self.langchain_memory = None
        self.fact_memory = None
        
        # Inicializar sistema de hechos si hay componentes
        if embedding_service and vector_memory:
            try:
                from src.memory.fact_extractor import FactExtractor, FactMemoryService
                
                fact_extractor = FactExtractor(
                    model_name=model_name,
                    base_url=self.base_url,
                    temperature=0.3,
                    db_manager=db_manager
                )
                
                self.fact_memory = FactMemoryService(
                    fact_extractor=fact_extractor,
                    vector_memory=vector_memory,
                    embedding_service=embedding_service,
                    extraction_interval=1
                )
                
                self.logger.info("✅ Sistema de hechos inicializado")
                
            except Exception as e:
                self.logger.error(f"❌ Error inicializando sistema de hechos: {e}")
                self.fact_memory = None
        else:
            self.logger.warning("⚠️ Sin embedding_service o vector_memory, memoria de hechos deshabilitada")
        
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
            from src.database.prompt_manager import PromptManager
            pm = PromptManager(self.db_manager)
            history = pm.get_prompt_history('conversational', 'system_prompt', limit=1)
            version_num = history[0].version if history else "?"
            
            self.logger.info("=" * 60)
            self.logger.info(f"📝 PROMPT: conversational/system_prompt v{version_num}")
            
            if "MEMORIA Y CONTEXTO" in self.system_prompt:
                self.logger.info("✅ Versión correcta (con MEMORIA Y CONTEXTO)")
            else:
                self.logger.warning("⚠️ Versión antigua (sin MEMORIA Y CONTEXTO)")
            self.logger.info("=" * 60)
            
            self.logger.info("✅ Prompts cargados correctamente")
                
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
    
    def _build_prompt_with_memory(
        self,
        user_message: str,
        history_text: str,
        facts: List[str]
    ) -> str:
        """
        Construye prompt con historial reciente + hechos pasados + FECHA ACTUAL.
        
        Args:
            user_message: Mensaje actual
            history_text: Historial formateado
            facts: Hechos relevantes del pasado
            
        Returns:
            Prompt completo
        """
        prompt_parts = []
        
        # 1. SYSTEM PROMPT
        prompt_parts.append(self.system_prompt)
        
        # 2. FECHA ACTUAL (CRÍTICO)
        prompt_parts.append(self._get_current_date_context())
        
        # 3. HECHOS del pasado (si existen)
        if facts:
            facts_text = "\n--- INFORMACIÓN RELEVANTE DEL PASADO ---\n"
            facts_text += "\n".join(f"• {fact}" for fact in facts)
            facts_text += "\n---\n"
            prompt_parts.append(facts_text)
            self.logger.info(f"✅ {len(facts)} hechos agregados al contexto")
        
        # 4. HISTORIAL reciente
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
        Procesa mensaje con memoria persistente completa + fecha actual.
        
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
            
            # 2. Recuperar hechos relevantes (de TODAS las conversaciones pasadas)
            facts = []
            if self.fact_memory:
                facts = self.fact_memory.get_relevant_facts(
                    query=user_message,
                    limit=5
                )
            
            # 3. Obtener historial reciente (de esta conversación)
            history_text = langchain_mem.get_formatted_history(limit=10)
            
            # 4. Construir prompt con memoria completa + FECHA ACTUAL
            prompt = self._build_prompt_with_memory(
                user_message=user_message,
                history_text=history_text,
                facts=facts
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
                timeout=60
            )
            
            response.raise_for_status()
            result = response.json()
            answer = result.get('response', '').strip()
            
            if not answer:
                raise AgentExecutionError("El modelo no generó respuesta")
            
            # 6. Guardar en LangChain memory
            langchain_mem.add_user_message(user_message)
            langchain_mem.add_ai_message(answer)
            
            # 7. Agregar al sistema de hechos (extrae cada N mensajes)
            if self.fact_memory:
                self.fact_memory.add_exchange(user_message, answer)
            
            # 8. Logging
            duration = time.time() - start_time
            self.log_interaction(
                input_text=user_message,
                output_text=answer,
                metadata={
                    'model': self.model_name,
                    'duration_seconds': duration,
                    'used_facts': len(facts),
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