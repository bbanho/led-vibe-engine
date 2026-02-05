#!/usr/bin/env python3
import asyncio
import sys
import socket
import subprocess

SOCKET_PATH = "/tmp/silverblue_led.sock"

async def send_ping(color="green", msg="LED Ping Enviado"):
    # Enviar Notificação GNOME
    try:
        subprocess.run([
            "notify-send", 
            "-a", "Silverblue LED", 
            "-i", "dialog-information",
            msg, 
            f"Cor: {color.upper()}"
        ])
    except Exception as e:
        print(f"⚠️ Falha ao notificar: {e}")

    # Enviar Comando Socket
    try:
        reader, writer = await asyncio.open_unix_connection(SOCKET_PATH)
        message = f"PING {color}"
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
    color = sys.argv[1] if len(sys.argv) > 1 else "magenta"
    custom_msg = sys.argv[2] if len(sys.argv) > 2 else "LED Ping Enviado"
    asyncio.run(send_ping(color, custom_msg))
