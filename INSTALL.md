# 🚀 Installation & Déploiement MouFlanimexer

Guide complet pour installer MouFlanimexer sur un LXC Proxmox, avec démarrage
auto, watcher Sonarr automatique, et mises à jour automatiques. **Ce fichier
est la référence : si le serveur disparaît un jour, tout ce qu'il faut pour
tout reconstruire à l'identique est ici, dans ce dépôt** (à l'exception des
quelques éléments listés dans "Ce qui N'EST PAS dans ce dépôt" plus bas — à
sauvegarder séparément).

Même convention que pour les autres applications de ce compte GitHub (voir
aussi `INSTALL.md` du dépôt MouFloster) : un dossier sous `/opt/<nom>`, un
service systemd du même nom, et une mise à jour automatique par **cronjob**
(pas de webhook — ça expose le serveur sur internet pour rien, voir
l'explication dans l'`INSTALL.md` de MouFloster).

## 📋 Prérequis

- LXC Debian/Ubuntu sur Proxmox, avec accès au NAS Synology monté (ex:
  `/mnt/mouflosyno/...`) — MouFlanimexer ne gère pas ce montage lui-même
- Python 3.8+ (pas de venv ici : dépendances installées au niveau système)
- `mkvtoolnix` (mkvmerge/mkvextract) et `ffmpeg` — `install.sh` les installe
  automatiquement si absents
- Git configuré (le dépôt doit pouvoir faire `git pull` sans mot de passe)
- Accès root

## ⚡ Installation complète (sur une machine neuve)

```bash
# 1. Clone le repo au bon endroit
cd /opt
git clone https://github.com/mouflo/mouflanimexer.git
cd mouflanimexer

# 2. (Optionnel) Active les notifications Telegram
cp telegram_config.json.example telegram_config.json
nano telegram_config.json   # renseigne bot_token et chat_id

# 3. Installe tout : dépendances, service, watcher, mises à jour auto
chmod +x install.sh
bash install.sh
```

**C'est tout.** Le service démarre, se relance seul au boot, le watcher
Sonarr tourne toutes les 2 minutes, et le code se met à jour seul dès qu'un
nouveau commit arrive sur GitHub — sans aucune autre manipulation.

## 📊 Vérifier le statut

```bash
systemctl status mouflanimexer              # l'appli tourne ?
journalctl -u mouflanimexer -f               # logs en direct de l'appli
tail -f /var/log/mouflanimexer-deploy.log    # logs des déploiements
tail -f /var/log/mouflanimexer-cron.log      # logs bruts de la cronjob de déploiement
tail -f /opt/mouflanimexer/sonarr_watch.log  # logs du watcher Sonarr
```

## 🌐 Accès

- **App** : `http://<ip-du-serveur>:5000`

## 🤖 Automatisation en place

`setup-cronjob.sh` (déjà lancé par `install.sh`) installe deux lignes dans
la crontab root — **en les ajoutant à celles déjà présentes, jamais en les
remplaçant**, pour ne jamais effacer la cronjob d'une autre appli (ex:
Moufloster) :

```
*/1 * * * * bash /opt/mouflanimexer/deploy.sh >> /var/log/mouflanimexer-cron.log 2>&1
*/2 * * * * cd /opt/mouflanimexer && /usr/bin/python3 mouflanimexer.py --watch-sonarr >> /opt/mouflanimexer/sonarr_watch.log 2>&1
```

1. **`deploy.sh`** (chaque minute) : compare le commit local à GitHub,
   et s'il y a du neuf, télécharge (`git reset --hard`) + redémarre le
   service.
2. **`--watch-sonarr`** (toutes les 2 min) : parcourt le dossier manga
   (`SONARR_WATCH_DIRS` dans le code) à la recherche de nouveaux épisodes
   stables depuis au moins 2 min, et les traite automatiquement (remux
   audio/sous-titres). Un fichier qu'il ne peut pas traiter sans décision
   humaine est déposé dans `SONARR_REVIEW_DIR` + notification Telegram.
   Depuis la v3.29, un dossier qui disparaît en cours de scan (ex: Sonarr
   renomme une série en même temps) ne fait plus planter le process.

Pour réinstaller ces cronjobs à la main (normalement jamais nécessaire) :
```bash
bash /opt/mouflanimexer/setup-cronjob.sh
```

## 🔧 Configuration avancée

### Chemins spécifiques au NAS (en dur dans le code)

Ces chemins sont définis directement dans `mouflanimexer.py` (pas de
variables d'environnement) — à adapter dans le code si le NAS ou son point
de montage change :
```python
SONARR_WATCH_DIRS = [Path("/mnt/mouflosyno/Emby-Media/Manga")]
SONARR_REVIEW_DIR = Path("/mnt/mouflosyno/MouFlanimexer/A traiter (intervention manuelle)")
SONARR_STATE_PATH = Path("/opt/mouflanimexer/sonarr_watch_state.json")
PORT = 5000
```

### Séries exclues du style personnalisé

`excluded_series.json` (racine du dépôt, pas versionné) — liste JSON de noms
de séries à ignorer. Démarre vide (`[]`), géré via l'interface web ou :
```bash
python3 mouflanimexer.py --list-series            # voir toutes les séries détectées
python3 mouflanimexer.py --exclude-series "Nom exact"
python3 mouflanimexer.py --include-series "Nom exact"
```

### Notifications Telegram

`telegram_config.json` (racine du dépôt, pas versionné, voir
`telegram_config.json.example` pour le format) :
```json
{ "bot_token": "...", "chat_id": "..." }
```
Absent ou invalide → notifications simplement désactivées, rien ne plante.

## 🐛 Dépannage

**L'app ne démarre pas ?**
```bash
journalctl -u mouflanimexer -e
cd /opt/mouflanimexer && python3 mouflanimexer.py   # voir l'erreur en direct
```

**Le watcher Sonarr ne traite rien / plante ?**
```bash
python3 /opt/mouflanimexer/mouflanimexer.py --watch-sonarr   # test manuel, affiche l'erreur
tail -50 /opt/mouflanimexer/sonarr_watch.log
```

**Les mises à jour ne se font pas ?**
```bash
bash /opt/mouflanimexer/deploy.sh       # test manuel, affiche l'erreur
crontab -l                                # les 2 lignes mouflanimexer sont bien là ?
cat /var/log/mouflanimexer-deploy.log
```

## 📝 Fichiers importants (tous dans ce dépôt)

```
/opt/mouflanimexer/
├── mouflanimexer.py              # Application principale (web + watcher Sonarr)
├── requirements.txt              # Dépendances Python
├── mouflanimexer.service         # Service systemd — SOURCE DE VÉRITÉ, à copier dans /etc/systemd/system/
├── deploy.sh                     # Script de déploiement (lancé par cron chaque minute)
├── setup-cronjob.sh              # Installe les 2 lignes cron ci-dessus (idempotent)
├── install.sh                    # Installation complète en une commande sur machine neuve
└── telegram_config.json.example  # Modèle pour activer les notifications Telegram
```

## ⚠️ Ce qui N'EST PAS dans ce dépôt (à sauvegarder séparément)

Ces éléments sont volontairement exclus de git (secrets, données qui
évoluent en permanence, ou fichiers trop volumineux) — si le serveur est
perdu, ils ne reviendront pas avec un simple `git clone` :

- **`fonts/`** : ~250 polices utilisées pour le style des sous-titres —
  volumineux, jamais versionné. **À sauvegarder toi-même** (ex: une archive
  de ce dossier sur le NAS) si tu veux les retrouver après une migration.
- **`telegram_config.json`** : le jeton du bot Telegram.
- **`excluded_series.json`** : la liste des séries exclues — recréable à la
  main via `--exclude-series`, mais plus rapide à restaurer depuis une copie.
- **`sonarr_watch_state.json`** : mémoire du watcher (fichiers déjà traités).
  Sans lui, le premier passage après une migration croirait que tout le
  catalogue existant est "nouveau" — pense à relancer
  `--seed-sonarr-state` avant d'activer le watcher sur une machine neuve si
  tu n'as pas pu récupérer ce fichier (c'est ce que fait `install.sh`
  automatiquement quand le fichier est absent).

## 🎯 Intégration avec Moufloster

Les deux apps tournent sur le même LXC, même convention de déploiement :
- **MouFlanimexer** : `/opt/mouflanimexer`, service `mouflanimexer`, port 5000
- **Moufloster** : `/opt/moufloster`, service `moufloster`, port 8000

---

**Questions ?** Lance l'une des commandes de diagnostic ci-dessus et partage
les logs avec Claude.
