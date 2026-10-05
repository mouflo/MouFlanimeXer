"""
Page « ⚙️ Réglages » de MouFlanimeXer : Telegram (notifications) et Sonarr (rescan + renommage automatiques).
Les valeurs sont enregistrées dans les mêmes petits fichiers JSON qu'avant (hors dépôt git, droits 600) :
    telegram_config.json   {"bot_token": "...", "chat_id": "..."}
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


def init_app(app, version_fn, telegram_path, sonarr_path, folders_fn):
    """folders_fn() -> [(libellé, chemin)] : les dossiers utilisés, affichés en lecture seule."""

    @app.route("/reglages")
    def settings_page():
        return render_template("reglages.html", version=version_fn())

    @app.route("/api/settings/telegram")
    def telegram_state():
        c = _read(telegram_path)
        ok = bool(c.get("bot_token") and c.get("chat_id"))
        return jsonify({"configured": ok, "chat_hint": ("…" + str(c.get("chat_id"))[-4:]) if ok else ""})

    @app.route("/api/settings/telegram", methods=["POST"])
    def telegram_save():
        body = request.get_json(silent=True) or {}
        cur = _read(telegram_path)
        tok, chat = str(body.get("token", "")).strip(), str(body.get("chat_id", "")).strip()
        test_only = not tok and not chat
        tok, chat = tok or cur.get("bot_token", ""), chat or str(cur.get("chat_id", ""))
        if not tok or not chat:
            return jsonify({"ok": False, "error": "Telegram n'est pas encore réglé : renseigne le jeton et l'identifiant."}), 400
        if not _TOKEN_RE.match(tok):
            return jsonify({"ok": False, "error": "Jeton invalide : il ressemble à 123456789:ABC… (donné par @BotFather), sans espace."}), 400
        if not _CHAT_RE.match(chat):
            return jsonify({"ok": False, "error": "Identifiant de discussion invalide : un nombre (ex. 123456789), ou @nom d'un canal."}), 400
        code, text = _http(f"https://api.telegram.org/bot{tok}/getMe")
        if code != 200:
            return jsonify({"ok": False, "error": ("Telegram refuse ce jeton" if code in (401, 404) else "Telegram injoignable") + (". Rien n'a été enregistré." if not test_only else ".")}), 400
        code, text = _http(f"https://api.telegram.org/bot{tok}/sendMessage", payload={"chat_id": chat, "text": "✅ MouFlanimeXer : Telegram fonctionne, tu recevras ici les comptes rendus de remux 🎬"})
        if code != 200:
            return jsonify({"ok": False, "error": "Message refusé (as-tu écrit à ton bot au moins une fois ?)" + (". Rien n'a été enregistré." if not test_only else ".")}), 400
        if test_only:
            return jsonify({"ok": True, "message": "Message de test envoyé : regarde Telegram."})
        _write(telegram_path, {"bot_token": tok, "chat_id": chat})
        logger.info("Telegram réglé depuis la page web")
        return jsonify({"ok": True, "message": "Enregistré : un message de test vient d'arriver sur Telegram."})

    @app.route("/api/settings/sonarr")
    def sonarr_state():
        c = _read(sonarr_path)
        key = c.get("api_key", "")
        return jsonify({"configured": bool(c.get("base_url") and key), "base_url": c.get("base_url", ""), "hint": "…" + key[-4:] if key else ""})

    @app.route("/api/settings/sonarr", methods=["POST"])
    def sonarr_save():
        body = request.get_json(silent=True) or {}
        cur = _read(sonarr_path)
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
        _write(sonarr_path, {"base_url": url, "api_key": key})
        logger.info("Réglages Sonarr enregistrés depuis la page web")
        return jsonify({"ok": True, "message": "Enregistré : Sonarr répond et accepte la clé."})

    @app.route("/api/settings/folders")
    def folders_state():
        return jsonify({"folders": [{"label": label, "path": str(path), "ok": Path(path).exists()} for label, path in folders_fn()]})
