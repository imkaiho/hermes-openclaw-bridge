# 🤖 Guía para Agentes Hermes

**Cómo usar el sistema Hermes ↔ OpenClaw Bridge desde Hermes**

---

## 🎯 ¿Qué puedo hacer con esto?

Como agente Hermes, puedes:
- **Recibir tareas** de agentes OpenClaw
- **Ejecutar comandos** de sistema, código, debugging
- **Enviar resultados** estructurados de vuelta
- **Reportar al usuario** vía Telegram directamente

---

## 📁 Ubicación de Archivos

```
~/.hermes-openclaw-bridge/
├── inbox/       # Mensajes DE OpenClaw PARA ti
├── outbox/      # Mensajes DE ti PARA OpenClaw
├── signals/     # Signals para acciones especiales
├── logs/        # Logs del sistema
└── processed/   # Mensajes ya procesados
```

---

## 🚀 Configuración Inicial

### Paso 1: Instalar dependencias

```bash
pip install inotify-simple python-dotenv requests
```

### Paso 2: Configurar variables de entorno

Crear archivo `~/.hermes-openclaw-bridge/.env`:

```bash
# ===========================================
# CONFIGURACIÓN DEL BRIDGE
# ===========================================

# Directorio base del bridge
BRIDGE_DIR=$HOME/.hermes-openclaw-bridge

# ===========================================
# TELEGRAM (Para enviar reportes al usuario)
# ===========================================

# Bot Token: Obtener de @BotFather en Telegram
# ⚠️ NUNCA commitear este archivo a Git
KIRA_TELEGRAM_TOKEN=TU_TOKEN_AQUI

# Chat ID del usuario principal
# Obtener con: https://api.telegram.org/bot<TOKEN>/getUpdates
KIRA_CHAT_ID=TU_CHAT_ID_AQUI

# ===========================================
# HERMES CONFIG
# ===========================================

# Nombre de tu agente Hermes
HERMES_AGENT_NAME=kira

# Modelo a usar (OpenRouter, Ollama, etc.)
HERMES_MODEL=kimi-k2.6:cloud

# ===========================================
# OPENCLAW CONFIG
# ===========================================

# Nombre del agente OpenClaw que coordina
OPENCLAW_AGENT_NAME=aki

# Usuario principal (Telegram ID)
OPENCLAW_USER_ID=TU_CHAT_ID_AQUI
```

### Paso 3: Crear plantilla `.env.example`

```bash
# Copiar para referencia (sin datos reales)
cp .env .env.example
# Editar .env.example y remover datos sensibles
```

### Paso 4: Iniciar el bridge

```bash
cd ~/.hermes-openclaw-bridge
python3 scripts/bridge_trigger.py &

# Verificar que está corriendo
ps aux | grep bridge_trigger
```

---

## 📥 Cómo Recibir Tareas de OpenClaw

El bridge usa **inotify** para detectar mensajes instantáneamente. No necesitas hacer polling.

### Estructura de un mensaje entrante:

```json
{
  "id": "uuid-del-mensaje",
  "timestamp": "2026-04-22T10:00:00Z",
  "from": "aki",
  "to": "kira",
  "type": "task",
  "priority": "normal",
  "payload": {
    "action": "run_command",
    "command": "uptime",
    "respond_to_kaiho": true
  }
}
```

### Tipos de tareas que puedes recibir:

| Acción | Descripción | Payload esperado |
|--------|-------------|------------------|
| `run_command` | Ejecutar comando de sistema | `command`, `respond_to_kaiho`, `telegram_message` |
| `send_telegram` | Enviar mensaje a Telegram | `message`, `recipient` |
| `send_image` | Enviar imagen a Telegram | `file_path`, `message`, `recipient` |
| `server_status` | Reporte completo del servidor | `respond_to_kaiho` |
| `generate_code` | Generar código | `language`, `description`, `requirements` |
| `custom` | Acción personalizada | Definida por ti |

---

## ✍️ Cómo Responder a OpenClaw

### Método 1: Archivo Directo

```python
import json
from pathlib import Path
from datetime import datetime, timezone
import uuid

BRIDGE_DIR = Path.home() / ".hermes-openclaw-bridge"
OUTBOX = BRIDGE_DIR / "outbox"

def responder_a_openclaw(tipo, payload, reply_to=None):
    msg = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": "kira",  # Tu nombre
        "to": "aki",     # Nombre del agente OpenClaw
        "type": tipo,
        "priority": "normal",
        "payload": payload
    }
    
    if reply_to:
        msg["reply_to"] = reply_to
    
    OUTBOX.mkdir(parents=True, exist_ok=True)
    filepath = OUTBOX / f"{tipo}-{msg['id']}.msg"
    
    with open(filepath, "w") as f:
        json.dump(msg, f, indent=2)
    
    return msg["id"]

# Ejemplo: Responder con resultado
responder_a_openclaw("response", {
    "success": True,
    "result": "Comando ejecutado exitosamente",
    "task_id": "id-de-la-tarea-original"
}, reply_to="id-de-la-tarea-original")
```

### Método 2: Enviar Telegram Directamente

```python
import requests
import os
from dotenv import load_dotenv

load_dotenv(Path.home() / ".hermes-openclaw-bridge" / ".env")

TOKEN = os.getenv("KIRA_TELEGRAM_TOKEN")
CHAT_ID = os.getenv("KIRA_CHAT_ID")

def enviar_telegram(texto, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": texto,
        "parse_mode": parse_mode
    }
    response = requests.post(url, json=payload, timeout=10)
    return response.json()

# Ejemplo
enviar_telegram("🏮 <b>Reporte de Kira</b>\n\nTarea completada exitosamente.")
```

---

## 🔧 Implementación del Bridge Trigger

El script `bridge_trigger.py` es el corazón del sistema:

```python
#!/usr/bin/env python3
"""
Kira Bridge Trigger v3.1
Detecta mensajes entrantes con inotify y los procesa
"""

import json
import sys
import time
import fcntl
from datetime import datetime, timezone
from pathlib import Path
from inotify_simple import INotify, flags

BRIDGE_DIR = Path.home() / ".hermes-openclaw-bridge"
INBOX = BRIDGE_DIR / "inbox"
OUTBOX = BRIDGE_DIR / "outbox"
PROCESSED = BRIDGE_DIR / "logs" / "processed"
LOGS = BRIDGE_DIR / "logs"

class HermesBridge:
    def __init__(self):
        self.agent_name = "kira"
        self.running = False
        self.lock_file = None
        
    def acquire_lock(self):
        """Evita múltiples instancias"""
        lock_path = BRIDGE_DIR / ".bridge.lock"
        self.lock_file = open(lock_path, "w")
        try:
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.log("🔒 Lock adquirido")
            return True
        except IOError:
            self.log("❌ Otra instancia ya corre", "ERROR")
            self.lock_file.close()
            return False
    
    def log(self, mensaje, level="INFO"):
        timestamp = datetime.now(timezone.utc).isoformat()
        log_msg = f"[{timestamp}] [{level}] {mensaje}"
        print(log_msg)
        # También escribir a archivo de log
        log_file = LOGS / "bridge.log"
        with open(log_file, "a") as f:
            f.write(log_msg + "\n")
    
    def process_message(self, msg_file):
        """Procesa un mensaje entrante"""
        try:
            with open(msg_file, "r") as f:
                msg = json.load(f)
            
            if msg.get("to") not in ["kira", "broadcast"]:
                return
            
            self.log(f"📨 Mensaje de {msg['from']}: {msg['type']}")
            
            msg_type = msg.get("type")
            payload = msg.get("payload", {})
            
            if msg_type == "task":
                self.handle_task(msg)
            elif msg_type == "ping":
                self.handle_ping(msg)
            # ... más tipos
            
            # Mover a processed
            if msg_file.exists():
                PROCESSED.mkdir(exist_ok=True)
                msg_file.rename(PROCESSED / msg_file.name)
                self.log("✅ Mensaje procesado")
                
        except Exception as e:
            self.log(f"❌ Error: {e}", "ERROR")
    
    def handle_task(self, msg):
        """Ejecuta una tarea"""
        payload = msg.get("payload", {})
        action = payload.get("action", "")
        
        self.log(f"📝 Tarea: {action}")
        
        # Ejecutar según el tipo de acción
        if action == "run_command":
            self.run_command(payload, msg)
        elif action == "send_telegram":
            self.send_telegram(payload, msg)
        # ... más acciones
    
    def run_command(self, payload, msg):
        """Ejecuta comando de sistema"""
        import subprocess
        
        command = payload.get("command", "")
        respond_to_kaiho = payload.get("respond_to_kaiho", False)
        telegram_template = payload.get("telegram_message", "{result}")
        
        self.log(f"🖥️  Ejecutando: {command}")
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        output = result.stdout + result.stderr
        
        # Responder a OpenClaw
        self.responder_a_openclaw("response", {
            "success": result.returncode == 0,
            "result": output,
            "task_id": msg["id"]
        }, reply_to=msg["id"])
        
        # Enviar a Telegram si se solicitó
        if respond_to_kaiho and telegram_template:
            mensaje_final = telegram_template.format(result=output[:2000])
            self.enviar_telegram(mensaje_final)
    
    def responder_a_openclaw(self, tipo, payload, reply_to=None):
        """Envía respuesta a OpenClaw"""
        msg = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "from": self.agent_name,
            "to": "aki",
            "type": tipo,
            "priority": "normal",
            "payload": payload
        }
        
        if reply_to:
            msg["reply_to"] = reply_to
        
        OUTBOX.mkdir(parents=True, exist_ok=True)
        filepath = OUTBOX / f"{tipo}-{msg['id']}.msg"
        
        with open(filepath, "w") as f:
            json.dump(msg, f, indent=2)
        
        self.log(f"📤 Respuesta enviada: {tipo}")
    
    def enviar_telegram(self, texto, parse_mode="HTML"):
        """Envía mensaje a Telegram"""
        import requests
        import os
        from dotenv import load_dotenv
        
        load_dotenv(BRIDGE_DIR / ".env")
        
        token = os.getenv("KIRA_TELEGRAM_TOKEN")
        chat_id = os.getenv("KIRA_CHAT_ID")
        
        if not token or not chat_id:
            self.log("❌ Falta configuración de Telegram", "ERROR")
            return
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": texto,
            "parse_mode": parse_mode
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.json().get("ok"):
                self.log("✅ Telegram enviado")
            else:
                self.log(f"❌ Error Telegram: {response.json()}", "ERROR")
        except Exception as e:
            self.log(f"❌ Error enviando Telegram: {e}", "ERROR")
    
    def handle_ping(self, msg):
        """Responde a ping"""
        self.log("🏓 Ping recibido, enviando pong")
        self.responder_a_openclaw("pong", {
            "status": "alive",
            "message": "Kira activa (v3.1)",
            "version": "3.1"
        }, reply_to=msg["id"])
    
    def run(self):
        """Inicia el bridge"""
        if not self.acquire_lock():
            return
        
        self.running = True
        self.log("🚀 Kira Bridge v3.1 iniciado")
        
        # Procesar mensajes existentes
        for msg_file in INBOX.glob("*.msg"):
            self.process_message(msg_file)
        
        # Escuchar con inotify
        inotify = INotify()
        watch_flags = flags.CREATE | flags.MOVED_TO
        wd = inotify.add_watch(str(INBOX), watch_flags)
        
        self.log("✅ Escuchando mensajes...")
        
        try:
            while self.running:
                events = inotify.read(timeout=1000)
                for event in events:
                    if event.name.endswith('.msg'):
                        msg_file = INBOX / event.name
                        if msg_file.exists():
                            time.sleep(0.1)  # Esperar a que se escriba completo
                            self.process_message(msg_file)
        except KeyboardInterrupt:
            pass
        finally:
            inotify.rm_watch(wd)
            self.log("👋 Bridge detenido")
            if self.lock_file:
                fcntl.flock(self.lock_file, fcntl.LOCK_UN)
                self.lock_file.close()

if __name__ == "__main__":
    bridge = HermesBridge()
    try:
        bridge.run()
    except KeyboardInterrupt:
        pass
```

---

## 📊 Ejemplos de Uso

### Ejemplo 1: Recibir y Ejecutar Comando

```python
# Mensaje entrante en inbox/
{
  "type": "task",
  "payload": {
    "action": "run_command",
    "command": "docker ps --format 'table {{.Names}}\\t{{.Status}}'",
    "respond_to_kaiho": true,
    "telegram_message": "🐳 <b>Contenedores Docker</b>\n\n<pre>{result}</pre>"
  }
}

# Tu script debe:
# 1. Ejecutar el comando
# 2. Enviar resultado a OpenClaw (outbox/)
# 3. Enviar reporte a Telegram
```

### Ejemplo 2: Enviar Imagen

```python
# Mensaje entrante
{
  "type": "task",
  "payload": {
    "action": "send_image",
    "file_path": "/ruta/imagen.jpg",
    "message": "Imagen generada",
    "respond_to_kaiho": true
  }
}

# Tu script debe:
# 1. Verificar que el archivo existe
# 2. Enviar a Telegram con bot.send_photo()
# 3. Confirmar a OpenClaw
```

---

## ⚠️ Troubleshooting

### Problema: Bridge no detecta mensajes

**Solución:**
```bash
# Verificar que inotify funciona
ls -la /proc/sys/fs/inotify/
# Verificar que el bridge corre
ps aux | grep bridge_trigger
# Reiniciar
pkill -f bridge_trigger
python3 scripts/bridge_trigger.py &
```

### Problema: Telegram no envía

**Solución:**
1. Verificar token en `.env`
2. Verificar chat_id
3. Probar manualmente:
```bash
curl "https://api.telegram.org/bot<TOKEN>/sendMessage?chat_id=<ID>&text=test"
```

### Problema: Múltiples instancias

**Solución:**
```bash
# El lock file previene esto
# Si hay error, eliminar lock y reiniciar
rm ~/.hermes-openclaw-bridge/.bridge.lock
python3 scripts/bridge_trigger.py &
```

---

## 🎓 Mejores Prácticas

1. **Siempre usar lock** - Evita múltiples instancias
2. **Mover a processed/** - Limpia inbox/outbox después de procesar
3. **Loggear todo** - Esencial para debugging
4. **Manejar timeouts** - Comandos pueden tardar
5. **Validar payloads** - JSON puede estar corrupto
6. **Usar signals** - Para acciones complejas

---

## 📚 Recursos

- [README.md](../README.md) - Documentación general
- [OPENCLAW_AGENT_GUIDE.md](./OPENCLAW_AGENT_GUIDE.md) - Guía para OpenClaw
- [ARCHITECTURE.md](./ARCHITECTURE.md) - Detalles técnicos

---

**Versión:** 3.1  
**Última actualización:** 2026-04-22  
**Para:** Agentes Hermes que necesitan comunicarse con OpenClaw
