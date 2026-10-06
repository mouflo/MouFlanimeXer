"""
Page « ⚙️ Réglages » de MouFlanimeXer : Telegram (notifications) et Sonarr (rescan + renommage automatiques).
Les valeurs sont enregistrées dans les mêmes petits fichiers JSON qu'avant (hors dépôt git, droits 600) :
    telegram_config.json   {"bot_token": "...", "chat_id": "...", "thread_id": "(facultatif : sujet d'un groupe Telegram)"}
    sonarr_api_config.json {"base_url": "...", "api_key": "..."}
Les secrets ne sont jamais renvoyés à la page (seulement leurs derniers caractères).
"""
import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

from flask import jsonify, render_template, request

logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile(r"^\d{5,}:[A-Za-z0-9_-]{20,}$")
_CHAT_RE = re.compile(r"^(-?\d{3,}|@[A-Za-z0-9_]{4,})$")
_THREAD_RE = re.compile(r"^\d{1,12}$")
_URL_RE = re.compile(r"^https?://[^\s/]+(:\d{1,5})?(/\S*)?$")


def _read(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _http(url, headers=None, payload=None, timeout=10):
    """-> (code, texte). Ne lève rien : un problème réseau devient (0, message)."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={**(headers or {}), **({"Content-Type": "application/json"} if data else {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError) as e:
        return 0, str(getattr(e, "reason", e))


def init_app(app, version_fn, telegram_path, sonarr_path, folders_fn, paths_file=None, paths_defaults=None, busy_fn=None):
    """folders_fn() -> [(libellé, chemin)] : les dossiers utilisés (affichés) ;
    paths_file : data/paths.json, réglable ici ; busy_fn() -> True si un traitement est en cours (pas de redémarrage)."""
    import threading
    import time
    import fs_browser
    fs_browser.init_app(app)
    defaults = paths_defaults or {}

    @app.route("/reglages")
    def settings_page():
        return render_template("reglages.html", version=version_fn())

    @app.route("/api/settings/telegram")
    def telegram_state():
        c = _read(telegram_path)
        ok = bool(c.get("bot_token") and c.get("chat_id"))
        return jsonify({"configured": ok, "chat_hint": ("…" + str(c.get("chat_id"))[-4:]) if ok else "",
                        "thread_id": str(c.get("thread_id") or "")})

    @app.route("/api/settings/telegram", methods=["POST"])
    def telegram_save():
        body = request.get_json(silent=True) or {}
        cur = _read(telegram_path)
        tok, chat = str(body.get("token", "")).strip(), str(body.get("chat_id", "")).strip()
        thread = str(body["thread_id"]).strip() if "thread_id" in body else str(cur.get("thread_id") or "")
        if body.get("action") == "lien":
            trouve = lire_lien(str(body.get("lien", "")))
            if not trouve:
                return jsonify({"ok": False, "error": "Ce lien ne ressemble pas à un lien de message de groupe (https://t.me/c/…). Dans le sujet, appui long sur un message → « Copier le lien »."}), 400
            return jsonify({"ok": True, "chat_id": trouve[0], "thread_id": trouve[1],
                            "message": "Groupe et sujet lus dans le lien : appuie sur « Enregistrer » (un message de test sera envoyé)."})
        if body.get("action") == "detect":
            tok = tok or cur.get("bot_token", "")
            if not _TOKEN_RE.match(tok):
                return jsonify({"ok": False, "error": "Colle d'abord le jeton du bot (ou enregistre-le)."}), 400
            code, text = _http(f"https://api.telegram.org/bot{tok}/getUpdates", payload={"limit": 50, "timeout": 0})
            if code != 200 and "webhook" in str(text).lower():
                return jsonify({"ok": False, "error": WEBHOOK}), 400
            try:
                maj = json.loads(text).get("result", []) if code == 200 else []
            except ValueError:
                maj = []
            for m in reversed(maj):
                msg = m.get("message") or {}
                c = msg.get("chat") or {}
                if c.get("type") == "supergroup" and c.get("id") and msg.get("message_thread_id") and msg.get("is_topic_message"):
                    return jsonify({"ok": True, "chat_id": str(c["id"]), "thread_id": str(msg["message_thread_id"]),
                                    "message": "Groupe et sujet trouvés : pense à cliquer sur « Enregistrer »."})
            return jsonify({"ok": False, "error": "Aucun message de sujet reçu : dans ton groupe, ouvre le sujet de cette appli, écris « bonjour » (le bot doit être administrateur du groupe), puis réessaie."}), 400
        test_only = not tok and not chat and thread == str(cur.get("thread_id") or "")
        tok, chat = tok or cur.get("bot_token", ""), chat or str(cur.get("chat_id", ""))
        if not tok or not chat:
            return jsonify({"ok": False, "error": "Telegram n'est pas encore réglé : renseigne le jeton et l'identifiant."}), 400
        if not _TOKEN_RE.match(tok):
            return jsonify({"ok": False, "error": "Jeton invalide : il ressemble à 123456789:ABC… (donné par @BotFather), sans espace."}), 400
        if not _CHAT_RE.match(chat):
            return jsonify({"ok": False, "error": "Identifiant de discussion invalide : un nombre (ex. 123456789), ou @nom d'un canal."}), 400
        if thread and not _THREAD_RE.match(thread):
            return jsonify({"ok": False, "error": "Le numéro du sujet est un nombre (ex. 4). Laisse vide si tu n'utilises pas de sujets."}), 400
        code, text = _http(f"https://api.telegram.org/bot{tok}/getMe")
        if code != 200:
            return jsonify({"ok": False, "error": ("Telegram refuse ce jeton" if code in (401, 404) else "Telegram injoignable") + (". Rien n'a été enregistré." if not test_only else ".")}), 400
        essai = {"chat_id": chat, "text": "✅ MouFlanimeXer : Telegram fonctionne, tu recevras ici les comptes rendus de remux 🎬"}
        if thread and int(thread) != 1:          # 1 = sujet « Général » : Telegram veut qu'on ne précise rien
            essai["message_thread_id"] = int(thread)
        code, text = _http(f"https://api.telegram.org/bot{tok}/sendMessage", payload=essai)
        if code != 200:
            return jsonify({"ok": False, "error": "Message refusé (as-tu écrit à ton bot au moins une fois ? Le numéro du sujet est-il bon ?)" + (". Rien n'a été enregistré." if not test_only else ".")}), 400
        if test_only:
            return jsonify({"ok": True, "message": "Message de test envoyé : regarde Telegram."})
        _write(telegram_path, {"bot_token": tok, "chat_id": chat, "thread_id": thread})
        logger.info("Telegram réglé depuis la page web")
        return jsonify({"ok": True, "message": "Enregistré : un message de test vient d'arriver sur Telegram."})

    @app.route("/api/settings/sonarr")
    def sonarr_state():
        c = _read(sonarr_path)
        key = c.get("api_key", "")
        return jsonify({"configured": bool(c.get("base_url") and key), "base_url": c.get("base_url", ""), "hint": "…" + key[-4:] if key else "",
                        "path_map": c.get("path_map") or []})

    @app.route("/api/settings/sonarr", methods=["POST"])
    def sonarr_save():
        body = request.get_json(silent=True) or {}
        cur = _read(sonarr_path)
        path_map = cur.get("path_map") or []
        if "path_map" in body:                      # correspondances de chemins Sonarr <-> ce serveur
            path_map = []
            for m in body.get("path_map") or []:
                son, loc = str((m or {}).get("sonarr", "")).strip().rstrip("/"), str((m or {}).get("local", "")).strip().rstrip("/")
                if not son and not loc:
                    continue
                if not son.startswith("/") or not loc.startswith("/"):
                    return jsonify({"ok": False, "error": f"Correspondance invalide : « {son} » ↔ « {loc} » (deux chemins complets commençant par /)."}), 400
                path_map.append({"sonarr": son, "local": loc})
        url = str(body.get("base_url", "")).strip().rstrip("/") or cur.get("base_url", "")
        key = str(body.get("api_key", "")).strip() or cur.get("api_key", "")
        if not _URL_RE.match(url):
            return jsonify({"ok": False, "error": "Adresse invalide : elle doit ressembler à http://192.168.1.50:8989"}), 400
        if not re.match(r"^[A-Za-z0-9]{16,64}$", key):
            return jsonify({"ok": False, "error": "Clé invalide : colle la clé API de Sonarr (Réglages → Général), sans espace."}), 400
        code, text = _http(url + "/api/v3/system/status", headers={"X-Api-Key": key})
        if code == 0:
            return jsonify({"ok": False, "error": f"Sonarr injoignable ({text})"}), 400
        if code in (401, 403):
            return jsonify({"ok": False, "error": "Sonarr refuse cette clé"}), 400
        if code != 200:
            return jsonify({"ok": False, "error": f"Sonarr a répondu une erreur ({code})"}), 400
        if body.get("test"):
            return jsonify({"ok": True, "message": "Sonarr répond et accepte la clé."})
        _write(sonarr_path, {"base_url": url, "api_key": key, "path_map": path_map})
        logger.info("Réglages Sonarr enregistrés depuis la page web")
        return jsonify({"ok": True, "message": "Enregistré : Sonarr répond et accepte la clé."})

    @app.route("/api/settings/folders")
    def folders_state():
        return jsonify({"folders": [{"label": label, "path": str(path), "ok": Path(path).exists()} for label, path in folders_fn()]})

    @app.route("/api/settings/paths")
    def paths_state():
        cur = _read(paths_file) if paths_file else {}
        return jsonify({"work_root": cur.get("work_root") or defaults.get("work_root", ""),
                        "scan_default": cur.get("scan_default") or "",
                        "watch_dirs": cur["sonarr_watch_dirs"] if "sonarr_watch_dirs" in cur else defaults.get("sonarr_watch_dirs", []),
                        "watch_mp4": bool(cur.get("watch_mp4", True)),
                        "busy": bool(busy_fn and busy_fn())})

    @app.route("/api/settings/paths", methods=["POST"])
    def paths_save():
        if not paths_file:
            return jsonify({"ok": False, "error": "Réglage indisponible"}), 400
        if busy_fn and busy_fn():
            return jsonify({"ok": False, "error": "Un traitement est en cours : termine-le ou arrête-le avant de changer les dossiers (l'appli doit redémarrer)."}), 409
        body = request.get_json(silent=True) or {}
        work = str(body.get("work_root", "")).strip().rstrip("/")
        scan = str(body.get("scan_default", "")).strip().rstrip("/")
        watch = [str(w).strip().rstrip("/") for w in (body.get("watch_dirs") or []) if str(w).strip()]
        for label, value in [("dossier de travail", work)] + [("dossier à scanner", scan)] * bool(scan) + [("dossier surveillé", w) for w in watch]:
            if not value.startswith("/") or "\n" in value:
                return jsonify({"ok": False, "error": f"Chemin invalide pour le {label} : « {value} » (chemin complet commençant par /)."}), 400
            if not Path(value).is_dir():
                return jsonify({"ok": False, "error": f"Dossier introuvable sur le serveur ({label}) : « {value} ». Rien n'a été enregistré."}), 400
        if not os.access(work, os.W_OK):
            return jsonify({"ok": False, "error": f"Impossible d'écrire dans « {work} » (droits ? partage en lecture seule ?). Rien n'a été enregistré."}), 400
        _write(paths_file, {"work_root": work, "scan_default": scan, "sonarr_watch_dirs": watch, "watch_mp4": bool(body.get("watch_mp4", True))})
        logger.info("Dossiers mis à jour depuis la page web : travail %s · scan %s · surveillés %s", work, scan or "(travail)", ", ".join(watch) or "(aucun)")
        threading.Thread(target=lambda: (time.sleep(1.5), os._exit(0)), daemon=True).start()   # systemd relance l'appli
        return jsonify({"ok": True, "message": "Enregistré. L'appli redémarre pour relire les dossiers… (le surveillant Sonarr les prend au prochain passage)"})


WEBHOOK = "Ce bot est déjà branché sur une autre application (par exemple Jeedom) : Telegram lui envoie directement les messages, l'appli ne peut donc pas les lire pour détecter quoi que ce soit. Utilise plutôt « Lien d'un message » (appui long sur un message du sujet → Copier le lien), ou crée un bot réservé à tes applis avec @BotFather."

_LIEN = re.compile(r"t\.me/c/(\d{5,})/(\d+)(?:/(\d+))?")


def lire_lien(lien):
    """Lien d'un message de groupe (appui long → « Copier le lien ») → (groupe, sujet) ou None.
    https://t.me/c/1234567890/45/678 : groupe -1001234567890, sujet 45 ; https://t.me/c/1234567890/5 : lien du sujet 5 (1 = « Général »)."""
    m = _LIEN.search(lien or "")
    return ("-100" + m.group(1), m.group(2)) if m else None        # le 2e nombre est toujours le sujet
