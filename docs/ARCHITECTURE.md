# 🏗️ Arquitectura del Sistema Hermes ↔ OpenClaw Bridge

**Documentación técnica detallada del sistema**

---

## 📋 Resumen

El sistema **Hermes ↔ OpenClaw Bridge** permite comunicación bidireccional entre múltiples agentes de IA usando un sistema de archivos JSON con notificación en tiempo real mediante **inotify**.

---

## 🎯 Objetivos del Sistema

1. **Comunicación asíncrona** - Agentes pueden "hablar" sin estar conectados
2. **Persistencia** - Mensajes se guardan hasta ser procesados
3. **Escalabilidad** - Soporta múltiples agentes (Aki, Kira, Mika, etc.)
4. **Fiabilidad** - File locking evita condiciones de carrera
5. **Extensibilidad** - Fácil añadir nuevos tipos de tareas

---

## 🏛️ Arquitectura General

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              SISTEMA COMPLETO                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────┐              ┌─────────────────────┐             │
│  │     OpenClaw        │              │     Hermes          │             │
│  │                     │              │                     │             │
│  │  ┌───────────────┐  │              │  ┌───────────────┐  │             │
│  │  │   Aki (Agent) │  │              │  │  Kira (Agent) │  │             │
│  │  │               │  │              │  │               │  │             │
│  │  │ - Telegram    │  │              │  │  - CLI        │  │             │
│  │  │ - WhatsApp    │  │              │  │  - System     │  │             │
│  │  │ - Coordina    │  │              │  │  - Code Gen   │  │             │
│  │  └───────┬───────┘  │              │  └───────┬───────┘  │             │
│  │          │          │              │          │          │             │
│  └──────────┼──────────┘              └──────────┼──────────┘             │
│             │                                    │                        │
│             │                                    │                        │
│             ▼                                    ▼                        │
│  ┌──────────────────────────────────────────────────────────┐          │
│  │                   BRIDGE (Sistema de Archivos)              │          │
│  │                                                            │          │
│  │   ┌─────────────────────────────────────────────────────┐  │          │
│  │   │              Bridge Trigger (Daemon)                 │  │          │
│  │   │                                                      │  │          │
│  │   │  - File Lock: fcntl.flock()                         │  │          │
│  │   │  - Inotify: CREATE, MOVED_TO                      │  │          │
│  │   │  - Message Queue: FIFO                            │  │          │
│  │   └─────────────────────────────────────────────────────┘  │          │
│  │                                                            │          │
│  │   ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌────────┐ │          │
│  │   │ inbox/  │    │ outbox/ │    │signals/ │    │logs/   │ │          │
│  │   │         │    │         │    │         │    │        │ │          │
│  │   │ Aki→Kira│    │ Kira→Aki│    │ Special │    │ Status │ │          │
│  │   └─────────┘    └─────────┘    └─────────┘    └────────┘ │          │
│  │                                                            │          │
│  └────────────────────────────────────────────────────────────┘          │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📁 Estructura de Directorios

```
.hermes-openclaw-bridge/
├── inbox/              # Mensajes entrantes (DE otros agentes)
│   └── *.msg          # Archivos JSON (no borrar manualmente)
│
├── outbox/             # Mensajes salientes (A otros agentes)
│   ├── *.msg          # Archivos JSON temporales
│   └── processed/     # Mensajes ya enviados
│
├── signals/            # Signals para acciones especiales
│   ├── telegram_send/   # Enviar a Telegram
│   ├── system_cmd/     # Ejecutar comandos
│   └── processed/     # Signals procesados
│
├── logs/               # Logs del sistema
│   ├── bridge.log      # Log principal
│   ├── processed/      # Mensajes procesados
│   └── status.json     # Estado actual
│
├── scripts/            # Scripts de utilidad
│   ├── bridge_trigger.py       # Daemon principal
│   ├── send_message.py         # Enviar mensaje manual
│   └── process_signal.py       # Procesador de signals
│
└── .env                # Configuración (NO versionar)
```

---

## 🔄 Flujo de Mensajes

### Flujo 1: OpenClaw → Hermes

```
Aki (OpenClaw)              Bridge (inotify)              Kira (Hermes)
     │                              │                              │
     │  1. Escribe msg en outbox/  │                              │
     │ ───────────────────────────► │                              │
     │                              │                              │
     │                              │  2. inotify detecta CREATE    │
     │                              │                              │
     │                              │  3. Lee JSON, valida         │
     │                              │                              │
     │                              │  4. Mueve a inbox/         │
     │                              │ ───────────────────────────► │
     │                              │                              │
     │                              │                              │ 5. inotify detecta
     │                              │                              │
     │                              │                              │ 6. Procesa tarea
     │                              │                              │
     │                              │                              │ 7. Escribe respuesta
     │                              │                              │    en outbox/
```

### Flujo 2: Hermes → OpenClaw

```
Kira (Hermes)               Bridge (inotify)              Aki (OpenClaw)
     │                              │                              │
     │  1. Escribe msg en outbox/  │                              │
     │ ───────────────────────────► │                              │
     │                              │                              │
     │                              │  2. inotify detecta CREATE    │
     │                              │                              │
     │                              │  3. Lee JSON, valida         │
     │                              │                              │
     │                              │  4. Mueve a inbox/ (Aki)     │
     │                              │ ───────────────────────────► │
     │                              │                              │
     │                              │                              │ 5. inotify detecta
     │                              │                              │
     │                              │                              │ 6. Notifica a Aki
     │                              │                              │
     │                              │                              │ 7. Aki lee y procesa
```

---

## 📋 Formato de Mensajes

### Estructura Base

```json
{
  "id": "uuid-v4-unico",
  "timestamp": "2026-04-22T10:00:00+00:00",
  "from": "nombre-agente-origen",
  "to": "nombre-agente-destino",
  "type": "task|ping|status|response|error",
  "priority": "low|normal|high|urgent",
  "payload": {}
}
```

### Campos Opcionales

```json
{
  "reply_to": "uuid-del-mensaje-original",
  "expires_at": "2026-04-22T11:00:00+00:00",
  "tags": ["backup", "urgent"]
}
```

---

## 🔒 Mecanismo de File Locking

### Problema: Condiciones de Carrera

Sin locking, múltiples instancias podrían:
1. Procesar el mismo mensaje 2+ veces
2. Mover archivos que otro proceso está leyendo
3. Corromper el estado del sistema

### Solución: fcntl.flock()

```python
import fcntl

class HermesBridge:
    def acquire_lock(self):
        lock_path = BRIDGE_DIR / ".bridge.lock"
        self.lock_file = open(lock_path, "w")
        
        try:
            # LOCK_EX = Exclusive lock
            # LOCK_NB = No bloquear, fallar inmediatamente
            fcntl.flock(self.lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except IOError:
            # Otra instancia tiene el lock
            return False
    
    def release_lock(self):
        if self.lock_file:
            fcntl.flock(self.lock_file, fcntl.LOCK_UN)
            self.lock_file.close()
```

### Comportamiento del Lock

| Escenario | Resultado |
|-----------|-----------|
| Primera instancia inicia | ✅ Adquiere lock, corre normal |
| Segunda instancia intenta iniciar | ❌ Detecta lock, sale con error |
| Primera instancia termina | 🔓 Libera lock, archivo puede borrarse |
| Segunda instancia reintenta | ✅ Ahora adquiere lock, corre normal |

---

## 📡 Sistema de Inotify

### ¿Qué es inotify?

Sistema del kernel Linux que notifica cambios en filesystem en tiempo real:
- **CREATE**: Nuevo archivo creado
- **MODIFY**: Archivo modificado
- **MOVED_TO**: Archivo movido al directorio
- **DELETE**: Archivo eliminado

### Implementación en el Bridge

```python
from inotify_simple import INotify, flags

class HermesBridge:
    def watch_with_inotify(self):
        inotify = INotify()
        
        # Flags a escuchar
        watch_flags = flags.CREATE | flags.MOVED_TO
        
        # Añadir watcher al directorio inbox
        wd = inotify.add_watch(str(INBOX), watch_flags)
        
        # Loop principal
        while self.running:
            # Esperar eventos (timeout 1 segundo)
            events = inotify.read(timeout=1000)
            
            for event in events:
                # Filtrar archivos .msg
                if event.name.endswith('.msg'):
                    msg_file = INBOX / event.name
                    self.process_message(msg_file)
        
        # Limpiar
        inotify.rm_watch(wd)
```

### Ventajas vs Polling

| Método | Latencia | CPU Usage | Complejidad |
|--------|----------|-----------|---------------|
| Polling | Alta (5s+) | Alta | Baja |
| **inotify** | **Baja (~100ms)** | **Baja** | **Media** |
| WebSockets | Baja | Media | Alta |

---

## 🎯 Sistema de Signals

### ¿Cuándo usar Signals?

Para acciones que requieren coordinación entre múltiples componentes:
- Enviar imagen a Telegram
- Ejecutar comando de sistema
- Transferencia de archivos grandes

### Estructura de un Signal

```json
{
  "type": "signal",
  "id": "signal-uuid",
  "timestamp": "2026-04-22T10:00:00Z",
  "signal_type": "telegram_send|system_cmd|file_transfer",
  "payload": {
    "file_path": "/ruta/al/archivo",
    "message": "Texto",
    "recipient": "telegram"
  },
  "from_agent": "kira",
  "to_agent": "aki",
  "status": "pending|processing|completed|error"
}
```

### Flujo de Procesamiento de Signals

```
1. Agente crea signal en signals/
   ↓
2. Signal Processor (separado) detecta con inotify
   ↓
3. Procesa según signal_type
   ↓
4. Actualiza status del signal
   ↓
5. Mueve a signals/processed/
   ↓
6. Opcionalmente notifica al agente original
```

---

## 🗂️ Gestión de Estados

### Estados del Bridge

```json
{
  "status": "idle|busy|error",
  "current_task": "uuid-o-null",
  "last_update": "2026-04-22T10:00:00Z",
  "version": "3.1",
  "uptime_seconds": 3600
}
```

### Estados de Mensajes

| Estado | Descripción | Ubicación |
|----------|-------------|-----------|
| `pending` | Recién creado, esperando procesamiento | inbox/ o outbox/ |
| `processing` | Siendo procesado por el bridge | - (en memoria) |
| `completed` | Procesado exitosamente | processed/ |
| `error` | Falló el procesamiento | processed/ (con flag error) |

---

## 🔧 Componentes del Sistema

### 1. Bridge Trigger (Daemon)

```python
# Responsabilidades:
- Mantener file lock exclusivo
- Escuchar inbox/ con inotify
- Procesar mensajes entrantes
- Mover a processed/
- Loggear operaciones
```

### 2. Message Handlers

```python
# Responsabilidades:
- handle_task(): Ejecutar acciones
- handle_ping(): Responder con pong
- handle_status(): Loggear estado
- handle_response(): Procesar respuestas
- handle_error(): Reportar errores
```

### 3. Signal Processor

```python
# Responsabilidades:
- Escuchar signals/ con inotify
- Ejecutar acciones según signal_type
- Actualizar status de signals
- Reportar resultados
```

### 4. Status Monitor

```python
# Responsabilidades:
- Escribir estado actual a status.json
- Rotar logs
- Limpieza de archivos viejos
```

---

## 📊 Métricas y Monitoreo

### Métricas Clave

| Métrica | Descripción | Target |
|---------|-------------|--------|
| Latencia de procesamiento | Tiempo desde CREATE hasta procesado | < 500ms |
| Mensajes pendientes | Cantidad en inbox/ | < 10 |
| Errores por hora | Fallos de procesamiento | < 1 |
| Uptime | Tiempo de actividad | > 99% |

### Comandos de Monitoreo

```bash
# Ver estado actual
cat ~/.hermes-openclaw-bridge/status/bridge.json

# Ver mensajes pendientes
ls -la ~/.hermes-openclaw-bridge/inbox/ | wc -l

# Ver logs recientes
tail -f ~/.hermes-openclaw-bridge/logs/bridge.log

# Ver uso de recursos
ps aux | grep bridge_trigger
```

---

## 🛡️ Seguridad

### Consideraciones de Seguridad

1. **File Permissions**
   - Directorio bridge: `700` (solo owner)
   - Archivos .env: `600` (solo owner)
   - Logs: `644` (owner puede leer/escribir)

2. **Validación de Payloads**
   - Sanitizar paths de archivos
   - Validar JSON antes de parsear
   - Limitar tamaño de payloads (< 10MB)

3. **Ejecución de Comandos**
   - Usar `subprocess.run()` con `shell=False` si es posible
   - Validar comandos contra whitelist
   - Timeout obligatorio (evitar bloqueos)

4. **Tokens y Secrets**
   - NUNCA en código fuente
   - Usar variables de entorno
   - Rotar tokens periódicamente

---

## 🔄 Casos de Uso Avanzados

### Caso 1: Pipeline de Imágenes

```
1. Aki genera imagen con AI
2. Aki envía task a Kira: "procesar imagen"
3. Kira recibe, procesa con Python/PIL
4. Kira guarda resultado en /ruta/
5. Kira crea signal: "send_telegram"
6. Signal Processor envía imagen a Telegram
7. Kira envía response a Aki: "completado"
```

### Caso 2: Monitoreo de Servidor

```
1. Cron ejecuta script cada 5 minutos
2. Script escribe task en outbox/
3. Bridge detecta, mueve a inbox/ (Kira)
4. Kira recibe: "check_server_status"
5. Kira ejecuta comandos de monitoreo
6. Kira envía reporte a Telegram directo
7. Kira envía status a Aki
```

### Caso 3: Generación de Código

```
1. Usuario pide a Aki: "generar script de backup"
2. Aki delega a Kira (mejor para código)
3. Kira genera script Python
4. Kira guarda en ~/scripts/backup.py
5. Kira crea signal con path del archivo
6. Signal Processor notifica a usuario
7. Kira reporta a Aki: "script generado en /ruta"
```

---

## 🔮 Futuras Mejoras

### Posibles Extensiones

1. **WebSocket Bridge**: Comunicación en tiempo real sin filesystem
2. **Message Queue**: Usar Redis/RabbitMQ para alta carga
3. **Web Dashboard**: Interfaz visual para monitoreo
4. **Plugin System**: Facilitar añadir nuevos tipos de tareas
5. **Distributed Agents**: Agentes en múltiples máquinas

---

## 📚 Referencias

- [README.md](../README.md) - Documentación general
- [OPENCLAW_AGENT_GUIDE.md](./OPENCLAW_AGENT_GUIDE.md) - Guía para OpenClaw
- [HERMES_AGENT_GUIDE.md](./HERMES_AGENT_GUIDE.md) - Guía para Hermes

---

**Versión:** 3.1  
**Arquitecto:** Aki & Kira  
**Última actualización:** 2026-04-22
