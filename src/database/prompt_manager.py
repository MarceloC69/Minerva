# src/database/prompt_manager.py - Gestor de prompts versionados
"""
Manager para prompts versionados.
Permite crear, activar, y recuperar versiones de prompts.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from .schema import PromptVersion


class PromptManager:
    """
    Gestor de prompts versionados.
    
    Características:
    - Versionado automático
    - Solo una versión activa por prompt
    - Historial completo
    - Rollback a versiones anteriores
    """
    
    def __init__(self, db_manager):
        """
        Inicializa el gestor de prompts.
        
        Args:
            db_manager: Instancia de DatabaseManager
        """
        self.db_manager = db_manager
        self.logger = logging.getLogger("minerva.prompts")
    
    def create_prompt_version(
        self,
        agent_type: str,
        prompt_name: str,
        content: str,
        description: Optional[str] = None,
        variables: Optional[List[str]] = None,
        created_by: str = 'system',
        auto_activate: bool = True
    ) -> PromptVersion:
        """
        Crea una nueva versión de un prompt.
        
        Args:
            agent_type: Tipo de agente ('conversational', 'knowledge', etc.)
            prompt_name: Nombre del prompt ('system_prompt', 'rag_prompt', etc.)
            content: Contenido del prompt
            description: Descripción de los cambios
            variables: Lista de variables que usa el prompt
            created_by: Quién creó la versión
            auto_activate: Si activar automáticamente esta versión
            
        Returns:
            Nueva versión creada
        """
        session = self.db_manager.get_session()
        
        try:
            # Obtener última versión
            last_version = session.query(PromptVersion).filter(
                and_(
                    PromptVersion.agent_type == agent_type,
                    PromptVersion.prompt_name == prompt_name
                )
            ).order_by(desc(PromptVersion.version)).first()
            
            next_version = (last_version.version + 1) if last_version else 1
            
            # Crear nueva versión
            new_prompt = PromptVersion(
                agent_type=agent_type,
                prompt_name=prompt_name,
                version=next_version,
                content=content,
                description=description or f"Version {next_version}",
                created_by=created_by,
                is_active=False,  # Se activa después si auto_activate=True
                variables={'vars': variables} if variables else None
            )
            
            session.add(new_prompt)
            session.commit()
            session.refresh(new_prompt)
            
            # Activar si se solicita
            if auto_activate:
                self.activate_prompt_version(new_prompt.id)
            
            self.logger.info(
                f"✅ Prompt creado: {agent_type}.{prompt_name} v{next_version}"
            )
            
            return new_prompt
            
        finally:
            session.close()
    
    def activate_prompt_version(self, version_id: int) -> bool:
        """
        Activa una versión específica de un prompt.
        Desactiva todas las demás versiones del mismo prompt.
        
        Args:
            version_id: ID de la versión a activar
            
        Returns:
            True si se activó correctamente
        """
        session = self.db_manager.get_session()
        
        try:
            # Obtener la versión a activar
            target_version = session.query(PromptVersion).filter(
                PromptVersion.id == version_id
            ).first()
            
            if not target_version:
                self.logger.warning(f"Versión {version_id} no encontrada")
                return False
            
            # Desactivar todas las versiones del mismo prompt
            session.query(PromptVersion).filter(
                and_(
                    PromptVersion.agent_type == target_version.agent_type,
                    PromptVersion.prompt_name == target_version.prompt_name
                )
            ).update({'is_active': False})
            
            # Activar la versión seleccionada
            target_version.is_active = True
            session.commit()
            
            self.logger.info(
                f"✅ Prompt activado: {target_version.agent_type}.{target_version.prompt_name} v{target_version.version}"
            )
            
            return True
            
        finally:
            session.close()
    
    def get_active_prompt(
        self,
        agent_type: str,
        prompt_name: str
    ) -> Optional[str]:
        """
        Obtiene el contenido del prompt activo.
        
        Args:
            agent_type: Tipo de agente
            prompt_name: Nombre del prompt
            
        Returns:
            Contenido del prompt o None si no existe
        """
        session = self.db_manager.get_session()
        
        try:
            active_prompt = session.query(PromptVersion).filter(
                and_(
                    PromptVersion.agent_type == agent_type,
                    PromptVersion.prompt_name == prompt_name,
                    PromptVersion.is_active == True
                )
            ).first()
            
            if active_prompt:
                # Incrementar contador de uso
                active_prompt.usage_count += 1
                session.commit()
                
                return active_prompt.content
            
            self.logger.warning(
                f"No hay prompt activo para {agent_type}.{prompt_name}"
            )
            return None
            
        finally:
            session.close()
    
    def get_prompt_history(
        self,
        agent_type: str,
        prompt_name: str,
        limit: int = 10
    ) -> List[PromptVersion]:
        """
        Obtiene el historial de versiones de un prompt.
        
        Args:
            agent_type: Tipo de agente
            prompt_name: Nombre del prompt
            limit: Número máximo de versiones a retornar
            
        Returns:
            Lista de versiones (más recientes primero)
        """
        session = self.db_manager.get_session()
        
        try:
            versions = session.query(PromptVersion).filter(
                and_(
                    PromptVersion.agent_type == agent_type,
                    PromptVersion.prompt_name == prompt_name
                )
            ).order_by(desc(PromptVersion.version)).limit(limit).all()
            
            return versions
            
        finally:
            session.close()
    
    def get_all_active_prompts(
        self,
        agent_type: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Obtiene todos los prompts activos.
        
        Args:
            agent_type: Filtrar por tipo de agente (opcional)
            
        Returns:
            Diccionario {prompt_name: content}
        """
        session = self.db_manager.get_session()
        
        try:
            query = session.query(PromptVersion).filter(
                PromptVersion.is_active == True
            )
            
            if agent_type:
                query = query.filter(PromptVersion.agent_type == agent_type)
            
            prompts = query.all()
            
            return {
                f"{p.agent_type}.{p.prompt_name}": p.content
                for p in prompts
            }
            
        finally:
            session.close()
    
    def delete_prompt_version(self, version_id: int) -> bool:
        """
        Elimina una versión de prompt.
        No permite eliminar la versión activa.
        
        Args:
            version_id: ID de la versión a eliminar
            
        Returns:
            True si se eliminó correctamente
        """
        session = self.db_manager.get_session()
        
        try:
            version = session.query(PromptVersion).filter(
                PromptVersion.id == version_id
            ).first()
            
            if not version:
                return False
            
            if version.is_active:
                self.logger.warning(
                    f"No se puede eliminar versión activa: {version_id}"
                )
                return False
            
            session.delete(version)
            session.commit()
            
            self.logger.info(f"Versión {version_id} eliminada")
            return True
            
        finally:
            session.close()