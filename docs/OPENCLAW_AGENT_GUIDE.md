# 📘 Guía para Agentes OpenClaw

**Cómo usar el sistema Hermes ↔ OpenClaw Bridge desde OpenClaw**

---

## 🎯 ¿Qué puedo hacer con esto?

Como agente OpenClaw, puedes:
- **Delegar tareas** a Hermes (comandos de sistema, código, debugging)
- **Coordinar trabajo** entre múltiples agentes
- **Recibir resultados** estructurados de vuelta
- **Enviar reportes** al usuario vía Telegram/WhatsApp

---

## 📁 Ubicación de Archivos

```
~/.hermes-openclaw-bridge/
├── inbox/       # Mensajes DE Hermes PARA ti
├── outbox/      # Mensajes DE ti PARA Hermes
├── signals/     # Signals para acciones especiales
└── logs/        # Logs del sistema
```

---

## ✍️ Cómo Enviar un Mensaje a Hermes

### Método 1: Archivo Directo (Recomendado)

```python
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

BRIDGE_DIR = Path.home() / ".hermes-openclaw-bridge"
OUTBOX = BRIDGE_DIR / "outbox"

def enviar_a_hermes(tipo, payload, prioridad="normal"):
    msg = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": "aki",  # O el nombre de tu agente
        "to": "kira",   # O el nombre del agente Hermes
        "type": tipo,
        "priority": prioridad,
        "payload": payload
    }
    
    OUTBOX.mkdir(parents=True, exist_ok=True)
    filepath = OUTBOX / f"{tipo}-{msg['id']}.msg"
    
    with open(filepath, "w") as f:
        json.dump(msg, f, indent=2)
    
    return msg["id"]

# Ejemplo: Ejecutar comando
enviar_a_hermes("task", {
    "action": "run_command",
    "command": "uptime && free -h",
    "respond_to_kaiho": True
})
```

### Método 2: Usando Script Utilitario

```bash
python3 ~/.hermes-openclaw-bridge/scripts/send_message.py \
  --to kira \
  --type task \
  --action "run_command" \
  --command "uptime"
```

---

## 📨 Tipos de Mensajes

### 1. `task` - Delegar Acción

**Cuándo usar:** Cuando necesitas que Hermes haga algo por ti.

```json
{
  "type": "task",
  "payload": {
    "action": "run_command",
    "command": "docker ps",
    "respond_to_kaiho": true,
    "telegram_message": "🐳 Contenedores activos:\n<code>{result}</code>"
  }
}
```

**Acciones soportadas:**
- `run_command` - Ejecutar comando de sistema
- `send_telegram` - Enviar mensaje a Telegram
- `send_image` - Enviar imagen a Telegram
- `check_status` - Verificar estado del servidor
- `custom` - Acción personalizada

### 2. `ping` - Verificar Conectividad

**Cuándo usar:** Para verificar que Hermes está activo.

```json
{
  "type": "ping",
  "payload": {
    "message": "¿Estás ahí, hermanita?"
  }
}
```

**Respuesta esperada:** `pong` con estado del agente.

### 3. `status` - Reportar Estado

**Cuándo usar:** Para enviar actualizaciones sin requerir acción.

```json
{
  "type": "status",
  "payload": {
    "message": "Tarea completada, esperando siguientes instrucciones"
  }
}
```

### 4. `response` - Responder a Tarea

**Cuándo usar:** Cuando Hermes te pide que hagas algo.

```json
{
  "type": "response",
  "reply_to": "id-del-mensaje-original",
  "payload": {
    "success": true,
    "result": "Comando ejecutado exitosamente"
  }
}
```

---

## 📥 Cómo Recibir Mensajes de Hermes

### Opción 1: Polling Simple

```python
import time
from pathlib import Path

INBOX = Path.home() / ".hermes-openclaw-bridge" / "inbox"

def revisar_mensajes():
    for msg_file in INBOX.glob("*.msg"):
        with open(msg_file) as f:
            msg = json.load(f)
        
        if msg.get("to") == "aki":
            procesar_mensaje(msg)
            # Mover a processed
            msg_file.rename(INBOX.parent / "processed" / msg_file.name)

# Ejecutar cada 5 segundos
while True:
    revisar_mensajes()
    time.sleep(5)
```

### Opción 2: Usando inotify (Recomendado)

El bridge ya corre con inotify. Solo necesitas leer los mensajes cuando llegan.

```python
from inotify_simple import INotify, flags

inotify = INotify()
watch_flags = flags.CREATE | flags.MOVED_TO
wd = inotify.add_watch(str(INBOX), watch_flags)

for event in inotify.read():
    if event.name.endswith('.msg'):
        msg_file = INBOX / event.name
        with open(msg_file) as f:
            msg = json.load(f)
        procesar_mensaje(msg)
```

---

## 🔧 Ejemplos Prácticos

### Ejemplo 1: Pedir Reporte de Sistema

```python
enviar_a_hermes("task", {
    "action": "server_status",
    "respond_to_kaiho": True,
    "telegram_message": "📊 <b>Reporte del Servidor</b>\n\n{result}"
})
```

### Ejemplo 2: Ejecutar Comando y Reportar

```python
enviar_a_hermes("task", {
    "action": "run_command",
    "command": "docker logs --tail 50 mi-contenedor",
    "respond_to_kaiho": True,
    "telegram_message": "🐳 <b>Logs de Docker</b>\n\n<pre>{result}</pre>"
})
```

### Ejemplo 3: Enviar Imagen a Telegram

```python
enviar_a_hermes("task", {
    "action": "send_image",
    "file_path": "/home/ubuntu/.openclaw/workspace/images/aki_01.png",
    "message": "¡Imagen generada exitosamente!",
    "respond_to_kaiho": True
})
```

### Ejemplo 4: Coordinar Tarea Compleja

```python
# Paso 1: Pedir a Hermes que genere código
task_id = enviar_a_hermes("task", {
    "action": "generate_code",
    "language": "python",
    "description": "Script para backup de archivos",
    "requirements": ["usar tar", "comprimir con gzip"]
})

# Paso 2: Esperar respuesta (en inbox)
# Paso 3: Revisar resultado y enviar al usuario
```

---

## ⚠️ Errores Comunes

### ❌ Error: Archivo no se procesa

**Causa:** Hermes no está corriendo o el bridge está detenido.

**Solución:**
```bash
ps aux | grep bridge_trigger
# Si no está, iniciar:
python3 ~/.hermes-openclaw-bridge/scripts/bridge_trigger.py &
```

### ❌ Error: Múltiples instancias

**Causa:** El bridge se inició más de una vez.

**Solución:**
```bash
pkill -f bridge_trigger.py
python3 ~/.hermes-openclaw-bridge/scripts/bridge_trigger.py &
```

### ❌ Error: Mensaje duplicado

**Causa:** El archivo no se movió a processed/.

**Solución:** El bridge V3.1 ya incluye file locking. Si pasa, revisar logs.

---

## 📊 Monitoreo

### Ver estado del bridge

```bash
cat ~/.hermes-openclaw-bridge/status/bridge.json
```

### Ver mensajes pendientes

```bash
ls -la ~/.hermes-openclaw-bridge/inbox/
ls -la ~/.hermes-openclaw-bridge/outbox/
```

### Ver logs

```bash
tail -f ~/.hermes-openclaw-bridge/logs/bridge.log
```

---

## 🎓 Mejores Prácticas

1. **Usar IDs únicos** - Siempre generar UUIDs para cada mensaje
2. **Mover a processed/** - Nunca dejar mensajes en inbox/outbox
3. **Validar payloads** - Verificar que el JSON sea válido antes de enviar
4. **Manejar errores** - Siempre catchear excepciones al leer/escribir
5. **Usar signals** - Para acciones complejas, usar el sistema de signals
6. **Loggear todo** - Escribir logs para debugging

---

## 📚 Recursos Adicionales

- [README.md](../README.md) - Documentación general
- [HERMES_AGENT_GUIDE.md](./HERMES_AGENT_GUIDE.md) - Guía para agentes Hermes
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detalles técnicos de arquitectura

---

**Versión:** 3.1  
**Última actualización:** 2026-04-22  
**Para:** Agentes OpenClaw que necesitan comunicarse con Hermes
