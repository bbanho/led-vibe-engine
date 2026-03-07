#!/usr/bin/env python3
import asyncio
import sys
import socket
import subprocess

SOCKET_PATH = "/tmp/silverblue_led.sock"

async def send_ping(cmd_arg="green", extra_arg="LED Ping Enviado"):
    # Enviar Notificação GNOME
    try:
        subprocess.run([
            "notify-send", 
            "-a", "Silverblue LED", 
            "-i", "dialog-information",
            extra_arg if not cmd_arg.upper() == "MODE" else f"Alterando modo para {extra_arg}", 
            f"Comando: {cmd_arg.upper()}"
        ])
    except Exception as e:
        print(f"⚠️ Falha ao notificar: {e}")

    # Enviar Comando Socket
    try:
        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
        
        # Lista estendida de modos suportados
        modes = ["STATIC", "DYNAMIC", "WARM_COLD", "VAPORWAVE", "WAR_ZONE", "ROCK", "JAZZ", "TECHNO", "LOFI", "KCD2", "GTA4"]
        
        if cmd_arg.upper() == "MODE" and extra_arg.upper() in modes:
            message = f"MODE {extra_arg.upper()}"
        elif cmd_arg.upper() in modes:
            message = f"MODE {cmd_arg.upper()}"
        elif cmd_arg.lower() == "set" and len(sys.argv) >= 5:
            h, s, b = sys.argv[2], sys.argv[3], sys.argv[4]
            message = f"SET {h} {s} {b}"
        else:
            message = f"PING {cmd_arg}"
            
        writer.write(message.encode())
        await writer.drain()
        writer.close()
        await writer.wait_closed()
        print(f"✅ Comando enviado: {message}")
    except FileNotFoundError:
        print("❌ Serviço LED não está rodando (Socket não encontrado).")
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")

if __name__ == "__main__":
    arg1 = sys.argv[1] if len(sys.argv) > 1 else "magenta"
    arg2 = sys.argv[2] if len(sys.argv) > 2 else "LED Ping Enviado"
    asyncio.run(send_ping(arg1, arg2))
