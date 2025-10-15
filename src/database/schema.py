"""
Esquema de la base de datos SQLite para Minerva.
"""

from sqlalchemy import (
    Column, Integer, String, Text, Float, DateTime, ForeignKey, Boolean, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Conversation(Base):
    """
    Tabla de conversaciones/sesiones de chat.
    """
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=True)  # Título opcional de la conversación
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)  # Conversación activa o archivada
    extra_metadata = Column(JSON, nullable=True)  # Metadata adicional (tags, etc.)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', created_at={self.created_at})>"


class Message(Base):
    """
    Tabla de mensajes individuales dentro de conversaciones.
    """
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' o 'assistant'
    content = Column(Text, nullable=False)  # Contenido del mensaje
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Metadata técnica
    agent_type = Column(String(50), nullable=True)  # Tipo de agente que respondió
    model = Column(String(100), nullable=True)  # Modelo usado (ej: phi3)
    temperature = Column(Float, nullable=True)  # Temperatura usada
    tokens = Column(Integer, nullable=True)  # Número de tokens generados
    
    # Contexto usado
    had_context = Column(Boolean, default=False)  # Si usó contexto de RAG/búsqueda
    context_source = Column(String(50), nullable=True)  # 'qdrant', 'web', etc.
    
    # Metadata adicional
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"


class Document(Base):
    """
    Tabla de documentos procesados y almacenados en Qdrant.
    """
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_path = Column(String(500), nullable=True)
    file_type = Column(String(20), nullable=False)  # 'pdf', 'docx', 'txt', etc.
    file_size = Column(Integer, nullable=True)  # Tamaño en bytes
    
    # Procesamiento
    processed_at = Column(DateTime, default=func.now(), nullable=False)
    chunk_count = Column(Integer, nullable=True)  # Número de chunks creados
    total_tokens = Column(Integer, nullable=True)  # Tokens aproximados
    
    # Qdrant
    qdrant_collection = Column(String(100), nullable=True)  # Colección en Qdrant
    qdrant_ids = Column(JSON, nullable=True)  # IDs de vectores en Qdrant
    
    # Metadata del documento
    title = Column(String(300), nullable=True)
    author = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Lista de tags
    
    # Estado
    is_indexed = Column(Boolean, default=True)
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"


class AgentLog(Base):
    """
    Tabla de logs estructurados de agentes.
    """
    __tablename__ = 'agent_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)  # 'conversational', 'knowledge', etc.
    
    # Acción
    action = Column(String(100), nullable=False)  # 'chat', 'search', 'process_doc', etc.
    status = Column(String(20), nullable=False)  # 'success', 'error', 'warning'
    
    # Tiempo
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    duration_ms = Column(Integer, nullable=True)  # Duración en milisegundos
    
    # Detalles
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<AgentLog(id={self.id}, agent='{self.agent_name}', action='{self.action}', status='{self.status}')>"


class SystemStats(Base):
    """
    Tabla de estadísticas del sistema.
    """
    __tablename__ = 'system_stats'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Contadores
    total_conversations = Column(Integer, default=0)
    total_messages = Column(Integer, default=0)
    total_documents = Column(Integer, default=0)
    total_vectors = Column(Integer, default=0)
    
    # Performance
    avg_response_time_ms = Column(Float, nullable=True)
    avg_tokens_per_response = Column(Float, nullable=True)
    
    # Uso
    disk_usage_mb = Column(Float, nullable=True)
    qdrant_size_mb = Column(Float, nullable=True)
    
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<SystemStats(timestamp={self.timestamp}, conversations={self.total_conversations})>"