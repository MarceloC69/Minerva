# src/agents/conversational.py - Agente conversacional con memoria
"""
Agente conversacional de Minerva.
Maneja conversaciones generales y responde preguntas usando Ollama.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
import requests
import json
import time

from .base_agent import BaseAgent, AgentExecutionError
from config.settings import settings


class ConversationalAgent(BaseAgent):
    """
    Agente para conversación general.
    
    Características:
    - Conversación amigable y natural
    - Conexión directa con Ollama (sin CrewAI overhead)
    - Persistencia en SQLite
    - MEMORIA de conversaciones anteriores
    - Rápido y eficiente
    """
    
    def __init__(
        self,
        model_name: str = "phi3",
        temperature: float = 0.7,
        log_dir: Optional[Path] = None,
        db_manager = None
    ):
        """
        Inicializa el agente conversacional.
        
        Args:
            model_name: Modelo de Ollama a usar
            temperature: Creatividad de las respuestas (0.0-1.0)
            log_dir: Directorio para logs
            db_manager: Gestor de base de datos
        """
        # Llamar al constructor de BaseAgent correctamente
        super().__init__(
            name="conversational_agent",
            agent_type="conversational",
            log_dir=log_dir
        )
        
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = settings.OLLAMA_BASE_URL
        self.db_manager = db_manager
        
        self.logger.info(f"LLM configurado: {model_name}")
    
    def _build_prompt_with_history(
        self,
        user_message: str,
        history: List,
        context: Optional[str] = None
    ) -> str:
        """
        Construye el prompt incluyendo historial de conversación.
        
        Args:
            user_message: Mensaje actual del usuario
            history: Lista de mensajes anteriores (objetos Message)
            context: Contexto adicional opcional
            
        Returns:
            Prompt completo formateado
        """
        # System prompt directo
        system_prompt = (
            "Eres Minerva, un asistente personal amigable y servicial. "
            "Respondes de manera clara, concisa y natural. "
            "Mantienes el contexto de la conversación y recuerdas lo que el usuario te ha contado."
        )
        
        # Construir historial
        history_text = ""
        if history:
            history_text = "\n### Historial de conversación:\n"
            for msg in history[-10:]:  # Últimos 10 mensajes
                role = "Usuario" if msg.role == "user" else "Minerva"
                history_text += f"{role}: {msg.content}\n"
            history_text += "\n"
        
        # Construir prompt completo
        prompt_parts = [
            system_prompt,
            history_text,
        ]
        
        if context:
            prompt_parts.append(f"\n### Contexto adicional:\n{context}\n")
        
        prompt_parts.append(f"\n### Usuario: {user_message}\n\n### Minerva:")
        
        return "\n".join(prompt_parts)
    
    def _build_prompt(
        self,
        user_message: str,
        context: Optional[str] = None
    ) -> str:
        """
        Construye el prompt sin historial (fallback).
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (opcional)
            
        Returns:
            Prompt formateado
        """
        # System prompt directo
        system_prompt = (
            "Eres Minerva, un asistente personal amigable y servicial. "
            "Respondes de manera clara, concisa y natural."
        )
        
        prompt_parts = [
            system_prompt,
        ]
        
        if context:
            prompt_parts.append(f"\n### Contexto adicional:\n{context}\n")
        
        prompt_parts.append(f"\n### Usuario: {user_message}\n\n### Minerva:")
        
        return "\n".join(prompt_parts)
    
    def chat(
        self,
        user_message: str,
        context: Optional[str] = None,
        conversation_id: Optional[int] = None
    ) -> str:
        """
        Procesa un mensaje del usuario y genera respuesta.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (opcional)
            conversation_id: ID de conversación en DB (opcional)
            
        Returns:
            Respuesta generada por el agente
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"Procesando mensaje: {user_message[:100]}...")
            
            # Recuperar historial si hay conversation_id
            history = []
            if self.db_manager and conversation_id:
                try:
                    # Obtener mensajes anteriores (últimos 20 para tener contexto)
                    history = self.db_manager.get_conversation_messages(
                        conversation_id=conversation_id,
                        limit=20
                    )
                    self.logger.info(f"Historial recuperado: {len(history)} mensajes")
                except Exception as e:
                    self.logger.warning(f"No se pudo recuperar historial: {e}")
            
            # Guardar mensaje del usuario en DB
            if self.db_manager and conversation_id:
                self.db_manager.add_message(
                    conversation_id=conversation_id,
                    role='user',
                    content=user_message
                )
            
            # Construir prompt con o sin historial
            if history:
                prompt = self._build_prompt_with_history(user_message, history, context)
            else:
                prompt = self._build_prompt(user_message, context)
            
            # Llamar a Ollama API
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
            
            # Extraer respuesta
            answer = result.get('response', '').strip()
            
            if not answer:
                raise AgentExecutionError("El modelo no generó respuesta")
            
            # Guardar respuesta en DB
            if self.db_manager and conversation_id:
                self.db_manager.add_message(
                    conversation_id=conversation_id,
                    role='assistant',
                    content=answer
                )
            
            # Logging usando método de BaseAgent
            duration = time.time() - start_time
            self.log_interaction(
                input_text=user_message,
                output_text=answer,
                metadata={
                    'model': self.model_name,
                    'temperature': self.temperature,
                    'duration_seconds': duration,
                    'had_history': len(history) > 0
                }
            )
            self.logger.info(f"Respuesta generada ({len(answer)} chars)")
            
            return answer
            
        except requests.RequestException as e:
            error_msg = f"Error conectando con Ollama: {e}"
            self.logger.error(error_msg)
            raise AgentExecutionError(error_msg)
        
        except Exception as e:
            error_msg = f"Error procesando mensaje: {e}"
            self.logger.error(error_msg)
            raise AgentExecutionError(error_msg)