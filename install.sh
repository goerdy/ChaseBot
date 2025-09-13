#!/bin/bash

# TelegramChaseBot Installation Script für LXC Container
# Verwendung: wget -O - https://raw.githubusercontent.com/goerdy/ChaseBot/master/install.sh | bash

set -e  # Exit on any error

echo "🤖 TelegramChaseBot Installation Script"
echo "======================================"
echo ""

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Prüfe ob als root ausgeführt
if [ "$EUID" -ne 0 ]; then
    log_error "Bitte führe das Script als root aus: sudo bash install.sh"
    exit 1
fi

# System-Update
log_info "Aktualisiere System-Pakete..."
apt update && apt upgrade -y

# Python und pip installieren
log_info "Installiere Python und pip..."
apt install -y python3 python3-pip python3-venv python3-dev

# Git installieren
log_info "Installiere Git..."
apt install -y git

# Weitere benötigte Pakete
log_info "Installiere weitere Abhängigkeiten..."
apt install -y sqlite3 curl wget

# Erstelle Bot-User
log_info "Erstelle Bot-User 'chasebot'..."
if ! id "chasebot" &>/dev/null; then
    useradd -m -s /bin/bash chasebot
    log_success "User 'chasebot' erstellt"
else
    log_warning "User 'chasebot' existiert bereits"
fi

# Wechsle zu Bot-User
log_info "Wechsle zu Bot-User..."
su - chasebot << 'EOF'

# Setze Home-Verzeichnis
cd /home/chasebot

# Erstelle Bot-Verzeichnis
log_info() {
    echo -e "\033[0;34m[INFO]\033[0m $1"
}

log_success() {
    echo -e "\033[0;32m[SUCCESS]\033[0m $1"
}

log_error() {
    echo -e "\033[0;31m[ERROR]\033[0m $1"
}

log_info "Erstelle Bot-Verzeichnis..."
mkdir -p /home/chasebot/chasebot
cd /home/chasebot/chasebot

# Klone Repository
log_info "Klone Repository von GitHub..."
git clone https://github.com/goerdy/ChaseBot.git .

# Erstelle Python Virtual Environment
log_info "Erstelle Python Virtual Environment..."
python3 -m venv venv

# Aktiviere Virtual Environment
log_info "Aktiviere Virtual Environment..."
source venv/bin/activate

# Installiere Python-Abhängigkeiten
log_info "Installiere Python-Abhängigkeiten..."
pip install --upgrade pip
pip install -r requirements.txt

# Erstelle systemd Service
log_info "Erstelle systemd Service..."

EOF

# Erstelle systemd Service File
cat > /etc/systemd/system/chasebot.service << 'EOF'
[Unit]
Description=TelegramChaseBot - Live-Action Capture the Flag Bot
After=network.target

[Service]
Type=simple
User=chasebot
Group=chasebot
WorkingDirectory=/home/chasebot/chasebot
Environment=PATH=/home/chasebot/chasebot/venv/bin
ExecStart=/home/chasebot/chasebot/venv/bin/python Chase.py
Restart=always
RestartSec=10

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=chasebot

[Install]
WantedBy=multi-user.target
EOF

# Setze Berechtigungen
log_info "Setze Berechtigungen..."
chown -R chasebot:chasebot /home/chasebot/chasebot
chmod +x /home/chasebot/chasebot/Chase.py

# Lade systemd neu
log_info "Lade systemd neu..."
systemctl daemon-reload

# Erstelle Konfigurationsdatei
log_info "Erstelle Konfigurationsdatei..."
cp /home/chasebot/chasebot/config.env.example /home/chasebot/chasebot/config.env

# Setze Berechtigungen für config.env
chown chasebot:chasebot /home/chasebot/chasebot/config.env
chmod 600 /home/chasebot/chasebot/config.env

# Erstelle Update-Script
log_info "Erstelle Update-Script..."
cat > /home/chasebot/chasebot/update.sh << 'EOF'
#!/bin/bash
# Update Script für TelegramChaseBot

echo "🔄 Aktualisiere TelegramChaseBot..."

cd /home/chasebot/chasebot

# Aktiviere Virtual Environment
source venv/bin/activate

# Hole neueste Version
git pull origin master

# Installiere neue Abhängigkeiten
pip install -r requirements.txt

# Starte Bot neu
sudo systemctl restart chasebot

echo "✅ Update abgeschlossen!"
EOF

chmod +x /home/chasebot/chasebot/update.sh
chown chasebot:chasebot /home/chasebot/chasebot/update.sh

# Erstelle Log-Rotation
log_info "Erstelle Log-Rotation..."
cat > /etc/logrotate.d/chasebot << 'EOF'
/home/chasebot/chasebot/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 chasebot chasebot
    postrotate
        systemctl reload chasebot > /dev/null 2>&1 || true
    endscript
}
EOF

# Installation abgeschlossen
log_success "Installation abgeschlossen!"
echo ""
echo "📋 Nächste Schritte:"
echo "1. Bearbeite die Konfiguration: nano /home/chasebot/chasebot/config.env"
echo "2. Setze deinen TELEGRAM_API_KEY und ADMIN Username"
echo "3. Starte den Bot: systemctl start chasebot"
echo "4. Aktiviere Auto-Start: systemctl enable chasebot"
echo "5. Prüfe Status: systemctl status chasebot"
echo "6. Logs anzeigen: journalctl -u chasebot -f"
echo ""
echo "🔧 Bot-Verwaltung:"
echo "- Bot starten: systemctl start chasebot"
echo "- Bot stoppen: systemctl stop chasebot"
echo "- Bot neustarten: systemctl restart chasebot"
echo "- Status prüfen: systemctl status chasebot"
echo "- Logs anzeigen: journalctl -u chasebot -f"
echo "- Update: /home/chasebot/chasebot/update.sh"
echo ""
echo "📁 Bot-Verzeichnis: /home/chasebot/chasebot"
echo "📄 Konfiguration: /home/chasebot/chasebot/config.env"
echo "📊 Logs: journalctl -u chasebot"
echo ""
log_warning "Vergiss nicht, deine Bot-Konfiguration in config.env anzupassen!"
