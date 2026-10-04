#!/bin/bash
# Script de déploiement automatique pour MouFlanimexer — lancé chaque minute
# par cron (voir setup-cronjob.sh). Même principe que MouFloster : vérifie
# GitHub, et ne touche à rien si rien n'a changé.

REPO_DIR="/opt/mouflanimexer"
LOG_FILE="/var/log/mouflanimexer-deploy.log"
SERVICE_NAME="mouflanimexer"

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

touch "$LOG_FILE"

if [ ! -d "$REPO_DIR" ]; then
    log "❌ Répertoire $REPO_DIR introuvable !"
    exit 1
fi

cd "$REPO_DIR"

OLD_COMMIT=$(git rev-parse HEAD)
git fetch origin -q
NEW_COMMIT=$(git rev-parse origin/main 2>/dev/null || git rev-parse origin/master)

if [ "$OLD_COMMIT" = "$NEW_COMMIT" ]; then
    exit 0
fi

log "=== 🚀 Déploiement MouFlanimexer détecté ==="
log "Ancien commit: $OLD_COMMIT"
log "Nouveau commit: $NEW_COMMIT"

log "📥 Téléchargement des changements..."
git reset --hard origin/main || git reset --hard origin/master

# Pas de venv pour MouFlanimexer (python3 système) : on réinstalle juste les
# dépendances système si requirements.txt a changé.
if git diff $OLD_COMMIT HEAD -- requirements.txt | grep -q .; then
    log "📦 Installation des dépendances (requirements.txt modifié)..."
    pip install -q -r requirements.txt --break-system-packages 2>&1 | tee -a "$LOG_FILE"
fi

log "🔄 Redémarrage du service..."
if systemctl is-active --quiet $SERVICE_NAME; then
    systemctl restart $SERVICE_NAME
    sleep 2
    if systemctl is-active --quiet $SERVICE_NAME; then
        log "✅ Déploiement réussi ! Service redémarré."
    else
        log "❌ Erreur : le service n'a pas pu redémarrer."
        exit 1
    fi
else
    log "⚠️  Service n'était pas actif, tentative de démarrage..."
    systemctl start $SERVICE_NAME
    sleep 2
fi

log "=== Fin du déploiement MouFlanimexer ==="
