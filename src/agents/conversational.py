"""
Agente conversacional de Minerva.
Maneja conversaciones generales y responde preguntas usando Ollama.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import requests
import json

from .base_agent import BaseAgent, AgentExecutionError
from config.prompts import get_agent_config
from config.settings import settings


class ConversationalAgent(BaseAgent):
    """
    Agente para conversación general.
    
    Características:
    - Conversación amigable y natural
    - Conexión directa con Ollama (sin CrewAI overhead)
    - Rápido y eficiente
    """
    
    def __init__(
        self,
        model_name: str = "phi3",
        temperature: float = 0.7,
        log_dir: Optional[Path] = None
    ):
        """
        Inicializa el agente conversacional.
        
        Args:
            model_name: Nombre del modelo de Ollama
            temperature: Temperatura para generación (0.0-1.0)
            log_dir: Directorio para logs
        """
        super().__init__(
            name="conversational_agent",
            agent_type="conversational",
            log_dir=log_dir
        )
        
        self.model_name = model_name
        self.temperature = temperature
        self.base_url = settings.OLLAMA_BASE_URL
        
        # Obtener configuración de prompts
        self.config = get_agent_config('conversational')
        
        # Verificar conexión con Ollama
        try:
            self._verify_connection()
            self.logger.info(f"LLM configurado: {model_name}")
        except Exception as e:
            self.logger.error(f"Error configurando LLM: {e}")
            raise AgentExecutionError(f"No se pudo conectar a Ollama: {e}")
    
    def _verify_connection(self) -> None:
        """Verifica que Ollama esté accesible."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise AgentExecutionError(f"Ollama no está accesible: {e}")
    
    def _build_prompt(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Construye el prompt completo con el rol del agente.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (opcional)
            
        Returns:
            Prompt completo
        """
        system_prompt = f"{self.config['role']}\n\n{self.config['backstory']}"
        
        if context:
            full_prompt = f"{system_prompt}\n\nContexto:\n{context}\n\nUsuario: {user_message}\n\nMinerva:"
        else:
            full_prompt = f"{system_prompt}\n\nUsuario: {user_message}\n\nMinerva:"
        
        return full_prompt
    
    def chat(self, user_message: str, context: Optional[str] = None) -> str:
        """
        Procesa un mensaje del usuario y genera respuesta.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (opcional)
            
        Returns:
            Respuesta generada por el agente
        """
        try:
            self.logger.info(f"Procesando mensaje: {user_message[:100]}...")
            
            # Construir prompt
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
                raise AgentExecutionError("Ollama no devolvió respuesta")
            
            # Registrar interacción
            self.log_interaction(
                input_text=user_message,
                output_text=answer,
                metadata={
                    'model': self.model_name,
                    'temperature': self.temperature,
                    'had_context': context is not None,
                    'tokens': result.get('eval_count', 0)
                }
            )
            
            self.logger.info(f"Respuesta generada ({len(answer)} chars)")
            return answer
            
        except requests.exceptions.Timeout:
            self.logger.error("Timeout esperando respuesta de Ollama")
            raise AgentExecutionError("Timeout: Ollama tardó demasiado en responder")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error de conexión con Ollama: {e}")
            raise AgentExecutionError(f"Error de conexión: {e}")
        except Exception as e:
            self.logger.error(f"Error en chat: {e}", exc_info=True)
            raise AgentExecutionError(f"Error procesando mensaje: {e}")
    
    def stream_chat(self, user_message: str, context: Optional[str] = None):
        """
        Procesa un mensaje con streaming.
        
        Args:
            user_message: Mensaje del usuario
            context: Contexto adicional (opcional)
            
        Yields:
            Fragmentos de la respuesta
        """
        try:
            self.logger.info(f"Procesando mensaje (streaming): {user_message[:100]}...")
            
            # Construir prompt
            prompt = self._build_prompt(user_message, context)
            
            # Llamar a Ollama API con streaming
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "temperature": self.temperature,
                    "stream": True
                },
                stream=True,
                timeout=60
            )
            
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    if 'response' in chunk:
                        text = chunk['response']
                        full_response += text
                        yield text
            
            # Registrar interacción completa
            self.log_interaction(
                input_text=user_message,
                output_text=full_response,
                metadata={
                    'model': self.model_name,
                    'temperature': self.temperature,
                    'had_context': context is not None,
                    'streaming': True
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error en streaming: {e}", exc_info=True)
            raise AgentExecutionError(f"Error en streaming: {e}")
    
    def update_temperature(self, temperature: float) -> None:
        """
        Actualiza la temperatura del modelo.
        
        Args:
            temperature: Nueva temperatura (0.0-1.0)
        """
        if not 0.0 <= temperature <= 1.0:
            raise ValueError("Temperature debe estar entre 0.0 y 1.0")
        
        self.temperature = temperature
        self.logger.info(f"Temperatura actualizada a {temperature}")


def create_conversational_agent(**kwargs) -> ConversationalAgent:
    """
    Factory function para crear agente conversacional.
    
    Args:
        **kwargs: Argumentos para ConversationalAgent
        
    Returns:
        Instancia de ConversationalAgent
    """
    return ConversationalAgent(**kwargs)