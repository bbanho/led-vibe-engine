#!/bin/bash
set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="led-vibe-engine"
SERVICE_FILE="$HOME/.config/systemd/user/${SERVICE_NAME}.service"
VENV_PYTHON="$SCRIPT_DIR/.venv/bin/python3"

echo -e "${BLUE}🔧 Instalando LED Vibe Engine...${NC}"

# 1. Remover serviços antigos conflitantes
echo -e "${BLUE}🧹 Removendo serviços antigos...${NC}"
for OLD in "audio-sync" "silverblue-led-vibe"; do
    OLD_FILE="$HOME/.config/systemd/user/${OLD}.service"
    if systemctl --user is-active --quiet "${OLD}.service" 2>/dev/null; then
        systemctl --user stop "${OLD}.service"
        echo -e "  ${YELLOW}Parado: ${OLD}.service${NC}"
    fi
    if systemctl --user is-enabled --quiet "${OLD}.service" 2>/dev/null; then
        systemctl --user disable "${OLD}.service"
        echo -e "  ${YELLOW}Desabilitado: ${OLD}.service${NC}"
    fi
    if [ -f "$OLD_FILE" ]; then
        rm -f "$OLD_FILE"
        echo -e "  ${RED}Removido: $OLD_FILE${NC}"
    fi
done

# 2. Setup Venv
echo -e "${BLUE}📦 Configurando Python Venv...${NC}"
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    python3 -m venv "$SCRIPT_DIR/.venv"
fi
source "$SCRIPT_DIR/.venv/bin/activate"
pip install --upgrade pip -q
pip install -r "$SCRIPT_DIR/requirements.txt" -q

# 3. Verificar dependências de sistema (PortAudio)
echo -e "${BLUE}🔍 Verificando dependências de sistema...${NC}"
if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
    echo -e "${YELLOW}⚠️  Aviso: 'libportaudio' não encontrado.${NC}"
    echo "    Necessário para 'sounddevice'. Instale com: rpm-ostree install portaudio"
fi

# 4. Wrapper script
echo -e "${BLUE}📝 Configurando wrapper (~/.script/run_led.sh)...${NC}"
mkdir -p "$HOME/.script"
cat > "$HOME/.script/run_led.sh" <<EOF
#!/bin/bash
# LED Vibe Engine - Wrapper de controle
# Uso:
#   run_led.sh              -> Inicia o daemon (Vibe Engine)
#   run_led.sh blue         -> Envia ping azul
#   run_led.sh ping red     -> Envia ping vermelho
#   run_led.sh mode ROCK    -> Muda modo para ROCK

BASE_DIR="$SCRIPT_DIR"

if [ -n "\$1" ]; then
    if [ "\$1" == "ping" ]; then
        COLOR="\${2:-green}"
        "\$BASE_DIR/.venv/bin/python3" "\$BASE_DIR/led_ping_client.py" "\$COLOR"
    elif [ "\$1" == "mode" ]; then
        MODE="\${2:-JAZZ}"
        "\$BASE_DIR/.venv/bin/python3" "\$BASE_DIR/led_ping_client.py" mode "\$MODE"
    else
        "\$BASE_DIR/.venv/bin/python3" "\$BASE_DIR/led_ping_client.py" "\$1"
    fi
else
    "\$BASE_DIR/.venv/bin/python3" "\$BASE_DIR/audio_sync.py"
fi
EOF
chmod +x "$HOME/.script/run_led.sh"

# 5. Systemd Service
echo -e "${BLUE}⚙️  Instalando serviço systemd '${SERVICE_NAME}'...${NC}"
mkdir -p "$HOME/.config/systemd/user"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=LED Vibe Engine
After=bluetooth.target sound.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=${VENV_PYTHON} ${SCRIPT_DIR}/audio_sync.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable "${SERVICE_NAME}.service"
systemctl --user restart "${SERVICE_NAME}.service"

echo ""
echo -e "${GREEN}✅ LED Vibe Engine instalado e iniciado!${NC}"
echo ""
echo -e "Comandos úteis:"
echo -e "  systemctl --user status ${SERVICE_NAME}"
echo -e "  journalctl --user -fu ${SERVICE_NAME}"
echo -e "  ~/.script/run_led.sh blue      (ping azul)"
echo -e "  ~/.script/run_led.sh mode ROCK (modo ROCK)"
