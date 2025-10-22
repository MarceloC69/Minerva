# 📝 Guía de Administración de Prompts - Minerva

## 🎯 Introducción

La interfaz de administración de prompts te permite gestionar todos los prompts que usan los agentes de Minerva de manera visual y sin tocar código.

**Beneficios:**
- ✅ Versionado automático de todos los cambios
- ✅ Rollback a versiones anteriores en cualquier momento
- ✅ Ver estadísticas de uso
- ✅ Activar/desactivar prompts fácilmente
- ✅ Historial completo de modificaciones

---

## 🚀 Inicio Rápido

### 1. Primera vez - Inicializar prompts

Si es la primera vez que usas Minerva, ejecuta:

```bash
python init_prompts.py
```

Esto creará los prompts por defecto para todos los agentes.

### 2. Abrir la interfaz de administración

```bash
python main.py
```

Luego abre tu navegador en `http://localhost:7860` y ve a la pestaña **⚙️ Administración**.

---

## 📑 Estructura de Pestañas

### 📋 Prompts Activos

**¿Para qué sirve?**
- Ver todos los prompts que están actualmente activos
- Filtrar por tipo de agente
- Vista rápida del contenido

**Cómo usar:**
1. Selecciona un filtro (Todos, Conversational, Knowledge, etc.)
2. Presiona "🔄 Recargar" para actualizar
3. Verás una tabla con todos los prompts activos

---

### ✏️ Editar / Crear Prompt

**¿Para qué sirve?**
- Crear nuevas versiones de prompts existentes
- Crear prompts completamente nuevos
- Editar el contenido de prompts

**Cómo usar:**

#### Para editar un prompt existente:

1. **Seleccionar:**
   - Tipo de Agente: `conversational`, `knowledge`, `router`, etc.
   - Nombre del Prompt: `system_prompt`, `rag_prompt`, etc.

2. **Cargar:**
   - Presiona "📂 Cargar Prompt"
   - Verás el contenido actual y la información de versión

3. **Editar:**
   - Modifica el contenido en el editor de texto
   - Agrega una descripción de los cambios (recomendado)
   - Verifica "Creado por" (tu nombre o "admin")
   - Decide si quieres activar automáticamente la nueva versión

4. **Guardar:**
   - Presiona "💾 Guardar Nueva Versión"
   - Se creará una nueva versión incremental (v1, v2, v3...)

#### Para crear un prompt nuevo:

1. Selecciona el agente y nombre de prompt
2. Si no existe, escribe el contenido desde cero
3. Guarda como una nueva versión v1

---

### 📜 Historial de Versiones

**¿Para qué sirve?**
- Ver todas las versiones de un prompt
- Comparar cambios entre versiones
- Activar versiones anteriores (rollback)
- Ver estadísticas de uso

**Cómo usar:**

1. **Ver historial:**
   - Selecciona Tipo de Agente y Nombre del Prompt
   - Presiona "📜 Ver Historial"
   - Verás todas las versiones ordenadas por fecha

2. **Activar una versión anterior:**
   - Identifica el número de versión que quieres activar
   - Ingresa el número en "Número de versión"
   - Presiona "✅ Activar Versión"
   - ¡Listo! Esa versión ahora está activa

**Información que verás:**
- ✅ Versión activa (destacada en verde)
- ⚪ Versiones inactivas
- 📅 Fecha y hora de creación
- 👤 Quién la creó
- 📝 Descripción de cambios
- 🔢 Número de veces que se usó

---

## 🎓 Mejores Prácticas

### 1. Descripciones Claras
```
✅ BUENO: "Agregado tono más empático y ejemplos de código"
❌ MALO: "Actualización"
```

### 2. Versionado Incremental
- No borres versiones antiguas
- Cada cambio crea una nueva versión
- Puedes volver atrás siempre que quieras

### 3. Testing de Prompts
- Después de crear una versión, pruébala en el chat
- Si no funciona bien, activa la versión anterior
- Refina y crea una nueva versión mejorada

### 4. Nombres Consistentes
Usa nombres estándar:
- `system_prompt` - Prompt principal del agente
- `rag_prompt` - Template para queries con contexto
- `routing_prompt` - Lógica de decisión del router
- `context_prompt` - Formato del contexto

---

## 📚 Tipos de Prompts

### Conversational Agent
**system_prompt**: Define la personalidad y comportamiento del agente conversacional

**Variables disponibles:**
- `{user_message}` - Mensaje del usuario
- `{history}` - Historial de conversación (opcional)

### Knowledge Agent
**system_prompt**: Instrucciones para responder basándose en documentos

**rag_prompt**: Template para queries con contexto de documentos

**Variables disponibles:**
- `{context}` - Contexto de documentos relevantes
- `{question}` - Pregunta del usuario
- `{sources}` - Fuentes de información

### Router
**routing_prompt**: Lógica para decidir qué agente usar

**Variables disponibles:**
- `{question}` - Pregunta del usuario
- `{has_documents}` - Si hay documentos disponibles (true/false)

---

## 🐛 Troubleshooting

### "No hay prompts activos"
**Solución:** Ejecuta `python init_prompts.py` para crear los prompts por defecto.

### "Error al guardar"
**Posibles causas:**
- No seleccionaste agente o nombre de prompt
- El contenido está vacío o muy corto (mínimo 10 caracteres)
- Error de conexión con la base de datos

### "No se puede activar versión"
**Posibles causas:**
- La versión no existe
- Error al acceder a la base de datos

**Solución:** Verifica el número de versión en el historial primero.

---

## 💡 Ejemplos de Uso

### Ejemplo 1: Hacer el agente más formal

1. Ir a Editar/Crear
2. Seleccionar: `conversational` + `system_prompt`
3. Cargar el prompt actual
4. Modificar el tono:
   ```
   - Sé conversacional y natural
   + Mantén un tono profesional y formal
   ```
5. Descripción: "Cambiado a tono más formal"
6. Guardar y activar

### Ejemplo 2: Agregar instrucciones específicas al RAG

1. Ir a Editar/Crear
2. Seleccionar: `knowledge` + `rag_prompt`
3. Cargar el prompt actual
4. Agregar al final:
   ```
   NOTA ADICIONAL:
   - Siempre indica el nivel de confianza de tu respuesta
   - Si hay múltiples interpretaciones, menciónalas todas
   ```
5. Descripción: "Agregadas instrucciones de confianza"
6. Guardar y activar

### Ejemplo 3: Rollback a versión anterior

1. Ir a Historial
2. Seleccionar agente y prompt
3. Ver Historial
4. Identificar la versión que funcionaba bien (ej: v3)
5. Ingresar "3" en número de versión
6. Activar Versión

---

## 🔐 Seguridad y Backup

### Backup de la base de datos

La base de datos SQLite contiene todos los prompts:

```bash
# Hacer backup
cp data/sqlite/minerva.db data/sqlite/minerva_backup.db

# Restaurar backup
cp data/sqlite/minerva_backup.db data/sqlite/minerva.db
```

### Exportar prompts (futuro)

En futuras versiones podrás exportar prompts a JSON/YAML para compartir o versionar con Git.

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs en la terminal donde ejecutaste `python main.py`
2. Verifica que la base de datos existe en `data/sqlite/minerva.db`
3. Prueba reiniciar la aplicación

---

## 🎉 ¡Listo!

Ya estás preparado para gestionar los prompts de Minerva como un profesional.

**Recuerda:**
- Cada cambio crea una nueva versión
- Puedes volver atrás siempre
- Describe tus cambios para tu yo del futuro
- Prueba en el chat después de cada cambio

¡Feliz administración de prompts! 🚀