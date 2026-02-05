#!/bin/bash
set -e

# Cores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 Instalando Silverblue LED Controller (Vibe Engine)...${NC}"

# 1. Setup Venv
echo -e "${BLUE}📦 Configurando Python Venv...${NC}"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

# 2. Verificar Dependências de Sistema (PortAudio)
echo -e "${BLUE}🔍 Verificando dependências de sistema...${NC}"
if ! ldconfig -p | grep -q libportaudio; then
    echo -e "${YELLOW}⚠️  Aviso: 'libportaudio' não encontrado.${NC}"
    echo "Necessário para 'sounddevice'. Instale com: rpm-ostree install portaudio"
fi

# 3. Wrapper Script
echo -e "${BLUE}📝 Atualizando Wrapper (~/.script/run_led.sh)...${NC}"
mkdir -p "$HOME/.script"
cat > "$HOME/.script/run_led.sh" <<EOF
#!/bin/bash
# Wrapper para Silverblue LED Controller
# Uso: 
#   ./run_led.sh          -> Inicia Daemon (Vibe Engine)
#   ./run_led.sh blue     -> Envia Ping Azul
#   ./run_led.sh ping red -> Envia Ping Vermelho

BASE_DIR="/var/home/bruno/silverblue-led-controller"

if [ -n "\$1" ]; then
    if [ "\$1" == "ping" ]; then
        COLOR="\${2:-green}"
    else
        COLOR="\$1"
    fi
    python3 "\$BASE_DIR/led_ping_client.py" "\$COLOR"
else
    "\$BASE_DIR/run_audio_sync.sh"
fi
EOF
chmod +x "$HOME/.script/run_led.sh"

# 4. Systemd Service
echo -e "${BLUE}⚙️  Configurando Systemd User Service...${NC}"
mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/silverblue-led-vibe.service" <<EOF
[Unit]
Description=Silverblue LED Controller (Vibe Engine)
After=sound.target
StartLimitIntervalSec=0

[Service]
Type=simple
ExecStart=$HOME/silverblue-led-controller/run_audio_sync.sh
Restart=always
RestartSec=5
StandardOutput=null
StandardError=journal

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable silverblue-led-vibe.service
echo -e "${GREEN}✅ Serviço habilitado (inicia no boot).${NC}"
echo -e "Para iniciar agora: systemctl --user start silverblue-led-vibe.service"

echo -e "${GREEN}✅ Instalação Concluída!${NC}"
echo -e "Comandos úteis:"
echo -e "  ~/.script/run_led.sh blue   (Testar Ping)"
echo -e "  ~/.script/run_led.sh        (Rodar manual)"
