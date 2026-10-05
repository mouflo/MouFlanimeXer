"""
Connexion à MouFlanimeXer: vraie page de connexion (formulaire HTML), compatible avec les gestionnaires de
mots de passe (Bitwarden, etc.).

Identifiant + mot de passe se définissent sur le serveur avec:   bash /opt/mouflanimexer/set-login.sh
Ils sont stockés dans /opt/mouflanimexer/login.json (hors GitHub, lisible par root seulement). Seul un HASH du
mot de passe est conservé, jamais le mot de passe lui-même.
"""

import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
import time
from pathlib import Path
from urllib.parse import quote

from flask import Response, redirect, render_template_string, request, session
from flask.sessions import SecureCookieSessionInterface
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = Path(__file__).resolve().parent
LOGIN_FILE = BASE_DIR / "login.json"
KEY_FILE = BASE_DIR / "session_key"

REMEMBER_DAYS = 30
MAX_FAILS_IP = 5
MAX_FAILS_GLOBAL = 30
WINDOW = 600  # secondes

_fails = {}
_fails_all = []
_lock = threading.Lock()


def _creds():
    try:
        data = json.loads(LOGIN_FILE.read_text(encoding="utf-8"))
        user, hashed = str(data.get("user", "")).strip(), str(data.get("hash", "")).strip()
        return (user, hashed) if user and hashed else ("", "")
    except (OSError, ValueError):
        return ("", "")


def configured():
    return all(_creds())


def _fingerprint():
    """Change quand le mot de passe change: les anciennes sessions deviennent invalides"""
    return hashlib.sha256(_creds()[1].encode()).hexdigest()[:16]


def _secret_key():
    env = os.getenv("SECRET_KEY", "").strip()
    if env:
        return env
    try:
        # création atomique: le service web et la tâche cron peuvent démarrer en même temps
        try:
            fd = os.open(KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as f:
                f.write(secrets.token_hex(32))
        except FileExistsError:
            pass
        for _ in range(20):  # laisse le temps à l'autre processus d'écrire la clé
            key = KEY_FILE.read_text().strip()
            if key:
                return key
            time.sleep(0.05)
    except OSError:
        pass
    return secrets.token_hex(32)  # sessions perdues au redémarrage, mais jamais de clé prévisible


def _recent(stamps, now):
    return [t for t in stamps if now - t < WINDOW]


def _blocked(ip):
    now = time.time()
    with _lock:
        _fails[ip] = _recent(_fails.get(ip, []), now)
        _fails_all[:] = _recent(_fails_all, now)
        return len(_fails[ip]) >= MAX_FAILS_IP or len(_fails_all) >= MAX_FAILS_GLOBAL


def _register_fail(ip):
    now = time.time()
    with _lock:
        _fails.setdefault(ip, []).append(now)
        _fails_all.append(now)


def _clear_fails(ip):
    with _lock:
        _fails.pop(ip, None)


LOGIN_HTML = """<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Connexion — MouFlanimeXer</title>
<link rel="icon" type="image/svg+xml" href="/icons/mouflanimexer.svg"><link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png"><link rel="manifest" href="/icons/manifest.webmanifest"><meta name="theme-color" content="#121315">
<style>
  * { box-sizing: border-box; }
  body { font-family: system-ui, sans-serif; background: #121212; color: #e0e0e0; display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 16px; }
  .login-box { background: #1e1e1e; border: 1px solid #333; border-radius: 8px; padding: 30px; width: 100%; max-width: 360px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }
  h2 { margin-top: 0; font-size: 1.3em; text-align: center; color: #fff; }
  label { display: block; margin-top: 15px; font-size: 0.9em; color: #aaa; }
  input[type=text], input[type=password] { width: 100%; padding: 10px; margin-top: 5px; border-radius: 4px; border: 1px solid #444; background: #2a2a2a; color: #fff; font-size: 16px; }
  input:focus { outline: none; border-color: #2e7d32; }
  .remember { display: flex; align-items: center; gap: 8px; margin-top: 15px; font-size: 0.9em; color: #aaa; }
  .remember input { width: 18px; height: 18px; accent-color: #2e7d32; margin: 0; }
  .remember label { margin: 0; }
  button { width: 100%; padding: 10px; margin-top: 22px; background: #2e7d32; color: white; border: none; border-radius: 4px; font-weight: bold; cursor: pointer; font-size: 1em; }
  button:hover { background: #388e3c; }
  .error { color: #ff5252; font-size: 0.9em; margin-top: 15px; text-align: center; }
  .setup { font-size: 0.9em; line-height: 1.5; color: #ccc; margin-top: 15px; }
  .setup code { display: block; background: #2a2a2a; padding: 10px; border-radius: 4px; margin: 10px 0; user-select: all; word-break: break-all; color: #9f9; }
</style>
</head>
<body>
<div class="login-box">
  <h2>MouFlanimeXer</h2>
  {% if not configured %}
    <div class="error">Aucun identifiant n'est encore défini sur ce serveur.</div>
    <div class="setup">
      Tape cette commande dans le terminal du serveur, puis reviens ici :
      <code>bash /opt/mouflanimexer/set-login.sh</code>
      Elle te demandera un identifiant et un mot de passe.
    </div>
  {% else %}
    {% if error %}<div class="error" role="alert">{{ error }}</div>{% endif %}
    <form method="post" action="/login" autocomplete="on">
      <input type="hidden" name="next" value="{{ next }}">
      <label for="username">Identifiant</label>
      <input type="text" id="username" name="username" autocomplete="username" autocapitalize="off" autocorrect="off" spellcheck="false" required autofocus value="{{ username }}">
      <label for="password">Mot de passe</label>
      <input type="password" id="password" name="password" autocomplete="current-password" required>
      <div class="remember">
        <input type="checkbox" id="remember" name="remember" value="1" checked>
        <label for="remember">Rester connecté {{ days }} jours</label>
      </div>
      <button type="submit">Se connecter</button>
    </form>
  {% endif %}
</div>
</body>
</html>
"""


def _safe_next(value):
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value and not value.startswith("/login"):
        return value
    return "/"


def _page(error="", username="", status=200):
    html = render_template_string(
        LOGIN_HTML, configured=configured(), error=error, username=username,
        next=_safe_next(request.values.get("next", "")), days=REMEMBER_DAYS,
    )
    resp = Response(html, status=status, mimetype="text/html")
    resp.headers["Cache-Control"] = "no-store"
    return resp


class _Cookies(SecureCookieSessionInterface):
    """Cookie 'Secure' seulement en HTTPS (derrière le proxy) → marche aussi en http local"""

    def get_cookie_secure(self, app):
        return request.is_secure


def is_logged_in():
    user, _ = _creds()
    return bool(user and session.get("u") == user and hmac.compare_digest(session.get("f", ""), _fingerprint()))


def init_app(app):
    app.secret_key = _secret_key()
    app.session_interface = _Cookies()
    app.config.update(
        SESSION_COOKIE_NAME="mouflanimexer_session",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=REMEMBER_DAYS * 86400,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    @app.route("/icons/<path:name>")
    def app_icons(name):
        from flask import send_from_directory
        resp = send_from_directory(BASE_DIR / "icons", name, max_age=86400)
        if name.endswith(".webmanifest"):
            resp.mimetype = "application/manifest+json"
        return resp

    @app.route("/favicon.ico")
    def app_favicon():
        from flask import send_from_directory
        return send_from_directory(BASE_DIR / "icons", "favicon-32.png", max_age=86400)

    @app.before_request
    def require_login():
        if request.path in ("/login", "/favicon.ico") or request.path.startswith("/icons/") or is_logged_in():
            return None
        target = request.full_path.rstrip("?") if request.method == "GET" else "/"
        return redirect("/login?next=" + quote(target, safe=""))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "GET":
            if is_logged_in():
                return redirect(_safe_next(request.args.get("next", "")))
            return _page()

        if not configured():
            return _page(status=503)
        ip = request.remote_addr or "?"
        if _blocked(ip):
            print(f"[connexion] bloqué (trop d'essais) depuis {ip}", file=sys.stderr, flush=True)
            return _page("Trop d'essais ratés. Réessaie dans quelques minutes.", status=429)

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user, hashed = _creds()
        # Les deux vérifications sont toujours faites: on ne révèle pas lequel est faux
        user_ok = hmac.compare_digest(username.encode(), user.encode())
        pass_ok = check_password_hash(hashed, password)
        if user_ok and pass_ok:
            _clear_fails(ip)
            session.clear()
            session["u"] = user
            session["f"] = _fingerprint()
            session.permanent = request.form.get("remember") == "1"
            return redirect(_safe_next(request.form.get("next", "")))

        _register_fail(ip)
        print(f"[connexion] échec depuis {ip} (identifiant « {username[:30]} »)", file=sys.stderr, flush=True)
        time.sleep(0.6)
        return _page("Identifiant ou mot de passe incorrect.", username=username, status=401)

    @app.route("/logout", methods=["GET", "POST"])
    def logout():
        session.clear()
        return redirect("/login")

    @app.after_request
    def security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp


def _write_login(user, password):
    if not re.fullmatch(r"[A-Za-z0-9._@+-]{2,64}", user):
        raise SystemExit("❌ Identifiant: 2 à 64 caractères (lettres, chiffres, . _ @ + -)")
    if len(password) < 8:
        raise SystemExit("❌ Mot de passe trop court (8 caractères minimum)")
    payload = json.dumps({"user": user, "hash": generate_password_hash(password)})
    tmp = LOGIN_FILE.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(payload)
    os.replace(tmp, LOGIN_FILE)
    os.chmod(LOGIN_FILE, 0o600)
    print(f"✅ Identifiant « {user} » enregistré (mot de passe haché)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--set-login":
        _write_login(os.environ.get("MF_USER", "").strip(), os.environ.get("MF_PASS", ""))
    else:
        print("Usage: bash set-login.sh")
