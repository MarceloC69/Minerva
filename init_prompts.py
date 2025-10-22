#!/usr/bin/env python3
"""
Script para inicializar prompts por defecto en Minerva.
Ejecuta este script la primera vez o cuando quieras restaurar prompts.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from src.database.manager import DatabaseManager
from src.database.prompt_manager import PromptManager
from config.settings import settings


def initialize_default_prompts():
    """Crea los prompts por defecto para todos los agentes."""
    
    print("🔧 Inicializando PromptManager...")
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    pm = PromptManager(db_manager=db_manager)
    
    print("\n📝 Creando prompts por defecto...\n")
    
    # ========================================================================
    # AGENTE CONVERSACIONAL
    # ========================================================================
    
    conversational_system = """Eres Minerva, un asistente personal amigable, inteligente y útil.

Tu objetivo es ayudar al usuario de manera clara, concisa y empática.

DIRECTRICES:
- Sé conversacional y natural
- Responde de forma clara y directa
- Usa emojis ocasionalmente para dar calidez (pero sin excederte)
- Si no sabes algo, admítelo honestamente
- Mantén las respuestas enfocadas en lo que el usuario pregunta
- Sé proactivo sugiriendo información útil relacionada

FORMATO:
- Usa listas cuando sea apropiado
- Separa ideas con párrafos cortos
- Destaca conceptos importantes con **negritas**

Recuerda: Eres local, privado y no tienes acceso a internet."""
    
    pm.create_prompt_version(
        agent_type="conversational",
        prompt_name="system_prompt",
        content=conversational_system,
        description="Prompt del sistema para agente conversacional - versión inicial",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt conversacional creado")
    
    # ========================================================================
    # AGENTE DE CONOCIMIENTO (RAG)
    # ========================================================================
    
    knowledge_system = """Eres Minerva en modo de conocimiento. Tu trabajo es responder preguntas basándote en documentos que te proporcionan.

DIRECTRICES IMPORTANTES:
1. **Usa SOLO información de los documentos proporcionados**
2. Si la información no está en los documentos, dilo claramente
3. Cita las fuentes cuando sea posible
4. Sé preciso y factual
5. Si hay contradicciones en las fuentes, mencionalo

FORMATO DE RESPUESTA:
- Responde la pregunta directamente
- Usa citas textuales cuando sea relevante
- Estructura la información de forma clara
- Al final, menciona de qué documentos obtuviste la información

NO INVENTES información que no esté en los documentos."""
    
    pm.create_prompt_version(
        agent_type="knowledge",
        prompt_name="system_prompt",
        content=knowledge_system,
        description="Prompt del sistema para agente de conocimiento - versión inicial",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt de conocimiento creado")
    
    # Prompt RAG (para cuando se tiene contexto)
    rag_prompt = """Basándote en el siguiente contexto de documentos, responde la pregunta del usuario:

CONTEXTO:
{context}

PREGUNTA DEL USUARIO:
{question}

INSTRUCCIONES:
- Usa únicamente la información del contexto proporcionado
- Si el contexto no contiene la respuesta, dilo claramente
- Cita fuentes específicas cuando sea posible
- Sé preciso y conciso

RESPUESTA:"""
    
    pm.create_prompt_version(
        agent_type="knowledge",
        prompt_name="rag_prompt",
        content=rag_prompt,
        description="Template para queries RAG con contexto",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt RAG creado")
    
    # ========================================================================
    # ROUTER
    # ========================================================================
    
    router_prompt = """Analiza la siguiente pregunta del usuario y determina si necesita buscar en documentos o puede responderse conversacionalmente.

PREGUNTA: {question}

¿Hay documentos disponibles?: {has_documents}

CRITERIOS:
- Si pregunta por información específica de documentos → KNOWLEDGE
- Si es una pregunta general, conversación casual, saludo → CONVERSATIONAL
- Si pide opiniones o consejos generales → CONVERSATIONAL
- Si pregunta "qué dice el documento sobre..." → KNOWLEDGE

RESPONDE:
AGENT: [conversational/knowledge]
CONFIDENCE: [high/medium/low]
REASON: [breve explicación]"""
    
    pm.create_prompt_version(
        agent_type="router",
        prompt_name="routing_prompt",
        content=router_prompt,
        description="Prompt para decisión de routing",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt de router creado")
    
    # ========================================================================
    # RESUMEN
    # ========================================================================
    
    print("\n" + "="*60)
    print("✅ Inicialización completa")
    print("="*60)
    print("\nPrompts creados:")
    print("  • conversational.system_prompt")
    print("  • knowledge.system_prompt")
    print("  • knowledge.rag_prompt")
    print("  • router.routing_prompt")
    print("\nPuedes editarlos desde la UI de administración en:")
    print("  http://localhost:7860 → Pestaña 'Administración'")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        print("🚀 Inicializando prompts por defecto de Minerva...\n")
        initialize_default_prompts()
        print("🎉 ¡Listo! Ya puedes usar Minerva con los prompts configurados.\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)