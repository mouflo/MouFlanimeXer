#!/bin/bash
# Installe la tâche cron de MouFlanimexer (watcher Sonarr). Idempotent : relançable sans
# risque, et n'ajoute une ligne que si elle n'existe pas déjà — ne touche
# JAMAIS aux lignes cron des autres applications (ex: Moufloster).

set -e

REPO_DIR="/opt/mouflanimexer"
WATCH_LOG="$REPO_DIR/sonarr_watch.log"

echo "🔧 Configuration du watcher Sonarr de MouFlanimexer..."

WATCH_ENTRY="*/2 * * * * cd $REPO_DIR && /usr/bin/python3 mouflanimexer.py --watch-sonarr >> $WATCH_LOG 2>&1"

CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

if ! echo "$CURRENT_CRON" | grep -qF -- "--watch-sonarr"; then
    NEW_CRON="$CURRENT_CRON
$WATCH_ENTRY"
    echo "$NEW_CRON" | crontab -
    echo "✅ Watcher Sonarr (toutes les 2 min) ajouté"
else
    echo "✅ Watcher Sonarr déjà configuré"
fi

echo ""
echo "📋 Crontab actuelle :"
crontab -l
echo ""
echo "📋 Log :"
echo "   tail -f $WATCH_LOG    (watcher Sonarr)"
