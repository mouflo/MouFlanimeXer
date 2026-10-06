"""Telegram dans un sujet de groupe : envoi avec message_thread_id et réglages (sans vrai Telegram)."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mouflanimexer as m

TOKEN = "123456789:" + "A" * 35


class SujetTelegram(unittest.TestCase):
    def _envoyer(self, conf):
        with tempfile.TemporaryDirectory() as t:
            chemin = Path(t) / "tg.json"
            chemin.write_text(json.dumps(conf), encoding="utf-8")
            vus = []
            with mock.patch.object(m, "TELEGRAM_CONFIG_PATH", chemin), \
                 mock.patch("urllib.request.urlopen", lambda req, timeout=0: vus.append(json.loads(req.data))):
                m.send_telegram_notification("salut")
            return vus[0]

    def test_sans_sujet_inchange(self):
        corps = self._envoyer({"bot_token": TOKEN, "chat_id": "-1001"})
        self.assertEqual(corps, {"chat_id": "-1001", "text": "salut"})

    def test_avec_sujet(self):
        corps = self._envoyer({"bot_token": TOKEN, "chat_id": "-1001", "thread_id": "9"})
        self.assertEqual(corps["message_thread_id"], 9)

    def test_sujet_invalide_ignore(self):
        corps = self._envoyer({"bot_token": TOKEN, "chat_id": "-1001", "thread_id": "abc"})
        self.assertNotIn("message_thread_id", corps)


class ReglagesSujet(unittest.TestCase):
    def test_enregistrement_et_detection(self):
        import settings_page
        from flask import Flask
        with tempfile.TemporaryDirectory() as t:
            chemin = Path(t) / "tg.json"
            app = Flask(__name__, template_folder=str(Path(m.__file__).parent / "templates"))
            settings_page.init_app(app, lambda: "t", chemin, Path(t) / "sn.json", lambda: [])
            envois = []

            def faux_http(url, headers=None, payload=None, timeout=10):
                if url.endswith("getUpdates"):
                    return 200, json.dumps({"result": [{"message": {"chat": {"type": "supergroup", "id": -1007},
                                                                    "message_thread_id": 5, "is_topic_message": True}}]})
                envois.append(payload)
                return 200, "{}"
            c = app.test_client()
            with mock.patch.object(settings_page, "_http", faux_http):
                r = c.post("/api/settings/telegram", json={"action": "detect", "token": TOKEN}).get_json()
                self.assertEqual((r["chat_id"], r["thread_id"]), ("-1007", "5"))
                r = c.post("/api/settings/telegram", json={"token": TOKEN, "chat_id": "-1007", "thread_id": "5"}).get_json()
                self.assertTrue(r["ok"])
                self.assertEqual(envois[-1]["message_thread_id"], 5)
                self.assertEqual(json.loads(chemin.read_text())["thread_id"], "5")
                self.assertEqual(c.get("/api/settings/telegram").get_json()["thread_id"], "5")
                r = c.post("/api/settings/telegram", json={"thread_id": "x"})
                self.assertEqual(r.status_code, 400)


if __name__ == "__main__":
    unittest.main()


class LienTest(unittest.TestCase):
    def test_lien_de_message(self):
        import settings_page
        self.assertEqual(settings_page.lire_lien("https://t.me/c/1234567890/45/678"), ("-1001234567890", "45"))
        self.assertEqual(settings_page.lire_lien("t.me/c/1234567890/678"), ("-1001234567890", "678"))
        self.assertIsNone(settings_page.lire_lien("https://exemple.fr"))
