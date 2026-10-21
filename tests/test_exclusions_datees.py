import os, sys, tempfile, unittest, time
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mouflanimexer as m


class ExclusionsDatees(unittest.TestCase):
    def setUp(self):
        self.coupure = m.exclusion_cutoff_ts()
        self.avant = self.coupure - 86400
        self.apres = self.coupure + 86400

    def test_toujours_exclue_meme_avec_fichier_recent(self):
        self.assertTrue(m.is_excluded_file("One Piece / S01", self.apres, set(), {"One Piece / S01"}))

    def test_ancienne_liste_protege_les_vieux_fichiers(self):
        self.assertTrue(m.is_excluded_file("Dr Stone / S1", self.avant, {"Dr Stone / S1"}, set()))

    def test_ancienne_liste_ne_protege_pas_un_fichier_recent(self):
        self.assertFalse(m.is_excluded_file("Dr Stone / S1", self.apres, {"Dr Stone / S1"}, set()))

    def test_serie_non_exclue_jamais_ignoree(self):
        self.assertFalse(m.is_excluded_file("Autre / S1", self.avant, {"Dr Stone / S1"}, {"One Piece / S01"}))

    def test_watcher_ne_prend_que_les_fichiers_neufs_des_series_datees(self):
        with tempfile.TemporaryDirectory() as t:
            dossiers = {}
            for serie, vieux in (("Dr Stone", True), ("Dr Stone", False)):
                pass
            def faire(nom, age_apres):
                d = Path(t) / nom / "s1"; d.mkdir(parents=True, exist_ok=True)
                f = d / f"{nom}.S01E01.mkv"; f.write_bytes(b"x")
                ts = self.apres if not age_apres else self.avant
                os.utime(f, (ts, ts)); return f
            vieux = faire("Vieux", True)
            neuf = faire("Neuf", False)
            op_neuf = faire("Perma", False)
            nom = lambda f: m.extract_series_name(f)
            exclues = {nom(vieux), nom(neuf)}
            toujours = {nom(op_neuf)}
            # fichiers « arrivés » il y a longtemps pour passer le délai de stabilité
            m.time_orig = time.time
            try:
                time.time = lambda: self.apres + 10**6
                trouves = m._sonarr_find_stable_new_files([Path(t)], {}, exclues, toujours)
            finally:
                time.time = m.time_orig
            self.assertEqual(sorted(p.name for p in trouves), [neuf.name])


class PageExclusions(unittest.TestCase):
    def test_enregistrer_ajoute_et_retire_en_gardant_les_inconnues(self):
        with tempfile.TemporaryDirectory() as t:
            sauve = (m.EXCLUDED_ALWAYS_PATH, m._series_bases, m.auth.is_logged_in)
            try:
                m.EXCLUDED_ALWAYS_PATH = Path(t) / "toujours.json"
                m.save_excluded_always({"One Piece / S01", "One Piece / S02", "Absente / S1"})
                m._series_bases = lambda force=False: ["One Piece", "Dr Stone", "Bleach"]
                m.auth.is_logged_in = lambda: True
                c = m.app.test_client()
                self.assertIn("One Piece 🔒", c.get("/exclusions").get_data(as_text=True))
                # One Piece décochée, Dr Stone cochée ; « Absente » (pas dans les dossiers) est gardée
                c.post("/exclusions", data={"toujours::Dr Stone": "on"})
                self.assertEqual(m.load_excluded_always(), {"Dr Stone", "Absente / S1"})
                # cocher One Piece protège toutes les saisons
                c.post("/exclusions", data={"toujours::One Piece": "on", "toujours::Dr Stone": "on"})
                self.assertTrue(m.is_excluded_file("One Piece / S99", 10**10, set(), m.load_excluded_always()))
            finally:
                (m.EXCLUDED_ALWAYS_PATH, m._series_bases, m.auth.is_logged_in) = sauve


if __name__ == "__main__":
    unittest.main()
