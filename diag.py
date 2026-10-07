"""
Journal et diagnostic intégrés à l'appli (même principe que MouFloster et MouFlopening) :
- journal dans la console ET dans data/mouflanimexer.log (tourne tout seul : 1 Mo x 3 fichiers)
- /api/diagnostic : le rapport complet affiché dans la fenêtre « Journal »
- /api/clientlog : les erreurs JavaScript du navigateur arrivent aussi dans le journal
- toute erreur Python non gérée est écrite dans le journal avec son détail
"""

import logging
import logging.handlers
import sys
from pathlib import Path

from flask import jsonify, request

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
LOG_FILE = DATA_DIR / "mouflanimexer.log"

logger = logging.getLogger("mouflanimexer")


def setup_logging():
    fmt = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for h in list(root.handlers):
        root.removeHandler(h)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)
    if "unittest" in sys.modules:          # tests automatiques : jamais dans le vrai journal (faux démarrages, fausses alertes)
        return
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        fh.setFormatter(fmt)
        root.addHandler(fh)
    except OSError as e:
        root.warning(f"Journal fichier indisponible : {e}")
    logging.getLogger("werkzeug").setLevel(logging.WARNING)


def tail(path, lines, max_bytes=200_000):
    try:
        path = Path(path)
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            data = f.read().decode("utf-8", errors="replace")
        return "\n".join(data.splitlines()[-lines:])
    except OSError:
        return "(aucun journal pour le moment)"


def init_app(app, version, report_fn):
    logger.info(f"Démarrage MouFlanimeXer v{version} · Python {sys.version.split()[0]}")

    @app.route("/api/diagnostic")
    def api_diagnostic():
        try:
            return jsonify({"report": report_fn()})
        except Exception as e:      # le diagnostic ne doit jamais être lui-même la cause d'une panne
            import traceback
            logger.exception("Rapport de diagnostic impossible")
            return jsonify({"report": f"Impossible de construire le rapport complet : {type(e).__name__}: {e}\n\n{traceback.format_exc()}"})

    @app.route("/api/clientlog", methods=["POST"])
    def api_clientlog():
        data = request.get_json(silent=True) or {}
        logger.error(f"[navigateur] {str(data.get('message', ''))[:400]} ({str(data.get('where', ''))[:200]})")
        return jsonify({"ok": True})

    @app.errorhandler(Exception)
    def on_error(exc):
        from werkzeug.exceptions import HTTPException
        if isinstance(exc, HTTPException):
            return exc
        logger.exception(f"Erreur non gérée sur {request.method} {request.path}")
        if request.path.startswith("/api/"):
            return jsonify({"error": f"Erreur interne : {type(exc).__name__}: {exc} (détails dans le Journal)"}), 500
        raise exc
