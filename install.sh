#!/bin/bash
# Installation complète de MouFlanimexer sur Proxmox (LXC) — à lancer une
# fois après le clone du repo dans /opt/mouflanimexer. Idempotent : peut être
# relancé sans danger sur une machine déjà installée.

set -e

REPO_DIR="/opt/mouflanimexer"
SERVICE_FILE="$REPO_DIR/mouflanimexer.service"
DEPLOY_SCRIPT="$REPO_DIR/deploy.sh"
CRON_SCRIPT="$REPO_DIR/setup-cronjob.sh"

echo "🎬 Installation de MouFlanimexer"
echo "================================"

if [ ! -d "$REPO_DIR" ]; then
    echo "❌ Erreur : $REPO_DIR introuvable (clone le repo là-bas d'abord)"
    exit 1
fi

# 1. Dépendances système (mkvtoolnix pour mkvmerge/mkvextract, ffmpeg)
echo "📦 Vérification des dépendances système..."
if ! command -v mkvmerge >/dev/null || ! command -v ffmpeg >/dev/null; then
    apt-get update -qq && apt-get install -y -qq mkvtoolnix ffmpeg
fi

# 2. Dépendances Python (pas de venv ici, python3 système)
echo "📦 Installation des dépendances Python..."
pip install -q -r "$REPO_DIR/requirements.txt" --break-system-packages

# 3. Permissions des scripts
chmod +x "$DEPLOY_SCRIPT" "$CRON_SCRIPT"

# 4. Fichiers de config locaux (jamais sur GitHub) s'ils n'existent pas déjà
[ -f "$REPO_DIR/excluded_series.json" ] || echo "[]" > "$REPO_DIR/excluded_series.json"
if [ ! -f "$REPO_DIR/telegram_config.json" ]; then
    echo "⚠️  telegram_config.json absent — notifications Telegram désactivées."
    echo "   Pour les activer : copie telegram_config.json.example vers"
    echo "   telegram_config.json et remplis bot_token/chat_id."
fi

# 5. Service systemd
echo "📋 Installation du service systemd..."
cp "$SERVICE_FILE" /etc/systemd/system/mouflanimexer.service
systemctl daemon-reload
systemctl enable mouflanimexer
systemctl start mouflanimexer

# 6. Seed de l'état du watcher Sonarr — UNIQUEMENT si c'est la toute première
# installation (sinon ça retraiterait tout le catalogue existant). Si le
# fichier d'état existe déjà (migration depuis un autre serveur, ou
# réinstallation), on ne le touche pas.
STATE_FILE="$REPO_DIR/sonarr_watch_state.json"
if [ ! -f "$STATE_FILE" ]; then
    echo "🌱 Premier démarrage : marquage du catalogue existant comme déjà connu..."
    python3 "$REPO_DIR/mouflanimexer.py" --seed-sonarr-state
else
    echo "ℹ️  État du watcher Sonarr déjà présent — pas de seed (normal sur une réinstallation)."
fi

# 7. Cronjobs (déploiement auto + watcher Sonarr)
echo "⏱️  Configuration des mises à jour et du watcher automatiques..."
bash "$CRON_SCRIPT"

echo ""
echo "📊 Statut du service :"
systemctl status mouflanimexer --no-pager

echo ""
echo "✅ Installation terminée !"
echo ""
echo "🌐 Accès : http://localhost:5000"
echo "📋 Logs app        : journalctl -u mouflanimexer -f"
echo "📋 Logs déploiement : tail -f /var/log/mouflanimexer-deploy.log"
echo "📋 Logs watcher     : tail -f $REPO_DIR/sonarr_watch.log"
echo ""
echo "Les mises à jour sont automatiques : chaque minute, le serveur vérifie"
echo "GitHub et redéploie seul s'il y a du nouveau. Rien d'autre à faire."
