#!/bin/bash
# Installe les tâches cron de MouFlanimexer. Idempotent : relançable sans
# risque, et n'ajoute une ligne que si elle n'existe pas déjà — ne touche
# JAMAIS aux lignes cron des autres applications (ex: Moufloster).

set -e

REPO_DIR="/opt/mouflanimexer"
DEPLOY_SCRIPT="$REPO_DIR/deploy.sh"
DEPLOY_LOG="/var/log/mouflanimexer-cron.log"
WATCH_LOG="$REPO_DIR/sonarr_watch.log"

echo "🔧 Configuration des cronjobs MouFlanimexer..."

touch "$DEPLOY_LOG"
chmod 666 "$DEPLOY_LOG"

DEPLOY_ENTRY="*/1 * * * * bash $DEPLOY_SCRIPT >> $DEPLOY_LOG 2>&1"
WATCH_ENTRY="*/2 * * * * cd $REPO_DIR && /usr/bin/python3 mouflanimexer.py --watch-sonarr >> $WATCH_LOG 2>&1"

CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")
NEW_CRON="$CURRENT_CRON"
ADDED=0

if ! echo "$CURRENT_CRON" | grep -qF "$DEPLOY_SCRIPT"; then
    NEW_CRON="$NEW_CRON
$DEPLOY_ENTRY"
    ADDED=1
    echo "✅ Déploiement auto (toutes les 1 min) ajouté"
else
    echo "✅ Déploiement auto déjà configuré"
fi

if ! echo "$CURRENT_CRON" | grep -qF -- "--watch-sonarr"; then
    NEW_CRON="$NEW_CRON
$WATCH_ENTRY"
    ADDED=1
    echo "✅ Watcher Sonarr (toutes les 2 min) ajouté"
else
    echo "✅ Watcher Sonarr déjà configuré"
fi

if [ "$ADDED" -eq 1 ]; then
    echo "$NEW_CRON" | crontab -
fi

echo ""
echo "📋 Crontab actuelle :"
crontab -l
echo ""
echo "📋 Logs :"
echo "   tail -f $DEPLOY_LOG   (déploiement)"
echo "   tail -f $WATCH_LOG    (watcher Sonarr)"
