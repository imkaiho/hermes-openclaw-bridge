#!/usr/bin/env python3
"""
Script utilitario para enviar mensajes al bridge desde CLI
"""

import json
import uuid
import sys
from datetime import datetime, timezone
from pathlib import Path

# Detectar directorio del bridge
BRIDGE_DIR = Path.home() / ".hermes-openclaw-bridge"
OUTBOX = BRIDGE_DIR / "outbox"

def create_message(from_agent, to_agent, msg_type, payload, priority="normal"):
    """Crea un mensaje estructurado"""
    msg = {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "from": from_agent,
        "to": to_agent,
        "type": msg_type,
        "priority": priority,
        "payload": payload
    }
    return msg

def send_message(msg, dry_run=False):
    """Envía el mensaje al outbox"""
    OUTBOX.mkdir(parents=True, exist_ok=True)
    
    filename = f"{msg['type']}-{msg['id']}.msg"
    filepath = OUTBOX / filename
    
    if dry_run:
        print(f"[DRY RUN] Mensaje se guardaría en: {filepath}")
        print(json.dumps(msg, indent=2))
        return msg["id"]
    
    with open(filepath, "w") as f:
        json.dump(msg, f, indent=2)
    
    print(f"✅ Mensaje enviado: {filepath}")
    return msg["id"]

def main():
    """CLI para enviar mensajes"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enviar mensaje al bridge")
    parser.add_argument("--from", dest="from_agent", required=True, help="Agente origen")
    parser.add_argument("--to", required=True, help="Agente destino")
    parser.add_argument("--type", choices=["task", "ping", "status", "response"], 
                        default="task", help="Tipo de mensaje")
    parser.add_argument("--priority", choices=["low", "normal", "high", "urgent"],
                        default="normal", help="Prioridad")
    parser.add_argument("--action", help="Acción a ejecutar (para task)")
    parser.add_argument("--command", help="Comando a ejecutar")
    parser.add_argument("--message", help="Mensaje")
    parser.add_argument("--payload", type=json.loads, help="Payload JSON completo")
    parser.add_argument("--dry-run", action="store_true", help="Simular sin escribir")
    
    args = parser.parse_args()
    
    # Construir payload
    if args.payload:
        payload = args.payload
    else:
        payload = {}
        if args.action:
            payload["action"] = args.action
        if args.command:
            payload["command"] = args.command
        if args.message:
            payload["message"] = args.message
    
    # Crear y enviar mensaje
    msg = create_message(
        from_agent=args.from_agent,
        to_agent=args.to,
        msg_type=args.type,
        payload=payload,
        priority=args.priority
    )
    
    msg_id = send_message(msg, dry_run=args.dry_run)
    print(f"ID del mensaje: {msg_id}")

if __name__ == "__main__":
    main()