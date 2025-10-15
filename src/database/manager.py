"""
Manager para operaciones de base de datos SQLite.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine, desc, and_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from .schema import Base, Conversation, Message, Document, AgentLog, SystemStats


class DatabaseManager:
    """
    Gestor de la base de datos SQLite de Minerva.
    
    Proporciona métodos para:
    - Crear y gestionar conversaciones
    - Guardar y recuperar mensajes
    - Registrar documentos procesados
    - Logs de agentes
    - Estadísticas del sistema
    """
    
    def __init__(self, db_path: Path):
        """
        Inicializa el gestor de base de datos.
        
        Args:
            db_path: Ruta al archivo SQLite
        """
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear engine
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            echo=False,  # True para ver SQL queries (debug)
            connect_args={'check_same_thread': False}
        )
        
        # Crear sesión
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Crear todas las tablas
        self._initialize_database()
    
    def _initialize_database(self):
        """Crea todas las tablas si no existen."""
        Base.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Retorna una nueva sesión de base de datos."""
        return self.SessionLocal()
    
    # ========================================================================
    # CONVERSACIONES
    # ========================================================================
    
    def create_conversation(
        self,
        title: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Conversation:
        """
        Crea una nueva conversación.
        
        Args:
            title: Título opcional
            metadata: Metadata adicional
            
        Returns:
            Conversación creada
        """
        session = self.get_session()
        try:
            conversation = Conversation(
                title=title or f"Conversación {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                extra_metadata=metadata
            )
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            return conversation
        finally:
            session.close()
    
    def get_conversation(self, conversation_id: int) -> Optional[Conversation]:
        """Obtiene una conversación por ID."""
        session = self.get_session()
        try:
            return session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
        finally:
            session.close()
    
    def get_active_conversations(self, limit: int = 10) -> List[Conversation]:
        """Obtiene las conversaciones activas más recientes."""
        session = self.get_session()
        try:
            return session.query(Conversation).filter(
                Conversation.is_active == True
            ).order_by(desc(Conversation.updated_at)).limit(limit).all()
        finally:
            session.close()
    
    def archive_conversation(self, conversation_id: int):
        """Archiva una conversación."""
        session = self.get_session()
        try:
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation:
                conversation.is_active = False
                session.commit()
        finally:
            session.close()
    
    # ========================================================================
    # MENSAJES
    # ========================================================================
    
    def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        agent_type: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        tokens: Optional[int] = None,
        had_context: bool = False,
        context_source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Message:
        """
        Agrega un mensaje a una conversación.
        
        Args:
            conversation_id: ID de la conversación
            role: 'user' o 'assistant'
            content: Contenido del mensaje
            agent_type: Tipo de agente (opcional)
            model: Modelo usado (opcional)
            temperature: Temperatura (opcional)
            tokens: Número de tokens (opcional)
            had_context: Si usó contexto
            context_source: Fuente del contexto
            metadata: Metadata adicional
            
        Returns:
            Mensaje creado
        """
        session = self.get_session()
        try:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                agent_type=agent_type,
                model=model,
                temperature=temperature,
                tokens=tokens,
                had_context=had_context,
                context_source=context_source,
                extra_metadata=metadata
            )
            session.add(message)
            
            # Actualizar timestamp de conversación
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation:
                conversation.updated_at = datetime.now()
            
            session.commit()
            session.refresh(message)
            return message
        finally:
            session.close()
    
    def get_conversation_messages(
        self,
        conversation_id: int,
        limit: Optional[int] = None
    ) -> List[Message]:
        """
        Obtiene los mensajes de una conversación.
        
        Args:
            conversation_id: ID de la conversación
            limit: Límite de mensajes (más recientes)
            
        Returns:
            Lista de mensajes
        """
        session = self.get_session()
        try:
            query = session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.timestamp)
            
            if limit:
                # Obtener los últimos N mensajes
                query = query.order_by(desc(Message.timestamp)).limit(limit)
                messages = query.all()
                messages.reverse()  # Volver a orden cronológico
                return messages
            
            return query.all()
        finally:
            session.close()
    
    def search_messages(
        self,
        query: str,
        conversation_id: Optional[int] = None,
        limit: int = 10
    ) -> List[Message]:
        """
        Busca mensajes por contenido.
        
        Args:
            query: Texto a buscar
            conversation_id: Filtrar por conversación (opcional)
            limit: Número máximo de resultados
            
        Returns:
            Lista de mensajes que coinciden
        """
        session = self.get_session()
        try:
            q = session.query(Message).filter(
                Message.content.contains(query)
            )
            
            if conversation_id:
                q = q.filter(Message.conversation_id == conversation_id)
            
            return q.order_by(desc(Message.timestamp)).limit(limit).all()
        finally:
            session.close()
    
    # ========================================================================
    # DOCUMENTOS
    # ========================================================================
    
    def add_document(
        self,
        filename: str,
        file_type: str,
        file_size: Optional[int] = None,
        original_path: Optional[str] = None,
        chunk_count: Optional[int] = None,
        qdrant_collection: Optional[str] = None,
        qdrant_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Document:
        """Registra un documento procesado."""
        session = self.get_session()
        try:
            document = Document(
                filename=filename,
                original_path=original_path,
                file_type=file_type,
                file_size=file_size,
                chunk_count=chunk_count,
                qdrant_collection=qdrant_collection,
                qdrant_ids=qdrant_ids,
                extra_metadata=metadata
            )
            session.add(document)
            session.commit()
            session.refresh(document)
            return document
        finally:
            session.close()
    
    def get_documents(self, limit: int = 50) -> List[Document]:
        """Obtiene documentos procesados."""
        session = self.get_session()
        try:
            return session.query(Document).filter(
                Document.is_indexed == True
            ).order_by(desc(Document.processed_at)).limit(limit).all()
        finally:
            session.close()
    
    def get_document(self, document_id: int) -> Optional[Document]:
        """Obtiene un documento por ID."""
        session = self.get_session()
        try:
            return session.query(Document).filter(
                Document.id == document_id
            ).first()
        finally:
            session.close()
    
    # ========================================================================
    # LOGS DE AGENTES
    # ========================================================================
    
    def add_agent_log(
        self,
        agent_name: str,
        agent_type: str,
        action: str,
        status: str,
        duration_ms: Optional[int] = None,
        input_summary: Optional[str] = None,
        output_summary: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentLog:
        """Registra un log de agente."""
        session = self.get_session()
        try:
            log = AgentLog(
                agent_name=agent_name,
                agent_type=agent_type,
                action=action,
                status=status,
                duration_ms=duration_ms,
                input_summary=input_summary,
                output_summary=output_summary,
                error_message=error_message,
                extra_metadata=metadata
            )
            session.add(log)
            session.commit()
            session.refresh(log)
            return log
        finally:
            session.close()
    
    def get_agent_logs(
        self,
        agent_name: Optional[str] = None,
        limit: int = 100
    ) -> List[AgentLog]:
        """Obtiene logs de agentes."""
        session = self.get_session()
        try:
            query = session.query(AgentLog)
            
            if agent_name:
                query = query.filter(AgentLog.agent_name == agent_name)
            
            return query.order_by(desc(AgentLog.timestamp)).limit(limit).all()
        finally:
            session.close()
    
    # ========================================================================
    # ESTADÍSTICAS
    # ========================================================================
    
    def update_stats(self) -> SystemStats:
        """Calcula y guarda estadísticas del sistema."""
        session = self.get_session()
        try:
            stats = SystemStats(
                total_conversations=session.query(Conversation).count(),
                total_messages=session.query(Message).count(),
                total_documents=session.query(Document).count()
            )
            session.add(stats)
            session.commit()
            session.refresh(stats)
            return stats
        finally:
            session.close()
    
    def get_latest_stats(self) -> Optional[SystemStats]:
        """Obtiene las estadísticas más recientes."""
        session = self.get_session()
        try:
            return session.query(SystemStats).order_by(
                desc(SystemStats.timestamp)
            ).first()
        finally:
            session.close()
    
    # ========================================================================
    # UTILIDADES
    # ========================================================================
    
    def close(self):
        """Cierra la conexión a la base de datos."""
        self.engine.dispose()