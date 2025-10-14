"""
Clase base para todos los agentes de Minerva.
Proporciona funcionalidades comunes de logging y gestión de estado.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path


class BaseAgent:
    """
    Clase base para todos los agentes de Minerva.
    
    Proporciona:
    - Sistema de logging estructurado
    - Gestión de metadata del agente
    - Métodos comunes de utilidad
    """
    
    def __init__(
        self,
        name: str,
        agent_type: str,
        log_dir: Optional[Path] = None
    ):
        """
        Inicializa el agente base.
        
        Args:
            name: Nombre del agente
            agent_type: Tipo de agente ('conversational', 'knowledge', etc.)
            log_dir: Directorio para logs (opcional)
        """
        self.name = name
        self.agent_type = agent_type
        self.created_at = datetime.now()
        
        # Configurar logging
        self.logger = self._setup_logger(log_dir)
        
        # Metadata del agente
        self.metadata: Dict[str, Any] = {
            'name': name,
            'type': agent_type,
            'created_at': self.created_at.isoformat(),
            'interactions_count': 0
        }
        
        self.logger.info(f"Agente {name} ({agent_type}) inicializado")
    
    def _setup_logger(self, log_dir: Optional[Path] = None) -> logging.Logger:
        """
        Configura el sistema de logging para el agente.
        
        Args:
            log_dir: Directorio para archivos de log
            
        Returns:
            Logger configurado
        """
        # Crear logger específico para este agente
        logger = logging.getLogger(f"minerva.agents.{self.name}")
        logger.setLevel(logging.INFO)
        
        # Evitar duplicar handlers si ya existe
        if logger.handlers:
            return logger
        
        # Handler para consola
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Formato detallado
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # Handler para archivo (si se especifica directorio)
        if log_dir:
            log_dir = Path(log_dir)
            log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = log_dir / f"{self.name}_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        
        return logger
    
    def log_interaction(
        self,
        input_text: str,
        output_text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Registra una interacción del agente.
        
        Args:
            input_text: Texto de entrada del usuario
            output_text: Respuesta generada por el agente
            metadata: Metadata adicional (opcional)
        """
        self.metadata['interactions_count'] += 1
        
        interaction_log = {
            'timestamp': datetime.now().isoformat(),
            'interaction_number': self.metadata['interactions_count'],
            'input_length': len(input_text),
            'output_length': len(output_text),
            'metadata': metadata or {}
        }
        
        self.logger.info(
            f"Interacción #{interaction_log['interaction_number']}: "
            f"Input: {input_text[:50]}... | "
            f"Output: {output_text[:50]}..."
        )
        
        # Aquí en el futuro podemos guardar en SQLite
        # Por ahora solo log a consola/archivo
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Retorna estadísticas del agente.
        
        Returns:
            Dict con estadísticas
        """
        return {
            'name': self.name,
            'type': self.agent_type,
            'created_at': self.created_at.isoformat(),
            'interactions_count': self.metadata['interactions_count'],
            'uptime_seconds': (datetime.now() - self.created_at).total_seconds()
        }
    
    def reset_stats(self) -> None:
        """Reinicia las estadísticas del agente."""
        self.metadata['interactions_count'] = 0
        self.logger.info("Estadísticas reiniciadas")


class AgentError(Exception):
    """Excepción base para errores de agentes."""
    pass


class AgentConfigError(AgentError):
    """Error de configuración del agente."""
    pass


class AgentExecutionError(AgentError):
    """Error durante la ejecución del agente."""
    pass