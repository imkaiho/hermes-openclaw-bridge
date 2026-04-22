# 🌉 Hermes ↔ OpenClaw Bridge

**Sistema de comunicación bidireccional entre agentes de IA**

Este proyecto permite que múltiples agentes de IA (Hermes, OpenClaw, y otros) se comuniquen entre sí de manera estructurada, coordinen tareas, y compartan resultados.

---

## 📋 ¿Qué es esto?

Un **sistema de bridge** (puente) que conecta:
- **Hermes Agent** - Agente CLI independiente (framework Hermes)
- **OpenClaw** - Framework de agentes multi-canal (Telegram, WhatsApp, etc.)

**Caso de uso principal:** Tener múltiples agentes especializados trabajando juntos:
- **Agente OpenClaw** - Coordinador principal, comunicación con usuario (Telegram, WhatsApp, etc.)
- **Agente Hermes** - Especialista en código, DevOps, comandos de sistema

---

## 🏗️ Arquitectura

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│   OpenClaw      │         │   Bridge         │         │   Hermes        │
│   (Agent)       │◄───────►│   (File-based)   │◄───────►│   (Agent)       │
│                 │         │                  │         │                 │
│ - Telegram      │         │ - inbox/         │         │ - CLI           │
│ - WhatsApp      │         │ - outbox/        │         │ - System cmds   │
│ - Coordinación  │         │ - signals/       │         │ - Code gen      │
└─────────────────┘         │ - processed/     │         └─────────────────┘
                            └──────────────────┘
```

**Método de comunicación:** Archivos JSON en filesystem con inotify para detección instantánea.

---

## 🚀 Instalación

### Prerrequisitos

1. **Python 3.10+** instalado
2. **Hermes Agent** instalado y configurado
3. **OpenClaw** instalado y configurado
4. **inotify-simple** para detección de archivos

### Paso 1: Clonar/Descargar

```bash
cd /home/ubuntu/.openclaw/workspace/projects
git clone https://github.com/KV_Kaiho/hermes-openclaw-bridge.git
# O copiar manualmente los archivos
```

### Paso 2: Instalar dependencias

```bash
pip install inotify-simple
# O desde requirements.txt
pip install -r requirements.txt
```

### Paso 3: Configurar directorios

```bash
mkdir -p ~/.hermes-openclaw-bridge/{inbox,outbox,signals,logs,processed}
```

### Paso 4: Configurar credenciales

Crear archivo `~/.hermes-openclaw-bridge/.env` con:

```bash
# Telegram Bot Token (Kira)
KIRA_TELEGRAM_TOKEN=tu_token_aqui

# Telegram Chat ID (Usuario principal)
KIRA_CHAT_ID=tu_chat_id_aqui

# Directorios
BRIDGE_DIR=$HOME/.hermes-openclaw-bridge
```

**⚠️ IMPORTANTE:** Nunca commits `.env` a Git. Usa `.env.example` como plantilla.

---

## 📁 Estructura de Archivos

```
hermes-openclaw-bridge/
├── README.md                      # Este archivo
├── docs/
│   ├── OPENCLAW_AGENT_GUIDE.md   # Guía para agentes OpenClaw
│   ├── HERMES_AGENT_GUIDE.md     # Guía para agentes Hermes
│   └── ARCHITECTURE.md           # Documentación técnica
├── scripts/
│   ├── bridge_trigger.py         # Daemon principal (inotify)
│   ├── send_message.py           # Utilidad para enviar mensajes
│   └── process_signal.py         # Procesador de signals
├── examples/
│   ├── ping_pong.json            # Ejemplo básico
│   ├── task_command.json         # Ejecutar comando
│   └── task_telegram.json        # Enviar Telegram
├── config/
│   └── .env.example              # Plantilla de configuración
├── requirements.txt
└── LICENSE
```

---

## 💡 Uso Básico

### Enviar mensaje de OpenClaw → Hermes

```python
import json
from pathlib import Path
from datetime import datetime
import uuid

BRIDGE_DIR = Path.home() / ".hermes-openclaw-bridge"
OUTBOX = BRIDGE_DIR / "outbox"

msg = {
    "id": str(uuid.uuid4()),
    "timestamp": datetime.utcnow().isoformat(),
    "from": "aki",
    "to": "kira",
    "type": "task",
    "priority": "normal",
    "payload": {
        "action": "run_command",
        "command": "uptime",
        "respond_to_kaiho": True
    }
}

OUTBOX.mkdir(parents=True, exist_ok=True)
filepath = OUTBOX / f"task-{msg['id']}.msg"

with open(filepath, "w") as f:
    json.dump(msg, f, indent=2)

print(f"✅ Mensaje enviado: {filepath}")
```

### Enviar mensaje de Hermes → OpenClaw

```python
# Similar, pero desde el lado de Hermes
# El bridge detecta automáticamente y procesa
```

---

## 📨 Tipos de Mensajes

| Tipo | Descripción | Cuándo usar |
|------|-------------|-------------|
| `task` | Delegar una acción | Pedir que Hermes ejecute algo |
| `ping` | Verificar conectividad | Test de comunicación |
| `status` | Reportar estado | Actualizaciones sin acción requerida |
| `response` | Responder a tarea | Reportar resultado de tarea |
| `error` | Reportar error | Cuando algo falla |

---

## 🔧 Configuración Avanzada

### Signals para Acciones Complejas

Para acciones que requieren coordinación (ej: enviar imagen a Telegram):

```json
{
  "type": "signal",
  "signal_type": "telegram_send",
  "payload": {
    "file_path": "/ruta/imagen.jpg",
    "message": "Texto del mensaje",
    "recipient": "telegram"
  }
}
```

### File Locking

El bridge usa `fcntl.flock()` para evitar múltiples instancias:

```bash
# Solo UNA instancia del bridge debe correr
# El lock file: ~/.hermes-openclaw-bridge/.bridge.lock
```

---

## 🐛 Troubleshooting

### Problema: Mensajes no se procesan

**Solución:**
1. Verificar que el bridge esté corriendo: `ps aux | grep bridge_trigger`
2. Verificar logs: `tail -f ~/.hermes-openclaw-bridge/logs/bridge.log`
3. Verificar permisos de directorios

### Problema: Múltiples instancias

**Solución:**
```bash
# Matar todas las instancias
pkill -f bridge_trigger.py
# Iniciar una sola
python3 scripts/bridge_trigger.py &
```

### Problema: Archivos no se mueven a processed/

**Solución:**
- El bridge ya incluye verificación de existencia
- Si hay error, revisar logs para detalles

---

## 📊 Métricas y Monitoreo

### Ver estado del bridge

```bash
cat ~/.hermes-openclaw-bridge/status/bridge.json
```

### Ver mensajes procesados

```bash
ls -la ~/.hermes-openclaw-bridge/logs/processed/
```

### Ver logs en tiempo real

```bash
tail -f ~/.hermes-openclaw-bridge/logs/bridge.log
```

---

## 🔐 Seguridad

### Nunca commitear:
- `.env` files
- Tokens de API
- Chat IDs personales
- Logs con datos sensibles

### Usar siempre:
- `.gitignore` configurado
- `.env.example` como plantilla
- Variables de entorno para secretos

---

## 🤝 Contribuir

1. Fork el repositorio
2. Crear branch (`git checkout -b feature/nueva-funcionalidad`)
3. Commit cambios (`git commit -m 'Añadir nueva funcionalidad'`)
4. Push (`git push origin feature/nueva-funcionalidad`)
5. Pull Request

---

## 📄 Licencia

MIT License - Ver archivo LICENSE

---

**Creado por:** OpenClaw & Hermes Community  
**Versión:** 3.1  
**Última actualización:** 2026-04-22
