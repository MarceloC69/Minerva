# src/database/schema.py - v2.0.0 - Con soporte de memoria
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
    """Tabla de conversaciones/sesiones de chat."""
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True)
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}', created_at={self.created_at})>"


class Message(Base):
    """Tabla de mensajes individuales dentro de conversaciones."""
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    
    # Metadata técnica
    agent_type = Column(String(50), nullable=True)
    model = Column(String(100), nullable=True)
    temperature = Column(Float, nullable=True)
    tokens = Column(Integer, nullable=True)
    
    # Contexto usado
    had_context = Column(Boolean, default=False)
    context_source = Column(String(50), nullable=True)
    
    # Metadata adicional
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', conversation_id={self.conversation_id})>"


class Document(Base):
    """Tabla de documentos procesados y almacenados en Qdrant."""
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    original_path = Column(String(500), nullable=True)
    file_type = Column(String(20), nullable=False)
    file_size = Column(Integer, nullable=True)
    
    # Procesamiento
    processed_at = Column(DateTime, default=func.now(), nullable=False)
    chunk_count = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    
    # Qdrant
    qdrant_collection = Column(String(100), nullable=True)
    qdrant_ids = Column(JSON, nullable=True)
    
    # Metadata del documento
    title = Column(String(300), nullable=True)
    author = Column(String(200), nullable=True)
    summary = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    
    # Estado
    is_indexed = Column(Boolean, default=True)
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"


class AgentLog(Base):
    """Tabla de logs estructurados de agentes."""
    __tablename__ = 'agent_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_name = Column(String(100), nullable=False)
    agent_type = Column(String(50), nullable=False)
    
    # Acción
    action = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)
    
    # Tiempo
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    duration_ms = Column(Integer, nullable=True)
    
    # Detalles
    input_summary = Column(Text, nullable=True)
    output_summary = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<AgentLog(id={self.id}, agent='{self.agent_name}', action='{self.action}', status='{self.status}')>"


class SystemStats(Base):
    """Tabla de estadísticas del sistema."""
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


class PromptVersion(Base):
    """Tabla de versiones de prompts para agentes."""
    __tablename__ = 'prompt_versions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    agent_type = Column(String(50), nullable=False)
    prompt_name = Column(String(100), nullable=False)
    version = Column(Integer, nullable=False)
    
    # Contenido
    content = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String(100), default='system', nullable=False)
    is_active = Column(Boolean, default=False)
    
    # Variables del prompt
    variables = Column(JSON, nullable=True)
    
    # Métricas
    usage_count = Column(Integer, default=0)
    avg_response_quality = Column(Float, nullable=True)
    
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<PromptVersion(id={self.id}, agent='{self.agent_type}', name='{self.prompt_name}', v{self.version}, active={self.is_active})>"


# NUEVO: Tabla para tracking de memoria persistente
class MemoryFact(Base):
    """
    Tabla para tracking de hechos en memoria persistente (Mem0).
    Metadata para debugging y visualización.
    """
    __tablename__ = 'memory_facts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Identificación
    mem0_id = Column(String(100), nullable=True)  # ID en Mem0
    user_id = Column(String(100), default='default_user', nullable=False)
    
    # Contenido
    fact = Column(Text, nullable=False)  # El hecho memorizado
    source_conversation_id = Column(Integer, ForeignKey('conversations.id'), nullable=True)
    source_message = Column(Text, nullable=True)  # Mensaje original que generó el hecho
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    last_accessed = Column(DateTime, nullable=True)
    last_updated = Column(DateTime, nullable=True)
    
    # Clasificación
    category = Column(String(50), nullable=True)  # 'preference', 'personal_info', 'knowledge', etc.
    importance = Column(Integer, default=5)  # 1-10
    
    # Estado
    is_active = Column(Boolean, default=True)
    access_count = Column(Integer, default=0)  # Cuántas veces se usó
    
    # Metadata
    extra_metadata = Column(JSON, nullable=True)
    
    def __repr__(self):
        return f"<MemoryFact(id={self.id}, user='{self.user_id}', fact='{self.fact[:50]}...')>"