#!/bin/bash
cd "$(dirname "$0")"

# Ativa venv se existir, senão usa sistema
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "bin" ]; then
    source bin/activate
fi

# Executa o script Python
echo "🎵 Iniciando LED Audio Sync (Vibe Engine)..."
python3 audio_sync.py
