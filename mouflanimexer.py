#!/usr/bin/env python3
"""
mouflanimexer.py — V3.31
========================
Correctifs intégrés V1 (1.1 à 1.22, cf. historique complet dans le journal
des échanges) :
  - Bug 1 : get_true_orig_res() croise positions (priorité) + tailles de font
  - Bug 2 : détection automatique du style principal de dialogue
  - Bug 3 : Support Specials/OVA/Bonus/Movie comme sous-dossiers (v1.10)
  - Bug 4 : Détection auto sous-titres full/forced par noms de pistes (v1.11)
  - Bug 5 : Résolution None/None → fallback (640, 360) (v1.11, Kaiju No. 8)
  - Bug 6 : Gestion d'erreur extraction sous-titres échouée (v1.11)
  - Bug 7 : Regex _is_forced() accepte "forcer" infinitif (v1.12)
  - Bug 8 : Filtre marges aberrantes > PlayResX/2 (v1.13, Dragon Quest)
  - Bug 9 : Marges mémorisées par série (v1.14, Fairy Tail)
  - Bug 10 : Flous silencieux sans preview (v1.14)
  - Bug 11 : Profils "Vostfr"/"Subforced" (v1.15, Fairy Tail E30+)
  - Bug 12-13 : Ordre filtre marges + tirets typographiques + styles
    partiels (v1.16-1.19, Dragon Quest E62)
  - Bug 14 : Profil "Subforced FR" dans _is_forced() (v1.18)
  - Bug 15 : _profile_for_style() accepte correspondances partielles (v1.19)
  - Bug 16 : Re-classement full/forced par nom, ignore flag mkv (v1.20)
  - Bug 17 : ScaledBorderAndShadow: yes forcé (v1.21, Fairy Tail SDTV)
  - Bug 18-19 : PlayResX=0 rejetée + boucle police bloquante (v1.22, Death Note)

Historique V2.x :
  - v2.0 : Heuristique poids de piste — deux pistes FR au même nom (ex:
    "French"/"French") → la plus lourde = full, la plus légère = forced
    (Next Generations S01E127)
  - v2.1 : Boucle bloquante wait_for_font_upload() + vérification
    find_font_file() après upload — redemande tant que la police n'est
    pas réellement trouvable (Kozuka Mincho Pr6N)
  - v2.2 : Structure miroir : première tentative d'inclure le nom de
    série dans le chemin (remplacée en v2.5, voir plus bas)
  - v2.3 : (1) Nouvelle fonction series_path() pour le dossier ASS —
    anime_name contenant " / " (ex: "Hunter X Hunter / S1") faisait que
    pathlib scindait la chaîne en 2 dossiers avec espaces parasites en
    début/fin de nom, invalides sur le partage SMB/Samba du NAS → noms
    mangled DOS 8.3 (ex: "8ICLR2~W"). (2) read_play_res() distingue
    PlayResX/Y ABSENTS (assume déjà à la résolution cible, pas de
    scaling) de PlayResX/Y présents mais = 0 (fallback 640x360, cas
    Death Note)
  - v2.4 : (1) patch_ass_style() n'insérait jamais PlayResX/PlayResY
    quand ils étaient absents du fichier d'origine (seulement remplacés
    s'ils existaient) → sans ces lignes, les lecteurs retombent sur
    l'ancien défaut SSA (384x288) et les polices calibrées pour 1080p
    deviennent énormes (Boruto/LSCO) → maintenant insérées explicitement
    si absentes. (2) Une piste FR UNIQUE dans tout le fichier, même
    marquée forced_track/nommée "forcée" par erreur du fansub, est
    reclassée automatiquement en "full" (une forcée seule n'a pas de sens)
  - v2.5 : Fix double emboîtement du dossier miroir — v2.2/2.3 ajoutaient
    anime_name (via series_path) DEVANT rel.parent, qui contient déjà la
    structure Série/Saison réelle du dossier scanné → résultat dupliqué
    (.../Miroir/test/Boruto.../S1/Boruto.../S1/...). Le mode miroir
    reproduit maintenant l'arborescence source telle quelle
    (output_dir = mirror_root / rel.parent, sans anime_name) ; la
    correction series_path() reste utilisée uniquement pour le dossier
    ASS (bibliothèque plate sans structure source à copier)
  - v2.6 : find_font_file() ne strippait jamais l'extension du nom de
    police recherché (font_name passé avec ".ttf"/".otf", ex:
    "ArialBold.ttf") avant de le normaliser et de le comparer au stem
    (sans extension) des fichiers trouvés → la clé "arialboldttf" ne
    correspond jamais à "arialbold" → même une police correctement
    uploadée n'était donc JAMAIS reconnue par wait_for_font_upload(),
    qui redemandait indéfiniment puis abandonnait la police en cours
    de traitement (Boruto/NoName, épisode 168 — ArialBold.ttf refusée
    malgré un upload valide). Fix : Path(font_name).stem avant
    normalisation.
  - v2.7 : jusqu'ici, quand une police OBLIGATOIRE (ArialBold,
    TrebuchetMSBold, TrebuchetMSBoldItalic) restait introuvable même
    après la boucle d'upload, le traitement continuait quand même
    ("poursuite sans elle") et produisait un fichier "OK" mais
    visuellement incomplet, sans que ce soit facilement repérable.
    Désormais : le fichier original est déplacé tel quel (non traité)
    vers "/mnt/mouflosyno/MouFlanimexer/A traiter (police manquante)"
    (structure Série/Saison conservée) ; un résumé récapitule tous les
    fichiers zappés à la fin du traitement de toute la file ; une
    notification Telegram groupée est envoyée dans la foulée (config
    via /opt/mouflanimexer/telegram_config.json, hors dépôt git).
  - v2.8 : resolve_ambiguous_subs_by_weight() (heuristique de poids V2.0)
    ne se déclenchait JAMAIS quand les deux pistes FR n'avaient AUCUN nom
    (condition `and name`, un nom vide étant falsy) — précisément le cas
    "aucune indication du tout" qu'elle devait couvrir en priorité
    (fansub NoName). Et même quand elle se déclenchait, elle ne
    renommait que track_name, jamais le flag forced_track du
    conteneur — or _is_forced() vérifie ce flag AVANT le nom, donc un
    mauvais étiquetage du fansub écrasait silencieusement la décision
    par poids. Résultat : classement inversé à chaque fois sur
    Boruto/NoName (piste avec tout le dialogue étiquetée "forced",
    piste vide étiquetée "full"). Fix : nom vide accepté comme "même
    nom", et forced_track réécrit en cohérence avec le poids.
  - v2.9 : le vrai coupable de l'inversion Boruto/NoName persistant après
    v2.8 (les 2 pistes s'appelaient en fait "French"/"French", identiques
    — le fix v2.8 n'était pas en cause) : compare_subtitle_sizes()
    appelait mkvextract avec la syntaxe invalide "tracks=<id>:<sortie>"
    (le "tracks=" collé n'existe pas dans la CLI ; la syntaxe correcte,
    "mkvextract tracks <source> <id>:<sortie>", est déjà utilisée
    ailleurs dans ce fichier). L'extraction échouait donc silencieusement
    à chaque appel, les deux tailles retombaient à 0, et "0 >= 0" étant
    toujours vrai, la piste au plus petit ID gagnait à chaque fois le
    statut "full" — indépendamment de son contenu réel. Fix : syntaxe corrigée +
    exception levée si l'extraction échoue réellement, plutôt que de
    comparer deux tailles nulles et deviner un résultat faux.
  - v3.0 : support des sous-titres PGS (Presentation Graphics Subtitles —
    un sous-titre BITMAP/image, pas du texte, contrairement à ASS/SRT).
    Jusqu'ici ces pistes étaient totalement ignorées par is_ass_or_srt(),
    donc un fichier n'ayant QUE du PGS en FR était remuxé sans aucun
    sous-titre. Prise en charge désormais via OCR : extraction du flux
    PGS brut (.sup) par mkvextract, reconnaissance de texte par l'outil
    pgsrip (qui pilote tesseract) pour produire un .srt, puis réutilise
    exactement le pipeline SRT->ASS existant (même style personnalisé,
    mêmes marges, etc.). Nécessite tesseract-ocr + le paquet Python
    pgsrip installés sur le LXC ; en leur absence, la piste PGS est
    simplement ignorée avec un avertissement clair (aucun crash).
  - v3.1 : fix appel pgsrip — "rip" est une sous-commande obligatoire de
    sa CLI (pgsrip rip -l <lang> <fichier>), pas un simple flag ; l'appel
    initial ("pgsrip --language ...") ne correspondait à aucune commande
    valide.
  - v3.2 : le détail d'un échec OCR (stderr/stdout de pgsrip) est
    désormais remonté dans le log de l'app au lieu d'être avalé
    silencieusement, pour diagnostiquer sans passer par SSH.
  - v3.3 : (Fairy Tail S00E04) pgsrip REFUSE un .sup extrait isolément —
    confirmé en test manuel : "1 file filtered out". Il fait sa propre
    extraction en interne à partir d'un vrai conteneur vidéo (mkv
    complet confirmé fonctionnel). Pour cibler précisément la piste
    choisie (full/forced) sans dépendre de l'interprétation par pgsrip
    des flags MKV, un mini-mkv ne contenant QUE cette piste est
    maintenant construit (mkvmerge --subtitle-tracks) avant d'être passé
    à pgsrip.
  - v3.4 : les fautes de reconnaissance restaient nombreuses même après
    le fix v3.3 (ex: "CES CTEJEIOIS" pour un mot totalement dénaturé).
    pgsrip embarque déjà un nettoyeur post-OCR (cleanit, avec des règles
    groupées par tags : "ocr", "tidy", "no-sdh"...) mais ne les applique
    PAS par défaut. Activation des tags "ocr" et "tidy" (-t ocr -t tidy)
    pour corriger les confusions et artefacts d'OCR les plus courants.
  - v3.5 : support PGS entièrement retiré (is_pgs_codec, convert_pgs_to_srt
    et leurs points de branchement supprimés) — même avec le nettoyage
    post-OCR de v3.4, le taux de fautes de reconnaissance restait trop
    élevé pour un usage sans relecture ligne par ligne, ce que l'usage
    prévu de l'app ne permet pas. Retour au comportement d'avant v3.0 :
    une piste PGS est simplement ignorée (comme n'importe quel codec non
    pris en charge).
  - v3.6 : la piste audio "langue d'origine" (celle mise en 1ère position
    dans l'ordre des pistes et marquée --default-track:yes) était
    toujours calée sur le japonais s'il existait — et sur AUCUNE piste
    sinon. Un fichier n'ayant que de l'audio chinois + français (donghua/
    manhua) se retrouvait donc avec le français en première position ET
    aucune piste par défaut du tout à la lecture. La piste chinoise est
    désormais traitée comme le japonais : "langue d'origine", donc placée
    en premier et marquée par défaut dès qu'il n'y a pas de piste
    japonaise dans le fichier.
  - v3.7 : (Dragon Ball S0E01, fansub Saiyajin Corporation/Aegisub v1.10)
    read_play_res() ne déclarait "PlayResY: 864" SANS AUCUNE ligne
    PlayResX. Ce cas (une seule des deux dimensions présente) était
    confondu avec le bug Death Note (PlayResX/Y explicitement à 0) et
    retombait sur le SD 640x360 par défaut — alors que la convention
    standard ASS/libass/VSFilter déduit la dimension manquante de
    l'autre via un ratio 4:3. Hauteur réelle 864 interprétée comme 360 →
    mise à l'échelle ×3 au lieu de ×1.25 → sous-titres (style "Title",
    fontsize 110) démesurés à l'écran. Fix : PlayResX/Y manquant est
    maintenant calculé depuis l'autre (X = Y×4/3, ou Y = X×3/4) avant de
    retomber sur le SD par défaut si vraiment aucune valeur exploitable.
  - v3.8 : (Dragon Ball S01E07, fansub DragonMax) resolve_ambiguous_subs_by_weight()
    ne couvre que les pistes FR de MÊME nom (ex: "French"/"French") — ici
    les deux pistes ont des noms EXPLICITES ET DIFFÉRENTS ("FR Full" /
    "FR Forced"), avec un flag forced_track cohérent avec ces noms...
    mais le fansub avait inversé les DEUX en même temps : la piste
    appelée et flaguée "FR Forced" contenait en réalité tout le dialogue
    (348 répliques, 30 Ko une fois extraite) et celle appelée et flaguée
    "FR Full" ne contenait que les cartons de titre (14 lignes, 2 Ko).
    Aucune heuristique basée sur le nom ou le flag ne peut détecter ce
    cas puisque le conteneur ment de façon cohérente avec lui-même. Fix :
    nouvelle vérification systématique par poids (_sanity_check_full_forced,
    via mkvextract) appliquée à TOUTE paire full/forcée retenue
    automatiquement (peu importe comment elle a été déterminée — flag,
    mot-clé ou candidat unique), pas seulement aux pistes de même nom.
    Une piste "forcée" ne traduisant par définition que quelques lignes,
    si elle s'avère, une fois extraite, notablement plus lourde (>20%)
    que la piste "full", les deux sont automatiquement interverties (avec
    un message explicite dans le log). Le choix manuel de l'utilisateur
    via l'interface, lui, n'est jamais remis en cause par cette vérification.
  - v3.9 : (Dragon Ball S04E01, encodage Sonarr/DBP) certaines releases
    taguent la piste de sous-titres avec la langue de l'AUDIO plutôt que
    celle du texte lui-même : "Language: Japanese", titre "Sous-titre
    pour Japonais" (comprendre : "le sous-titre qui accompagne la piste
    japonaise" — un texte FRANÇAIS, pas une piste en langue japonaise).
    Ni le filtre LANGS_FRE ni le fallback UNDETERMINED_LANGS existant ne
    couvraient ce cas ("jpn" est une langue parfaitement déterminée), donc
    pick_subtitles_gen() ne trouvait aucune piste FR et le fichier était
    remuxé sans AUCUN sous-titre alors qu'une piste ASS exploitable
    existait bel et bien dans le conteneur. Fix : troisième fallback — si
    le fichier ne contient qu'UNE SEULE piste de sous-titres ASS/SRT au
    total (quelle que soit sa langue déclarée), elle est prise telle
    quelle, faute d'alternative avec laquelle la confondre.
  - v3.10 : (Dragon Ball Kai S02E01+, Mirolo) certaines releases incluent
    la MÊME piste "full" en double dans le conteneur — une fois en SRT,
    une fois en ASS ("French - SRT - KAZE" / "French - ASS - KAZE", 284
    événements chacune), sans aucune piste forcée à côté. Comme les deux
    sont classées "full" (aucune n'est marquée/nommée forcée), le script
    demandait à chaque épisode de choisir laquelle utiliser — et
    redemandait même une piste "forcée" alors qu'aucune n'existe. Un SRT
    est de toute façon systématiquement converti en ASS avant traitement,
    donc quand une piste ASS "full" existe déjà nativement en double d'un
    SRT, elle est maintenant TOUJOURS préférée automatiquement (le SRT
    redondant est simplement écarté) — même logique appliquée côté
    "forcée" si ce doublon s'y présentait un jour.
  - v3.11 : (Sparks of Tomorrow S01E01, NF/BYOR) AUDIO_BAD_KEYWORDS
    contenait "description" mais pas "descriptive" — or Netflix titre ses
    pistes d'audiodescription "Descriptive" / "Descriptive (VO)", pas
    "Description". _matches_any_keyword() exige le mot exact (\\bmot\\b),
    donc cette piste n'était JAMAIS reconnue comme audiodescription et se
    retrouvait en concurrence avec la vraie piste japonaise "VO" —
    demandant systématiquement à l'utilisateur de choisir entre les deux
    alors que l'une des deux n'était pas exploitable. Fix : "descriptive"
    ajouté au mot-clé.
  - v3.12 : premier automatisme complet Sonarr → traitement → bibliothèque
    Emby, sans passer par l'interface web. Nouveau mode CLI
    (`python3 mouflanimexer.py --watch-sonarr`, destiné à cron) qui
    surveille SONARR_WATCH_DIRS (le root folder manga déjà configuré dans
    Sonarr — DÉJÀ le dossier final lu par Emby, pas un tampon séparé) et
    traite automatiquement tout fichier .mkv nouveau et stable depuis au
    moins SONARR_STABLE_SECONDS (pour ne jamais toucher un import Sonarr
    encore en cours d'écriture).

    auto_process_file() fait tourner process_file_gen() de bout en bout
    sans interface, en répondant automatiquement aux décisions à faible
    risque (piste audio ambiguë entre candidats déjà d'égale qualité →
    1ère retenue ; marge personnalisée → conservée telle quelle, comme le
    choix historiquement retenu à la main) et en mettant le fichier de
    côté + notification Telegram dès qu'une décision à fort impact visuel
    serait nécessaire (sous-titre full/forcé ambigu → nouveau dossier
    SONARR_REVIEW_DIR, structure Série/Saison conservée ; police
    obligatoire manquante → réutilise le mécanisme existant PENDING_REVIEW_DIR
    de v2.7), plutôt que de deviner.

    En cas de succès, le fichier produit dans "FICHIER OK" REMPLACE
    l'original EN PLACE (même chemin, même nom, via os.replace()) au lieu
    d'être déposé ailleurs — sûr même avec les hardlinks qBittorrent/Sonarr
    déjà activés chez l'utilisateur : ça ne change que l'entrée de dossier
    du root folder manga, jamais les données seedées séparément depuis le
    dossier de download. Sonarr et Emby continuent de pointer sur le même
    chemin sans rien savoir du remux — aucun appel à l'API Sonarr requis.
    Un petit état JSON (SONARR_STATE_PATH, chemin+mtime des fichiers déjà
    traités) évite de retraiter indéfiniment le même fichier à chaque
    passage de cron. Testé unitairement : détection de stabilité,
    évitement des doublons, et conservation de la structure Série/Saison
    dans le dossier de revue.
  - v3.13 : sans étape préalable, le tout premier passage du watcher
    (état JSON vide) aurait considéré la totalité du catalogue manga déjà
    présent dans le root folder comme "nouveau" et tenté de TOUT retraiter
    d'un coup. Nouvelle commande ponctuelle
    (`python3 mouflanimexer.py --seed-sonarr-state`) à lancer UNE FOIS
    avant d'activer le cron : enregistre le mtime de tous les .mkv déjà
    présents comme "déjà connus", sans y toucher ni les traiter — seuls
    les épisodes qui arrivent APRÈS ce seed initial sont ensuite pris en
    charge par le watcher. Testé unitairement : après seed, plus aucun
    fichier existant n'est détecté comme candidat.
  - v3.14 : le watcher Sonarr ignorait la liste des séries exclues
    (EXCLUDED_SERIES_PATH) que l'interface web permet pourtant déjà de
    décocher par série — une série au style volontairement conservé (ex:
    One Piece) aurait donc quand même été traitée par le watcher
    automatique. _sonarr_find_stable_new_files() filtre désormais aussi
    sur extract_series_name(f) not in load_excluded_series(), la même
    liste partagée avec l'interface web. Trois nouvelles commandes CLI
    pour la gérer sans passer par le bouton "Démarrer" de l'interface
    web : `--list-series` (affiche le nom EXACT de chaque série détectée
    dans SONARR_WATCH_DIRS, y compris son suffixe de saison le cas
    échéant — ex: "One Piece / S01" — et marque celles déjà exclues),
    `--exclude-series "Nom exact"` et `--include-series "Nom exact"`.
    Testé unitairement : après exclusion, la série disparaît des
    candidats du watcher sans toucher à l'autre série présente.
  - v3.15 : le nom de fichier imposé par Sonarr (template incluant
    {MediaInfo AudioLanguages}, ex: "[FR+JA]") ne correspondait plus à
    l'ordre réel des pistes audio une fois le fichier remuxé (ex: devient
    JA+FR en interne) — Sonarr ne le sait pas tant qu'un rescan manuel
    n'est pas fait, obligeant l'utilisateur à rescanner la série à la main
    après chaque épisode. auto_process_file() déclenche désormais, juste
    après le remplacement en place réussi, un appel à l'API Sonarr
    (RescanSeries puis RenameSeries une fois le rescan terminé) pour que
    Sonarr relise le MediaInfo à jour et renomme lui-même le fichier selon
    son propre format — jamais de renommage fait directement par ce script
    (un renommage "à l'insu" de Sonarr lui ferait croire que le fichier a
    disparu, avec risque de re-téléchargement). Best-effort : toute erreur
    réseau/API est journalisée (log_decision) mais ne fait jamais échouer
    le traitement lui-même, qui reste "done" même si le rescan échoue —
    il suffira alors d'un rescan manuel comme avant. Config (URL + clé
    API) volontairement hors du code source, dans un fichier JSON local
    sur le LXC (même principe que la config Telegram, v2.7).
  - v3.16 : les appels POST vers l'API Sonarr (RescanSeries/RenameSeries,
    v3.15) échouaient systématiquement avec "HTTP Error 307: Temporary
    Redirect" — urllib ne suit jamais automatiquement une redirection sur
    une requête POST/PUT (comportement volontaire, pour ne pas rejouer une
    requête non idempotente sans confirmation), or l'instance Sonarr de
    l'utilisateur répond par une redirection 307 même sur ses propres
    endpoints d'API. _sonarr_api_call() suit désormais lui-même cette
    redirection (jusqu'à 3 sauts), en renvoyant la même méthode et le même
    corps vers l'URL indiquée par l'en-tête Location.
  - v3.17 : le renommage Sonarr déclenché automatiquement (v3.15) faisait
    perdre au watcher la trace du fichier — l'état "déjà traité" étant
    indexé par chemin complet, le fichier renommé par Sonarr (ex: [FR+JA]
    → [JA+FR]) n'apparaissait plus dans l'état sous son nouveau nom, et le
    watcher le reprenait pour un fichier neuf au passage suivant (retraité
    inutilement, avec le même risque de collision que celui rencontré sur
    Haikyu si un traitement chevauche l'autre). trigger_sonarr_rescan_and_
    rename() attend désormais la fin réelle du RenameSeries (au lieu de le
    déclencher sans attendre) et retrouve, via l'API, le chemin final exact
    du fichier après renommage ; auto_process_file() et run_sonarr_watch_
    once() enregistrent l'état "déjà traité" sous CE chemin, jamais sous
    l'ancien qui n'existe plus.
  - v3.18 : en mode manuel (interface web) avec "inclure les sous-dossiers"
    coché, sync_mirror_tree() recopiait les fichiers annexes (nfo, jpg...)
    de TOUTES les séries présentes dans le dossier scanné vers le dossier
    miroir, même celles décochées par l'utilisateur pour ce traitement —
    un scan avec 50 séries présentes mais seulement 2 cochées attendait
    quand même que les 48 autres soient parcourues et copiées pour rien.
    sync_mirror_tree() accepte désormais only_top_dirs, calculé dans
    worker_loop() à partir des dossiers de premier niveau qui contiennent
    réellement au moins un fichier dans STATE["queue"] (donc une série
    cochée) — les autres ne sont plus touchés du tout.
  - v3.19 : exception par série pour CONSERVER une ou plusieurs pistes de
    sous-titres d'une autre langue que le français (ex: anime avec FR ET
    coréen, où les deux doivent être gardés) — jusqu'ici, toute piste non
    FR était systématiquement supprimée (-S sur la source), seule la
    piste FR traitée (extraite/convertie en ASS) était réinjectée.
    Nouveau fichier de config partagé EXTRA_SUB_LANG_PATH (même principe
    qu'EXCLUDED_SERIES_PATH), géré via `--add-extra-sub-lang "Nom exact"
    <code_langue>` / `--remove-extra-sub-lang "Nom exact" <code_langue>`
    (ex: kor, eng...) et consultable avec `--list-series-in "/chemin"`
    pour retrouver le nom exact d'une série en dehors de SONARR_WATCH_
    DIRS. process_file_gen() sélectionne alors ces pistes via -s <ids>
    (passthrough intact depuis la source, jamais converties) au lieu du
    -S habituel qui les aurait sinon supprimées, et les place en dernier
    dans l'ordre des pistes, toujours non-défaut/non-forcées (le FR reste
    la piste par défaut). Testé unitairement (ajout/retrait/relecture de
    la config).
  - v3.20 : le passthrough brut (-s) du v3.19 ne suffisait pas pour le cas
    réel de l'utilisateur — sa piste coréenne contient en fait DEUX
    langues dans le même fichier ASS (FR en \\an8 en haut ajouté à la
    main, coréen en bas), donc elle a besoin du MÊME traitement que la
    piste FR normale (lecture de sa propre résolution/marges d'origine,
    patch de style, polices), pas d'une simple copie brute. Les pistes de
    extra_sub_tracks passent désormais par la même boucle d'extraction/
    patch que "full"/"forced" (label "extra::<code_langue>"), puis sont
    réinjectées comme fichiers ASS externes traités (comme le FR), tout
    en gardant la source blindée par -S comme avant. Nom affiché traduit
    pour les langues courantes (LANGUAGE_DISPLAY_NAMES), sinon code brut
    en majuscules. Ajout aussi d'un champ texte directement dans
    l'interface web (par série, à côté de la case à cocher), pour activer
    cette exception sans passer par SSH/CLI — utile en déplacement.
  - v3.21 : bug introduit par le v3.20 — la boucle de traitement partagée
    applique patch_ass_style() à TOUTES les pistes, y compris les pistes
    "extra::<lang>" (ex: coréen). Or _profile_for_style() matche par
    sous-chaîne : un nom de style non-FR comme "Default -kor" contient
    "default" et matchait donc le profil FR "dialogue", ce qui écrasait
    SA police d'origine par "Trebuchet MS" (police FR par défaut, sans
    aucun glyphe coréen) — carrés/tofu au visionnage sur Android, même si
    l'utilisateur corrigeait la police dans son propre fichier source.
    patch_ass_style() reçoit maintenant un paramètre apply_style_profiles
    (False pour les pistes "extra::<lang>") qui désactive complètement la
    réécriture cosmétique STYLE_PROFILES pour ces pistes — seule la mise à
    l'échelle de résolution reste appliquée, la police/couleurs d'origine
    sont intégralement préservées. Ajout de detect_style_fonts() (scanne
    la colonne Fontname des lignes Style, pas seulement les \\fn en ligne)
    pour que la police déclarée par une piste "extra::<lang>" soit bien
    vérifiée/embarquée comme les autres polices requises.
  - v3.22 : la v3.21 préservait la police d'origine d'une piste
    "extra::<lang>" (ex: coréen), mais ça ne suffit pas si CETTE police
    elle-même ne contient pas les glyphes du bon alphabet (ex: "Trebuchet
    MS" n'a aucun caractère coréen) — et comme le fichier existe bien dans
    la bibliothèque de polices, aucune alerte "police manquante" n'était
    déclenchée : toujours des carrés/tofu à l'affichage, cette fois sans
    même être détecté. Ajout de force_style_fontname() + constante
    EXTRA_SUB_UNIVERSAL_FONT ("Arial Unicode MS", couverture quasi
    universelle : latin, coréen, japonais, cyrillique...) : toute piste
    "extra::<lang>" se voit désormais systématiquement forcée vers cette
    police, sans jamais toucher aux pistes "full"/"forced" FR — plus
    besoin de corriger le .ass source à chaque fois, fonctionne aussi pour
    toute future piste supplémentaire (anglais, japonais...).
  - v3.23 : l'exception "sous-titre supplémentaire" (extra_sub_lang.json,
    v3.19/v3.20) était jusqu'ici appliquée indifféremment en manuel ET en
    automatique (watcher Sonarr), car process_file_gen() est partagée par
    les deux — un besoin ponctuel (un épisode précis) se serait donc
    appliqué à toute future sortie automatique de la série. Nouveau
    paramètre process_file_gen(..., apply_extra_sub_lang=True/False) :
    auto_process_file() (watcher) passe désormais explicitement False — le
    watcher automatique applique systématiquement le traitement de base
    (FR) uniquement, l'exception reste réservée au traitement manuel
    depuis l'interface web.
  - v3.24 : après un traitement MANUEL, l'utilisateur remplace lui-même le
    fichier d'origine par le résultat une fois vérifié visuellement — le
    watcher Sonarr automatique ne le sait pas (SONARR_STATE_PATH n'est
    mis à jour que par le watcher lui-même) et voit un fichier dont le
    mtime a changé : il le reprenait pour un fichier NEUF au prochain
    passage de cron, et le retraitait en base FR uniquement (depuis
    v3.23), écrasant un traitement manuel spécifique (ex: piste coréenne
    conservée). Ajout d'un marqueur invisible (petit fichier texte attaché
    au .mkv comme une police, MOUFLANIMEXER_MARKER_NAME) posé sur TOUT
    fichier produit — manuel ET automatique. is_already_processed()
    vérifie ce marqueur ; _sonarr_find_stable_new_files() s'en sert pour
    ne jamais retraiter un fichier déjà passé par le script, peu importe
    qui l'a remis en place ni quand.
  - v3.25 : notification Telegram individuelle (avec emojis) pour chaque
    fichier traité par le watcher Sonarr automatique — avant, un succès
    total ne déclenchait AUCUNE notification (résumé groupé envoyé
    seulement s'il y avait au moins une révision/erreur à signaler), donc
    impossible de suivre le traitement au fil de l'eau. notify_sonarr_
    result() construit un message par fichier : nom de série + SxxEyy
    extrait du nom de fichier + ✅/⚠️/❌ selon succès, mise de côté ou
    erreur.
  - v3.26 : (Smoking Behind the Supermarket with You) la v3.22 forçait la
    police universelle (Arial Unicode MS) sur TOUS les styles d'une piste
    "extra::<lang>", y compris les styles utilisés par le FR ajouté en
    \\an8 par-dessus le coréen par l'utilisateur ("Default", "Sign",
    "Italique") — ces lignes FR perdaient donc leur style habituel
    (Trebuchet MS/Arial, tailles/marges calibrées). Nouvelle fonction
    detect_extra_lang_styles() : repère par le CONTENU réel des lignes
    (plages Unicode de l'alphabet de la langue, ex: Hangul pour le
    coréen) quel(s) style(s) appartiennent VRAIMENT à la langue
    supplémentaire, plutôt que de se fier au nom du style (source du bug
    v3.21 : "Default -kor" matchait "default" par sous-chaîne). patch_
    ass_style(skip_profile_styles=...) et force_style_fontname(only_
    styles=...) n'excluent désormais plus que CES styles précis — tous
    les autres styles du même fichier (le FR ajouté par-dessus) reçoivent
    à nouveau le style FR normal.
  - v3.27 : sync_mirror_tree() (copie des nfo/jpg annexes en mode miroir,
    v3.18) n'a JAMAIS filtré les dossiers système (cache de miniatures
    Synology @eaDir, etc.), contrairement au scan manuel (/scan) qui le
    fait depuis longtemps — un seul dossier de série peut accumuler des
    dizaines de milliers de miniatures @eaDir au fil du temps, toutes
    recopiées pour rien dans le miroir même quand only_top_dirs restreint
    correctement à la seule série sélectionnée (ce qui donnait l'impression
    que "tout" était recopié). Nouvelle constante partagée
    SYSTEM_DIRS_EXCLUDED (même liste que /scan), appliquée aussi dans
    sync_mirror_tree(). Testé unitairement : un dossier @eaDir avec un
    fichier annexe réel (poster.jpg, tvshow.nfo) à côté → seuls les 2
    fichiers réels sont copiés, le cache @eaDir est ignoré, et une autre
    série non sélectionnée n'est pas touchée.
  - v3.28 : (Smoking Behind the Supermarket with You S01E07) la v3.26
    suppose qu'une piste bilingue donne à la langue supplémentaire un
    style ENTIÈREMENT dédié (ex: "Default -kor") — mais certains épisodes
    réutilisent le MÊME style à la fois pour le FR ajouté en \an8 ET pour
    la langue d'origine, sans \fn par ligne (observé : "Default" utilisé
    par 624 lignes, dont 337 en coréen et 287 en français ; le style
    "Default -kor", lui, existait mais n'était utilisé par AUCUNE ligne).
    v3.26 classait alors "Default" comme "le style coréen" et lui
    retirait le style FR habituel — cassant l'affichage des 287 lignes FR
    qui partagent ce même style. detect_extra_lang_style_usage() distingue
    désormais un style "pur" (100% dans l'alphabet voulu, comportement
    v3.26 inchangé) d'un style "mixte" (partagé) : un style mixte GARDE
    son style FR habituel (STYLE_PROFILES), et seules les lignes
    contenant réellement l'alphabet voulu reçoivent la police universelle
    EN LIGNE ({\fnArial Unicode MS}, nouvelle fonction
    force_inline_font_for_script_lines()), sans toucher au Style. Testé
    sur les deux fichiers réels de l'utilisateur (S01E12 : style pur,
    comportement inchangé ; S01E07 : style mixte, nouveau comportement).
  - v3.31 : connexion sécurisée (auth.py). Le mot de passe en clair et la
    clé de session d'exemple qui étaient écrits dans ce fichier sont supprimés:
    identifiant + HASH du mot de passe dans /opt/mouflanimexer/login.json
    (hors GitHub, chmod 600, défini par `bash set-login.sh`), clé de session
    aléatoire générée sur le serveur, blocage 10 min après 5 essais ratés,
    cookie "Secure" derrière HTTPS, toutes les routes protégées (pas
    seulement celles décorées), changement de mot de passe = toutes les
    sessions déconnectées. Page de connexion classique (formulaire HTML),
    compatible avec Bitwarden.
  - v3.30 : nouvelle page « Diagnostic » (/diagnostic, lien 🩺 en haut de la
    page) : un rapport complet à copier-coller d'un clic — version, mémoire,
    disque, outils (mkvmerge/mkvextract/ffprobe), état des dossiers
    (médiathèque, polices, surveillance Sonarr), état du traitement,
    journal de la page, décisions récentes (.jsonl), journal de déploiement
    et journal système du service (erreurs Python comprises) — sans avoir à
    se connecter au serveur. Mots de passe, jetons Telegram et clés d'API
    masqués automatiquement.
  - v3.29 : crash complet et silencieux du watcher Sonarr (traceback dans
    sonarr_watch.log, AUCUNE notification Telegram — même pas celle
    d'erreur, puisque le crash avait lieu AVANT la boucle try/except par
    fichier) — FileNotFoundError levée par le générateur interne de
    Path.rglob("*.mkv") quand un dossier disparaît EN COURS DE SCAN (ex:
    Sonarr renomme/déplace "Smoking Behind the Supermarket with You"
    pendant que le watcher le parcourt). Nouvelle fonction résiliente
    _iter_mkv_files() (os.walk avec onerror qui avale l'erreur et continue
    les dossiers suivants) remplace les 3 usages de rglob("*.mkv") pour la
    découverte de fichiers du watcher. Ajout aussi d'un filet de sécurité
    au niveau de l'entrée --watch-sonarr : toute exception non prévue qui
    remonterait malgré tout envoie désormais une notification Telegram
    avant de laisser planter le process (comportement cron inchangé par
    ailleurs). Testé unitairement : dossier qui disparaît pendant le scan
    (scandir qui lève FileNotFoundError) → les autres séries sont quand
    même trouvées.
"""

import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import threading
from pathlib import Path
from urllib.parse import quote as _urlquote

from flask import Flask, request, redirect, url_for, render_template_string, session, send_from_directory, Response
from functools import wraps

app = Flask(__name__)

import diag
diag.setup_logging()   # journal : console + data/mouflanimexer.log
logger = diag.logger


class _LoggedList(list):
    """Le journal affiché dans la page est aussi écrit dans le fichier de journal (rien ne se perd à l'actualisation)."""

    def append(self, item):
        super().append(item)
        try:
            text = item.get("text", "") if isinstance(item, dict) else str(item)
            if text.strip():
                (logger.warning if isinstance(item, dict) and item.get("alert") else logger.info)(text)
        except Exception:
            pass

import auth
auth.init_app(app)  # page de connexion + protection de toutes les routes (v3.31)


TARGET_PLAYRES = (1920, 1080)

STYLE_PROFILES = {
    "dialogue": {
        "match": {"Default", "Dialogue", "Italique", "TiretsDefault", "TiretsItalique"},
        "italic_match": {"Italique", "TiretsItalique"},
        "fontname": "Trebuchet MS", "fontsize": "66",
        "primary_colour": "&H00FFFFFF", "secondary_colour": "&H000000FF",
        "outline_colour": "&H00000000", "back_colour": "&H00000000",
        "bold": "-1", "underline": "0", "strikeout": "0",
        "scale_x": "100", "scale_y": "100", "spacing": "0", "angle": "0",
        "border_style": "1", "outline": "3", "shadow": "3", "alignment": "2",
        "margin_l": "150", "margin_r": "150", "margin_v": "45", "encoding": "1",
    },
    "sign": {
        "match": {"Sign"},
        "italic_match": set(),
        "fontname": "Arial", "fontsize": "63",
        "primary_colour": "&H00FFFFFF", "secondary_colour": "&H000000FF",
        "outline_colour": "&H00292929", "back_colour": "&H00000000",
        "bold": "-1", "underline": "0", "strikeout": "0",
        "scale_x": "100", "scale_y": "100", "spacing": "0", "angle": "0",
        "border_style": "1", "outline": "3", "shadow": "0", "alignment": "8",
        "margin_l": "120", "margin_r": "120", "margin_v": "90", "encoding": "1",
    },
}

LANGS_JPN = {"jpn", "ja"}
LANGS_FRE = {"fre", "fra", "fr"}
LANGS_CHI = {"chi", "zho", "zh", "cmn"}  # chinois (mandarin, etc.)
UNDETERMINED_LANGS = {None, "", "und", "undetermined", "mis", "zxx"}
# v3.32 : dossiers réglables depuis la page ⚙️ Réglages (data/paths.json, hors GitHub).
# Sans réglage : les chemins habituels. Le surveillant Sonarr (cron) relit le même fichier.
PATHS_FILE = Path(__file__).resolve().parent / "data" / "paths.json"
DEFAULT_WORK_ROOT = "/mnt/mouflosyno/MouFlanimexer"
DEFAULT_WATCH_DIRS = ["/mnt/mouflosyno/Emby-Media/Manga"]


def load_paths_config():
    try:
        data = json.loads(PATHS_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


_PATHS = load_paths_config()
WORK_ROOT = Path(_PATHS.get("work_root") or DEFAULT_WORK_ROOT)          # dossier de travail : sorties, journal, « À traiter »…
DEFAULT_FOLDER = str(_PATHS.get("scan_default") or WORK_ROOT)            # dossier proposé au scan
OK_DIR = WORK_ROOT / "FICHIER OK"                                        # fichiers terminés (mode scan sans miroir)
ASS_DIR = WORK_ROOT / "ASS"                                              # sous-titres d'origine conservés
AUTO_OUT_DIR = WORK_ROOT / ".en-cours-auto"                              # sorties du surveillant Sonarr, avant remplacement de l'original
PORT = 5000
BASE_VERSION = "3.33"  # Sous-titres : \\iclip, découpes et dessins vectoriels, bordures/ombres X/Y, espacement et vieux format SSA mis à l'échelle


def _get_version():
    try:
        count = subprocess.check_output(["git", "rev-list", "--count", "HEAD"], cwd=Path(__file__).resolve().parent, text=True, stderr=subprocess.DEVNULL).strip()
        short = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=Path(__file__).resolve().parent, text=True, stderr=subprocess.DEVNULL).strip()
        return f"{BASE_VERSION}.{count} ({short})"
    except Exception:
        return BASE_VERSION


APP_VERSION = _get_version()   # ex. 3.31.12 (a1b2c3d) : comme MouFloster et MouFlopening

LOG_PATH = WORK_ROOT / "Log" / ".MouFlanimexer_log.jsonl"     # dossier créé au premier écrit (pas au démarrage : NAS peut-être absent)

EXCLUDED_SERIES_PATH = Path("/opt/mouflanimexer/excluded_series.json")

# v3.19/v3.20 : exception par série pour CONSERVER une ou plusieurs
# pistes de sous-titres supplémentaires (langue autre que le français),
# traitées (extraction/patch de style) comme la piste FR puis réinjectées
# à part, en plus de la piste FR normale (full/forced) — ex: un anime
# avec des sous-titres FR ET coréen, où les deux doivent être gardés.
# Clé = nom exact tel que renvoyé par extract_series_name() (même
# convention que EXCLUDED_SERIES_PATH, y compris le suffixe de saison le
# cas échéant), valeur = liste de codes langue ISO 639-2 (ex: ["kor"]).
# Modifiable aussi directement depuis l'interface web (v3.20).
EXTRA_SUB_LANG_PATH = Path("/opt/mouflanimexer/extra_sub_lang.json")

# Bibliothèque locale de polices : toute police inconnue trouvée dans un
# fichier y est copiée automatiquement, pour être réutilisable ensuite.
REFERENCE_FONTS_DIR = Path("/opt/mouflanimexer/fonts")
REFERENCE_FONTS_DIR.mkdir(parents=True, exist_ok=True)

# v3.22 : police de repli forcée pour les pistes "extra::<lang>" (ex:
# coréen). Problème réel : même quand la police déclarée dans le .ass
# d'origine EXISTE dans la bibliothèque (donc aucune alerte "police
# manquante"), elle peut tout simplement ne pas contenir les glyphes du
# bon alphabet (ex: "Trebuchet MS" n'a aucun caractère coréen) → carrés/
# tofu à l'affichage, sans que le script ne détecte rien d'anormal.
# "Arial Unicode MS" couvre quasiment tous les alphabets (latin, coréen,
# japonais, cyrillique...), donc on l'impose systématiquement sur CES
# pistes uniquement (jamais sur "full"/"forced" FR), sans que l'utilisateur
# ait à corriger son fichier .ass source à chaque fois.
EXTRA_SUB_UNIVERSAL_FONT = "Arial Unicode MS"

# v3.24 : marqueur invisible (petit fichier texte attaché au .mkv, comme
# une police) posé sur TOUT fichier traité par mouflanimexer — manuel ET
# automatique. Sert à reconnaître un fichier déjà traité même quand il a
# été remplacé "à la main" par l'utilisateur (le watcher Sonarr se fie
# normalement au mtime enregistré dans SONARR_STATE_PATH, mais un
# remplacement manuel change le mtime sans que ce fichier d'état ne le
# sache -> le watcher le reprendrait pour un fichier neuf et écraserait un
# traitement manuel spécifique, ex: piste coréenne conservée). Avec ce
# marqueur, le watcher regarde le fichier lui-même plutôt que seulement le
# mtime, et ne retraite jamais un fichier déjà passé par le script.
MOUFLANIMEXER_MARKER_NAME = "mouflanimexer_processed.marker"

# Racine des copies "miroir" : reproduit toute l'arborescence d'un dossier
# scanné (nfo, images, sous-dossiers de saison...) sans jamais toucher au
# dossier d'origine ; seuls les .mkv/.mp4 sont remplacés par la version traitée.
MIRROR_ROOT_BASE = WORK_ROOT / "Miroir"

# Dossier où sont déplacés (sans être traités) les fichiers pour lesquels
# une police OBLIGATOIRE (Arial Bold, Trebuchet MS Bold/BoldItalic) reste
# introuvable même après la boucle d'upload — pour éviter de produire un
# fichier "OK" avec une police manquante, silencieusement (v2.7).
PENDING_REVIEW_DIR = WORK_ROOT / "A traiter (police manquante)"

# V3.12 : automatisme Sonarr → traitement automatique → bibliothèque Emby.
# Dossier(s) root folder Sonarr à surveiller pour les nouveaux épisodes
# manga importés (déjà organisés Série/Saison, déjà lus par Emby). Un
# fichier traité avec succès remplace l'original EN PLACE (même chemin,
# même nom) — Sonarr et Emby continuent de pointer dessus sans rien savoir
# du remux. Les cas nécessitant une décision humaine (sous-titre full/forcé
# ambigu, police obligatoire introuvable) sont mis de côté ici plutôt que
# de deviner, avec notification Telegram.
SONARR_WATCH_DIRS = [Path(p) for p in (_PATHS["sonarr_watch_dirs"] if "sonarr_watch_dirs" in _PATHS else DEFAULT_WATCH_DIRS)]   # liste vide = surveillance désactivée
SONARR_REVIEW_DIR = WORK_ROOT / "A traiter (intervention manuelle)"
SONARR_STATE_PATH = Path("/opt/mouflanimexer/sonarr_watch_state.json")
# Un fichier doit être stable (non modifié) depuis au moins ce délai avant
# d'être traité, pour ne jamais toucher un import Sonarr encore en cours.
SONARR_STABLE_SECONDS = 120

# Configuration Telegram (token + chat_id) : volontairement PAS dans le code
# source (jamais commit sur GitHub), lue depuis un petit fichier JSON local
# sur le LXC. Absent ou invalide → notifications simplement désactivées.
TELEGRAM_CONFIG_PATH = Path("/opt/mouflanimexer/telegram_config.json")


def load_telegram_config():
    """Retourne (bot_token, chat_id) ou (None, None) si le fichier de
    config est absent/invalide."""
    try:
        data = json.loads(TELEGRAM_CONFIG_PATH.read_text(encoding="utf-8"))
        token = data.get("bot_token")
        chat_id = data.get("chat_id")
        if token and chat_id:
            return token, chat_id
    except Exception:
        pass
    return None, None


# Configuration API Sonarr (URL + clé API) : volontairement PAS dans le
# code source (jamais commit sur GitHub), lue depuis un petit fichier JSON
# local sur le LXC, même principe que la config Telegram ci-dessus.
# Utilisée uniquement pour déclencher un rescan + renommage automatique
# après traitement (v3.15) — absente/invalide → simplement désactivé,
# il suffit alors de rescanner à la main comme avant.
SONARR_API_CONFIG_PATH = Path("/opt/mouflanimexer/sonarr_api_config.json")


def load_sonarr_api_config():
    """Retourne (base_url, api_key) ou (None, None) si le fichier de
    config est absent/invalide. base_url est retournée sans slash final."""
    try:
        data = json.loads(SONARR_API_CONFIG_PATH.read_text(encoding="utf-8"))
        base_url = (data.get("base_url") or "").rstrip("/")
        api_key = data.get("api_key")
        if base_url and api_key:
            return base_url, api_key
    except Exception:
        pass
    return None, None


def _sonarr_api_call(method, path, api_key, base_url, payload=None, timeout=20, _redirects_left=3):
    """Petit client HTTP minimal (urllib, pas de dépendance externe) pour
    l'API Sonarr v3. Lève une exception en cas d'échec (laissée à
    l'appelant, qui doit rester best-effort).

    v3.15.1 : urllib ne suit JAMAIS automatiquement une redirection HTTP
    (301/302/307/308) sur un POST/PUT — volontaire côté librairie, pour ne
    pas rejouer une requête non idempotente sans confirmation. Or Sonarr
    répond justement par une redirection 307 (ex: instance derrière un
    reverse proxy, ou http→https) même sur ses propres endpoints d'API.
    On suit donc la redirection nous-mêmes, manuellement, en renvoyant la
    même méthode et le même corps vers l'URL indiquée par 'Location'."""
    import urllib.request as _urllib_request
    import urllib.error as _urllib_error
    url = f"{base_url}{path}" if path.startswith("/") else f"{base_url}/{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = _urllib_request.Request(url, data=data, method=method)
    req.add_header("X-Api-Key", api_key)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with _urllib_request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return json.loads(body) if body else None
    except _urllib_error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308) and _redirects_left > 0:
            location = e.headers.get("Location")
            if location:
                # Location peut être relative (rare) ou absolue.
                if location.startswith("/"):
                    # Repart de la racine (scheme+host) de base_url.
                    from urllib.parse import urlsplit as _urlsplit
                    parts = _urlsplit(base_url)
                    new_base = f"{parts.scheme}://{parts.netloc}"
                    return _sonarr_api_call(method, location, api_key, new_base, payload, timeout, _redirects_left - 1)
                else:
                    from urllib.parse import urlsplit as _urlsplit
                    parts = _urlsplit(location)
                    new_base = f"{parts.scheme}://{parts.netloc}"
                    new_path = location[len(new_base):] or "/"
                    return _sonarr_api_call(method, new_path, api_key, new_base, payload, timeout, _redirects_left - 1)
        raise


def _sonarr_find_series_id(file_path: Path, base_url, api_key):
    """Retrouve l'ID Sonarr de la série dont le dossier racine contient
    file_path, en comparant les chemins (pas de dépendance à un nom
    exact). Retourne None si aucune correspondance."""
    series_list = _sonarr_api_call("GET", "/api/v3/series", api_key, base_url)
    if not series_list:
        return None
    file_str = str(file_path)
    best_match = None
    best_len = -1
    for series in series_list:
        series_path = series.get("path")
        if not series_path:
            continue
        # Le fichier doit être DANS ce dossier série (avec séparateur, pour
        # éviter qu'un dossier "One Piece" matche "One Piece 2").
        prefix = series_path.rstrip("/") + "/"
        if file_str.startswith(prefix) and len(prefix) > best_len:
            best_match = series.get("id")
            best_len = len(prefix)
    return best_match


def _sonarr_wait_command(command_id, base_url, api_key, max_wait=90, poll_every=3):
    """Attend qu'une commande Sonarr (rescan...) passe à l'état 'completed'
    avant de continuer, pour être sûr que le rescan a bien fini avant de
    déclencher le renommage. Abandonne silencieusement après max_wait
    secondes (le renommage sera simplement tenté quand même)."""
    waited = 0
    while waited < max_wait:
        try:
            status = _sonarr_api_call("GET", f"/api/v3/command/{command_id}", api_key, base_url)
        except Exception:
            return
        if status and status.get("status") in ("completed", "failed"):
            return
        time.sleep(poll_every)
        waited += poll_every


def _sonarr_find_episode_file_id(series_id, file_path: Path, base_url, api_key):
    """Retrouve l'ID Sonarr du fichier-épisode dont le chemin correspond
    exactement à file_path, parmi tous les fichiers de la série. Retourne
    None si aucune correspondance (ex: chemin déjà changé entre-temps)."""
    files = _sonarr_api_call("GET", f"/api/v3/episodefile?seriesId={series_id}", api_key, base_url)
    if not files:
        return None
    target = os.path.normpath(str(file_path))
    for item in files:
        item_path = item.get("path")
        if item_path and os.path.normpath(item_path) == target:
            return item.get("id")
    return None


def _sonarr_get_episode_file_path(episode_file_id, base_url, api_key):
    """Relit le fichier-épisode par son ID pour récupérer son chemin
    ACTUEL (potentiellement différent après un RenameSeries). Retourne
    None si introuvable/erreur."""
    try:
        item = _sonarr_api_call("GET", f"/api/v3/episodefile/{episode_file_id}", api_key, base_url)
        p = item.get("path") if item else None
        return Path(p) if p else None
    except Exception:
        return None


def trigger_sonarr_rescan_and_rename(file_path: Path):
    """(v3.15/v3.17) Best-effort : après un remplacement en place réussi,
    dit à Sonarr de relire le MediaInfo du fichier (RescanSeries) puis de
    le renommer selon son propre format (RenameSeries) — jamais fait
    directement par ce script (voir historique en tête de fichier).

    Retourne le chemin FINAL du fichier après renommage (Path), ou None si
    le renommage n'a pas pu être suivi (API absente, erreur réseau, série
    introuvable...) — dans ce cas l'appelant doit garder file_path comme
    référence, au risque que le watcher reprenne le fichier si Sonarr le
    renomme quand même de son côté sans qu'on ait pu le tracer (v3.17 :
    c'est justement pour éviter ça qu'on va maintenant jusqu'au bout et
    qu'on ATTEND la fin du RenameSeries, au lieu de le déclencher sans
    attendre comme en v3.15 — sinon l'état interne du watcher continuait
    de pointer vers l'ancien chemin, qui n'existe plus après renommage,
    et le fichier renommé était pris pour un fichier neuf et retraité)."""
    base_url, api_key = load_sonarr_api_config()
    if not base_url or not api_key:
        return None
    try:
        series_id = _sonarr_find_series_id(file_path, base_url, api_key)
        if series_id is None:
            log_decision(file_path, "sonarr_api_skip", message="Série introuvable via l'API Sonarr (chemin non reconnu).")
            return None

        episode_file_id = _sonarr_find_episode_file_id(series_id, file_path, base_url, api_key)

        rescan = _sonarr_api_call(
            "POST", "/api/v3/command", api_key, base_url,
            payload={"name": "RescanSeries", "seriesId": series_id},
        )
        rescan_id = rescan.get("id") if rescan else None
        if rescan_id is not None:
            _sonarr_wait_command(rescan_id, base_url, api_key)

        if episode_file_id is None:
            # Le rescan a pu changer les IDs (rare, mais possible s'il a
            # ré-importé le fichier) — on retente après coup.
            episode_file_id = _sonarr_find_episode_file_id(series_id, file_path, base_url, api_key)

        rename = _sonarr_api_call(
            "POST", "/api/v3/command", api_key, base_url,
            payload={"name": "RenameSeries", "seriesIds": [series_id]},
        )
        rename_id = rename.get("id") if rename else None
        if rename_id is not None:
            _sonarr_wait_command(rename_id, base_url, api_key)

        new_path = None
        if episode_file_id is not None:
            new_path = _sonarr_get_episode_file_path(episode_file_id, base_url, api_key)

        if new_path and new_path != file_path:
            log_decision(file_path, "sonarr_api_rescan_rename", message=f"Rescan + renommage Sonarr OK — nouveau nom : {new_path.name}")
        else:
            log_decision(file_path, "sonarr_api_rescan_rename", message=f"Rescan + renommage Sonarr déclenchés (seriesId={series_id}), nom inchangé ou non confirmé.")
        return new_path
    except Exception as e:
        log_decision(file_path, "sonarr_api_error", message=f"Échec appel API Sonarr (non bloquant) : {e}")
        return None


def send_telegram_notification(message):
    """Envoie un message texte via l'API Bot Telegram. Best-effort : toute
    erreur (réseau, config absente...) est avalée silencieusement pour ne
    jamais faire planter le traitement à cause d'une notif."""
    token, chat_id = load_telegram_config()
    if not token or not chat_id:
        return
    try:
        import urllib.request as _urllib_request
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": message}).encode("utf-8")
        req = _urllib_request.Request(
            url, data=payload, headers={"Content-Type": "application/json"}
        )
        _urllib_request.urlopen(req, timeout=10)
    except Exception:
        pass


# v3.25 : notification Telegram "jolie" par fichier traité automatiquement
# (watcher Sonarr) — nom de série + SxxEyy extraits du nom de fichier.
_EPISODE_TAG_RE = re.compile(r"[Ss](\d{1,2})[Ee](\d{1,4})")


def _format_episode_tag(path):
    """Retourne "S01E12" si repérable dans le nom de fichier, sinon None
    (ex: Specials/OVA sans numérotation SxxEyy standard)."""
    m = _EPISODE_TAG_RE.search(path.stem)
    if not m:
        return None
    return f"S{int(m.group(1)):02d}E{int(m.group(2)):02d}"


def _series_display_name(path):
    """extract_series_name() renvoie parfois "Nom / S01" (sous-dossier de
    saison) — on ne garde que "Nom" ici, le SxxEyy du nom de fichier suffit
    à afficher l'épisode précis."""
    return extract_series_name(path).split(" / ")[0].strip()


def notify_sonarr_result(path, status, message):
    """v3.25 : notification Telegram envoyée pour CHAQUE fichier traité
    automatiquement par le watcher Sonarr (succès, mis de côté, ou erreur)
    — remplace l'ancien résumé groupé en fin de passage de cron, qui restait
    silencieux en cas de succès total et ne permettait donc pas de suivre
    le traitement au fil de l'eau."""
    series = _series_display_name(path)
    ep_tag = _format_episode_tag(path) or path.stem

    if status == "done":
        emoji, title = "✅", "Traité automatiquement avec succès"
    elif status == "review":
        emoji, title = "⚠️", "Mis de côté — vérification manuelle nécessaire"
    else:
        emoji, title = "❌", "Échec du traitement"

    lines = [f"{emoji} MouFlanimeXer — {series}", f"🎬 {ep_tag} — {title}"]
    if message:
        lines.append(f"💬 {message}")
    send_telegram_notification("\n".join(lines))


def sync_mirror_tree(scan_root: Path, mirror_root: Path, log_cb, only_top_dirs=None):
    """Copie tout ce qui n'est pas une vidéo (.mkv/.mp4) depuis scan_root
    vers mirror_root, en reproduisant l'arborescence des sous-dossiers.
    Ne touche jamais scan_root. Les vidéos sont gérées séparément (remux).

    v3.18 : only_top_dirs (optionnel) restreint la copie aux dossiers de
    PREMIER NIVEAU listés (ex: {"One Piece", "Dragon Ball"}) — avant ce
    correctif, en mode "inclure les sous-dossiers", cette fonction
    recopiait les nfo/jpg/etc. de TOUTES les séries présentes dans le
    dossier scanné, même celles décochées par l'utilisateur pour ce
    traitement (ex: scanner 50 séries, n'en cocher que 2, mais attendre
    quand même que les 48 autres soient parcourues pour rien). None
    (défaut) garde l'ancien comportement (tout copier), pour compatibilité
    avec tout appelant qui n'aurait pas encore cette info."""
    video_exts = {".mkv", ".mp4"}
    count = 0
    if only_top_dirs is not None:
        roots = []
        for name in only_top_dirs:
            d = scan_root / name
            if d.is_dir():
                roots.append(d)
    else:
        roots = [scan_root]
    for root in roots:
        for src in root.rglob("*"):
            if src.is_dir():
                continue
            if src.suffix.lower() in video_exts:
                continue
            # v3.27 : ignorer les dossiers système (cache de miniatures
            # Synology @eaDir, etc.) — jamais filtré ici jusqu'à présent,
            # contrairement au scan manuel (/scan). Un seul dossier de
            # série peut accumuler des dizaines de milliers de miniatures
            # @eaDir au fil du temps, recopiées pour rien dans le miroir.
            if any(part.lower() in SYSTEM_DIRS_EXCLUDED for part in src.parts):
                continue
            try:
                rel = src.relative_to(scan_root)
            except ValueError:
                continue
            dest = mirror_root / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or dest.stat().st_size != src.stat().st_size:
                shutil.copy2(src, dest)
                count += 1
    log_cb(f"Copie miroir : {count} fichier(s) annexe(s) (nfo, images...) synchronisés"
           f"{' (séries sélectionnées uniquement)' if only_top_dirs is not None else ''}.")

AUDIO_BAD_KEYWORDS = {"visual", "impaired", "description", "descriptive", "ad", "commentary", "commentaire", "director"}
SUB_DEPRIORITIZED_KEYWORDS = {"dubbing", "doublage", "karaoke", "karaoké", "chanson", "song", "signs",
                              "cc", "sdh", "canada", "canadien", "canadienne", "québec", "quebec"}
DIALOGUE_STYLE_HINTS = {"tiretsdefault", "tiretsitalique"}

SERIES_SPLIT_RE = re.compile(r"\.S\d{2}E\d{2}", re.IGNORECASE)

# v3.27 : dossiers système (caches de miniatures Synology, corbeille de
# versionnage, etc.) à ignorer PARTOUT où l'arborescence est parcourue —
# déjà utilisé par le scan manuel (/scan) mais jamais par sync_mirror_tree(),
# qui pouvait donc recopier des dizaines de milliers de miniatures @eaDir
# accumulées dans le dossier d'UNE SEULE série sélectionnée.
SYSTEM_DIRS_EXCLUDED = {"@eadir", "@tmp", "@__thumb", ".@__thumb", ".@tmp", ".hidden", ".trashes"}

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def mkvmerge_json(path):
    r = run(["mkvmerge", "-J", str(path)])
    if r.returncode != 0:
        raise RuntimeError(f"mkvmerge a échoué sur {path.name} : {r.stderr}")
    return json.loads(r.stdout)


def verify_remux(src_info, out_path):
    """v3.32 : contrôle du fichier produit AVANT qu'il ne remplace quoi que ce soit.
    Retourne '' si tout va bien, sinon la raison (fichier tronqué, piste vidéo/audio absente…)."""
    try:
        out = mkvmerge_json(Path(out_path))
    except Exception as e:
        return f"illisible ({e})"
    kinds = [t.get("type") for t in out.get("tracks", [])]
    if "video" not in kinds:
        return "aucune piste vidéo"
    if "audio" not in kinds:
        return "aucune piste audio"
    d_src = ((src_info or {}).get("container", {}).get("properties", {}) or {}).get("duration")
    d_out = (out.get("container", {}).get("properties", {}) or {}).get("duration")
    if d_src and d_out and int(d_out) < int(d_src) * 0.95 and int(d_src) - int(d_out) > 5_000_000_000:   # nettement plus court : tronqué
        return f"durée différente de l'original ({int(d_out) / 1e9:.0f} s au lieu de {int(d_src) / 1e9:.0f} s)"
    return ""


def is_already_processed(path):
    """v3.24 : vrai si `path` porte déjà le marqueur mouflanimexer (petit
    fichier attaché, voir MOUFLANIMEXER_MARKER_NAME) — donc déjà traité,
    qu'il ait été remplacé par le watcher automatique ou à la main par
    l'utilisateur après vérification manuelle. Volontairement tolérant :
    en cas d'erreur (fichier verrouillé, mkvmerge indisponible...), on
    répond False plutôt que de bloquer le traitement."""
    try:
        info = mkvmerge_json(path)
    except Exception:
        return False
    for att in info.get("attachments", []):
        if att.get("file_name") == MOUFLANIMEXER_MARKER_NAME:
            return True
    return False

def ffprobe_audio_info(path, ffidx):
    r = run([
        "ffprobe", "-v", "error", "-select_streams", f"a:{ffidx}",
        "-show_entries", "stream=bit_rate,channels,profile", "-of", "json", str(path),
    ])
    try:
        s = json.loads(r.stdout)["streams"][0]
        return int(s.get("bit_rate") or 0), int(s.get("channels") or 0), (s.get("profile") or "")
    except Exception:
        return 0, 0, ""

def _measure_audio_bitrate(path, ffidx):
    """Calcule un débit approximatif en sommant la taille des paquets sur
    la piste — fiable quand le conteneur ne déclare pas de bitrate (très
    courant en MKV/AAC), c'est la même méthode que MediaInfo/Emby."""
    r = run([
        "ffprobe", "-v", "error", "-select_streams", f"a:{ffidx}",
        "-show_entries", "packet=duration_time,size", "-of", "csv=p=0", str(path),
    ])
    total_bytes = 0
    total_time = 0.0
    for line in r.stdout.splitlines():
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            total_time += float(parts[0])
            total_bytes += int(parts[1])
        except ValueError:
            continue
    if total_time > 0:
        return int((total_bytes * 8) / total_time)
    return 0


def audio_quality_score(path, track, ffidx):
    props = track.get("properties", {})
    bitrate, channels, profile = ffprobe_audio_info(path, ffidx)
    bps = props.get("tag_bps")
    if bps:
        try:
            bitrate = int(bps) or bitrate
        except ValueError:
            pass
    if not bitrate:
        bitrate = _measure_audio_bitrate(path, ffidx)
    if not channels:
        channels = props.get("audio_channels", 0)
    return bitrate, channels, profile

def _matches_any_keyword(name, keywords):
    name = (name or "").lower()
    return any(re.search(rf"\b{re.escape(kw)}\b", name) for kw in keywords)

def is_unwanted_audio(track):
    props = track.get("properties", {})
    for flag_key in ("visual_impaired_flag", "flag_visual_impaired",
                     "text_descriptions_flag", "flag_text_descriptions",
                     "commentary_flag", "flag_commentary"):
        if props.get(flag_key):
            return True
    return _matches_any_keyword(props.get("track_name"), AUDIO_BAD_KEYWORDS)

def classify_tracks(info):
    audio_tracks = [t for t in info["tracks"] if t["type"] == "audio"]
    sub_tracks = [t for t in info["tracks"] if t["type"] == "subtitles"]
    audio_with_ffidx = list(enumerate(audio_tracks))

    jpn = [(t, i) for i, t in audio_with_ffidx
           if t["properties"].get("language") in LANGS_JPN and not is_unwanted_audio(t)]
    fre = [(t, i) for i, t in audio_with_ffidx
           if t["properties"].get("language") in LANGS_FRE and not is_unwanted_audio(t)]
    chi = [(t, i) for i, t in audio_with_ffidx
           if t["properties"].get("language") in LANGS_CHI and not is_unwanted_audio(t)]

    if not jpn:
        # Une piste audio sans langue du tout est presque toujours la VO
        # japonaise (seule la piste FR est explicitement taguée sur beaucoup
        # de releases).
        jpn = [(t, i) for i, t in audio_with_ffidx
               if t["properties"].get("language") in UNDETERMINED_LANGS and not is_unwanted_audio(t)]

    return audio_tracks, sub_tracks, jpn, fre, chi

def extract_subtitle(path, track_id, out_path):
    r = run(["mkvextract", "tracks", str(path), f"{track_id}:{out_path}"])
    if r.returncode != 0:
        raise RuntimeError(f"Extraction des sous-titres impossible : {r.stderr}")

def extract_series_name(path: Path) -> str:
    """Extrait le nom de la série + sous-dossier (si présent).
    Reconnaît les sous-dossiers : S01/S02, Season 1, Specials, OVA, OAV, Bonus, Movie, etc.
    
    Exemples:
      /anime/Hunter x Hunter/S01/ep01.mkv → "Hunter x Hunter / S01"
      /anime/Kaiju No. 8/Specials/ep01.mkv → "Kaiju No. 8 / Specials"
      /anime/Hunter x Hunter/ep01.mkv → "Hunter x Hunter"
      /anime/ep01.mkv → extrait du nom du fichier
    """
    # Chercher un sous-dossier pertinent (ex: S01, S02, Season 1, Specials, OVA, Bonus, Movie, etc.)
    parts = path.parts
    subdirs = []
    
    # Remonter jusqu'à 2 niveaux de parent pour trouver "série / sous-dossier"
    if len(parts) >= 2:
        parent = path.parent.name
        grandparent = path.parent.parent.name if len(parts) >= 3 else ""
        
        # Si parent a l'air d'un sous-dossier (S01, S1, Season 1, Specials, OVA, etc.)
        if parent and parent.lower() != WORK_ROOT.name.lower():
            # Reconnaître les dossiers de sous-type : saisons, spéciaux, OVA, bonus, films, etc.
            if re.search(r"^s\d+$|^season\s+\d+$|^specials?$|^ova$|^oav$|^bonus|^movie", parent.lower()):
                # C'est un sous-dossier → use grandparent comme série
                if grandparent and grandparent.lower() != WORK_ROOT.name.lower():
                    series_raw = grandparent
                    subdir = parent
                else:
                    # Pas de grandparent, extraire du fichier
                    series_raw = SERIES_SPLIT_RE.split(path.stem, maxsplit=1)[0].strip()
                    subdir = parent
            else:
                # Parent n'a pas l'air d'un sous-dossier standard
                series_raw = parent
                subdir = None
        else:
            # Parent n'existe pas ou est mouflanimexer
            series_raw = SERIES_SPLIT_RE.split(path.stem, maxsplit=1)[0].strip()
            subdir = None
    else:
        series_raw = SERIES_SPLIT_RE.split(path.stem, maxsplit=1)[0].strip()
        subdir = None
    
    # Nettoyer le nom de la série
    series_raw = series_raw.replace(".", " ").replace("_", " ")
    series_raw = re.sub(r"\s+", " ", series_raw).strip()
    series_name = series_raw.title()
    
    # Retourner avec sous-dossier s'il existe
    if subdir:
        return f"{series_name} / {subdir.upper()}"
    return series_name


def series_path(base: Path, anime_name: str) -> Path:
    """CORRECTIF V2.3 : construit le chemin de dossier réel pour une série,
    en gérant proprement le cas 'Série / Sous-dossier'.

    Bug corrigé : anime_name peut contenir " / " (ex: "Hunter X Hunter / S1").
    Faire directement `base / anime_name` fait que pathlib scinde la chaîne
    sur le "/" et crée DEUX dossiers imbriqués avec des espaces parasites
    en début/fin de nom ("Hunter X Hunter " puis " S1") — invalides sur un
    partage SMB/Samba, qui les remplace alors par un nom court DOS 8.3
    illisible (ex: "8ICLR2~W"). On découpe et nettoie chaque morceau avant
    de construire le chemin, pour obtenir de vrais dossiers propres :
    base / "Hunter X Hunter" / "S1"
    """
    parts = [p.strip() for p in anime_name.split(" / ") if p.strip()]
    return Path(base, *parts) if parts else base

def load_excluded_series():
    try:
        return set(json.loads(EXCLUDED_SERIES_PATH.read_text(encoding="utf-8")))
    except Exception:
        return set()

def save_excluded_series(series_set):
    try:
        EXCLUDED_SERIES_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXCLUDED_SERIES_PATH.write_text(
            json.dumps(sorted(series_set), ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def load_extra_sub_lang():
    """(v3.19) Retourne {nom_série: [codes_langue]} — séries pour
    lesquelles une ou plusieurs pistes de sous-titres supplémentaires
    (hors FR) doivent être conservées telles quelles dans le fichier
    final, en plus de la piste FR normale."""
    try:
        return json.loads(EXTRA_SUB_LANG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_extra_sub_lang(mapping):
    try:
        EXTRA_SUB_LANG_PATH.parent.mkdir(parents=True, exist_ok=True)
        EXTRA_SUB_LANG_PATH.write_text(
            json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        pass

def _profile_for_style(name):
    """Trouve le profil correspondant à un nom de style (insensible à la casse).
    Accepte les correspondances partielles pour ignorer les suffixes comme " - 720"."""
    name_lower = name.lower().strip()
    for profile in STYLE_PROFILES.values():
        # Vérifier si le keyword du profil est INCLUS dans le nom du style (pas égalité exacte)
        if any(m.lower() in name_lower for m in profile["match"]):
            return profile
    return None

def read_play_res(ass_path):
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    x = y = None
    found_x = found_y = False
    in_info = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_info = stripped.lower() == "[script info]"
            continue
        if in_info:
            if stripped.startswith("PlayResX:"):
                found_x = True
                try: x = int(stripped.split(":", 1)[1].strip())
                except ValueError: pass
            elif stripped.startswith("PlayResY:"):
                found_y = True
                try: y = int(stripped.split(":", 1)[1].strip())
                except ValueError: pass

    # Cas 1 : PlayResX/Y complètement ABSENTS du fichier (ex: Boruto/LSCO).
    # La plupart des fansubs qui omettent ces lignes calibrent en réalité
    # leur script à la résolution native de la vidéo (souvent déjà 1080p
    # pour les releases WEBRip/Bluray récentes) — donc PAS de mise à l'échelle
    # nécessaire. On considère le script déjà à la résolution cible.
    if not found_x and not found_y:
        return TARGET_PLAYRES if TARGET_PLAYRES else (640, 360)

    # Cas 2 : UNE SEULE des deux valeurs est déclarée (ex: Dragon Ball
    # DBP/Aegisub v1.10 : "PlayResY: 864" seul, sans aucune ligne
    # PlayResX). Convention standard ASS/libass/VSFilter : la dimension
    # manquante est déduite de l'autre via un ratio 4:3 — PAS un SD
    # 640x360 par défaut. Sans ce correctif, une hauteur réelle de 864
    # était interprétée comme 360, provoquant une mise à l'échelle ×3 au
    # lieu de ×1.25 et des sous-titres démesurés (Dragon Ball S0E01,
    # style "Title" fontsize 110 → ~330 au lieu de ~137).
    if found_x and not found_y and x:
        y = round(x * 3 / 4)
    elif found_y and not found_x and y:
        x = round(y * 4 / 3)

    # Cas 3 : présents mais vides/invalides/à 0 (bug Death Note :
    # "PlayResX: 0" / "PlayResY: 0" explicitement déclarés) → ancienne
    # convention SD par défaut.
    if x is None or y is None or x == 0 or y == 0:
        return (640, 360)  # Résolution par défaut ASS
    return x, y

_POS_RE = re.compile(r"\\pos\(\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*\)")
_ORG_RE = re.compile(r"\\org\(\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*\)")
_MOVE_RE = re.compile(
    r"\\move\(\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)"
    r"(\s*,\s*[\-\d.]+\s*,\s*[\-\d.]+)?\)")
_CLIP_RE = re.compile(r"\\(i?clip)\(\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*\)")   # v3.33 : \iclip aussi
# v3.33 : effets rares jusque-là oubliés par la mise à l'échelle
_VCLIP_RE = re.compile(r"\\(i?clip)\(\s*(?:(\d+)\s*,\s*)?([mnlbspcMNLBSPC][^)]*)\)")   # découpe en forme de dessin
_XYBORD_RE = re.compile(r"\\(xbord|ybord|xshad|yshad)(-?[\d.]+)")
_FSP_RE = re.compile(r"\\fsp(-?[\d.]+)")
_PBO_RE = re.compile(r"\\pbo(-?[\d.]+)")
_DRAW_TAG_RE = re.compile(r"\\p(\d+)|\\r")
_DRAW_TOKEN_RE = re.compile(r"[a-zA-Z]|-?\d+(?:\.\d+)?")


def _fmt_num(v):
    """2 décimales maximum, sans zéros inutiles (« 12.50 » -> « 12.5 », « 12.00 » -> « 12 »)."""
    t = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def scale_drawing(drawing, sx, sy):
    """v3.33 : met à l'échelle les coordonnées d'un dessin ASS (« m 0 0 l 100 0 100 50 »…) :
    les nombres vont par paires x y, quelle que soit la commande (m, n, l, b, s, p, c)."""
    out, i = [], 0
    for tok in _DRAW_TOKEN_RE.findall(drawing):
        if tok.isalpha():
            out.append(tok)
            i = 0                     # chaque commande repart sur un x
        else:
            out.append(_fmt_num(float(tok) * (sx if i % 2 == 0 else sy)))
            i += 1
    return " ".join(out)


def scale_drawing_text(txt, sx, sy):
    """v3.33 : dans une ligne, le texte qui suit \\p1 (ou \\p2…) jusqu'à \\p0 est un dessin, pas du texte : on le met à l'échelle."""
    parts = re.split(r"(\{[^}]*\})", txt)
    level = 0
    for k, part in enumerate(parts):
        if part.startswith("{") and part.endswith("}"):
            for m in _DRAW_TAG_RE.finditer(part):
                level = int(m.group(1)) if m.group(1) is not None else 0
        elif level > 0 and part.strip():
            parts[k] = scale_drawing(part, sx, sy)
    return "".join(parts)
_FS_RE = re.compile(r"\\fs([\d.]+)")
_BORD_RE = re.compile(r"\\bord([\d.]+)")
_SHAD_RE = re.compile(r"\\shad([\d.]+)")

def get_true_orig_res(ass_path, declared_res):
    """CORRECTIF BUG 1 : Détermine la vraie résolution du script.
    
    Certains fansubs déclarent PlayResX/Y = 1920x1080 mais écrivent en réalité
    leurs coordonnées comme si c'était 640x360 (erreur ou habitude de template).
    
    **Stratégie de détection** :
    1. **PRIORITÉ AUX POSITIONS** : si les \pos indiquent clairement du 1920×1080,
       on croit les positions (elles ne mentent pas).
    2. **Ensuite tailles de font** : si beaucoup de styles sont petits (<35),
       c'est probablement du 640×360.
    3. **Fallback** : positions dans un petit coin ? → 640×360.
    """
    # Rejeter les résolutions aberrantes (0x0 = Death Note bug)
    if declared_res == (0, 0):
        return (640, 360)  # Fallback immédiat pour (0, 0)
    
    if declared_res != TARGET_PLAYRES:
        return declared_res

    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")

    # === ÉTAPE 1 : Analyser les positions ===
    max_x, max_y, pos_count = 0, 0, 0
    for m in _POS_RE.finditer(text):
        max_x = max(max_x, float(m.group(1)))
        max_y = max(max_y, float(m.group(2)))
        pos_count += 1

    # Si positions clairement dans les hautes valeurs → c'est du 1920×1080
    # (750 = seuil : en 640×360, on ne pourrait pas dépasser ~640)
    if pos_count > 0 and max_x > 750:
        return (1920, 1080)

    # === ÉTAPE 2 : Analyser les tailles de font (ignorer les styles annexes) ===
    style_sizes = []
    for line in text.splitlines():
        if line.startswith("Style:"):
            parts = line[len("Style:"):].strip().split(",")
            if len(parts) > 2:
                try:
                    fsize = float(parts[2])
                    style_sizes.append(fsize)
                except ValueError:
                    pass

    # Si beaucoup de styles ont une taille "normale" (>=35), c'est du 1920×1080
    # Les styles annexes (Debu, Step1, Plaque...) sont petits volontairement.
    if style_sizes:
        big_styles = sum(1 for s in style_sizes if s >= 35)
        # Au moins 50% de tailles normales = c'est du 1920×1080
        if big_styles >= len(style_sizes) * 0.5:
            return (1920, 1080)

    # === ÉTAPE 3 : Fallback positions ===
    if pos_count > 0 and max_x <= 750 and max_y <= 500:
        return (640, 360)

    return declared_res

def scale_positioning_tags(ass_path, orig_res, target_res):
    if not orig_res or orig_res == target_res:
        return
    
    ox, oy = orig_res
    tx, ty = target_res
    if not ox or not oy:
        return
    sx = tx / ox
    sy = ty / oy

    def repl_pos(m):
        x, y = float(m.group(1)), float(m.group(2))
        return f"\\pos({x*sx:.2f},{y*sy:.2f})"

    def repl_org(m):
        x, y = float(m.group(1)), float(m.group(2))
        return f"\\org({x*sx:.2f},{y*sy:.2f})"

    def repl_move(m):
        x1, y1, x2, y2 = (float(m.group(i)) for i in (1, 2, 3, 4))
        tail = m.group(5) or ""
        return f"\\move({x1*sx:.2f},{y1*sy:.2f},{x2*sx:.2f},{y2*sy:.2f}{tail})"

    def repl_clip(m):
        x1, y1, x2, y2 = (float(m.group(i)) for i in (2, 3, 4, 5))
        return f"\\{m.group(1)}({x1*sx:.2f},{y1*sy:.2f},{x2*sx:.2f},{y2*sy:.2f})"

    def repl_vclip(m):
        scale = f"{m.group(2)}," if m.group(2) else ""
        return f"\\{m.group(1)}({scale}{scale_drawing(m.group(3), sx, sy)})"

    def repl_xy(m):
        f = sx if m.group(1) in ("xbord", "xshad") else sy
        return f"\\{m.group(1)}{_fmt_num(float(m.group(2)) * f)}"

    def repl_fsp(m): return f"\\fsp{_fmt_num(float(m.group(1)) * sx)}"
    def repl_pbo(m): return f"\\pbo{_fmt_num(float(m.group(1)) * sy)}"

    def repl_fs(m): return f"\\fs{float(m.group(1)) * sy:.2f}"
    def repl_bord(m): return f"\\bord{float(m.group(1)) * sy:.2f}"
    def repl_shad(m): return f"\\shad{float(m.group(1)) * sy:.2f}"

    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    out = []
    in_events = False
    fmt_fields = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            out.append(line)
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            out.append(line)
            continue
        if in_events and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields):
                row = dict(zip(fmt_fields, parts))
                txt = row.get("text", "")
                txt = _POS_RE.sub(repl_pos, txt)
                txt = _ORG_RE.sub(repl_org, txt)
                txt = _MOVE_RE.sub(repl_move, txt)
                txt = _CLIP_RE.sub(repl_clip, txt)
                txt = _VCLIP_RE.sub(repl_vclip, txt)
                txt = _FS_RE.sub(repl_fs, txt)
                txt = _BORD_RE.sub(repl_bord, txt)
                txt = _SHAD_RE.sub(repl_shad, txt)
                txt = _XYBORD_RE.sub(repl_xy, txt)
                txt = _FSP_RE.sub(repl_fsp, txt)
                txt = _PBO_RE.sub(repl_pbo, txt)
                txt = scale_drawing_text(txt, sx, sy)
                row["text"] = txt
                line = "Dialogue:" + ",".join(row[f] for f in fmt_fields)
        out.append(line)
    Path(ass_path).write_text("\n".join(out), encoding="utf-8")

def _find_main_dialogue_style(ass_path):
    """CORRECTIF BUG 2 : Détecte le style principal utilisé par les dialogues.
    
    Au lieu de supposer que le style s'appelle "Default", on repère le style
    qui est utilisé par le plus de dialogues. Marche pour "Default", "Dialogue",
    "DIA", ou n'importe quel nom custom.
    """
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    style_count = {}
    in_events = False
    fmt_fields = None
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            continue
        if in_events and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields):
                row = dict(zip(fmt_fields, parts))
                style = row.get("style", "").strip()
                if style:
                    style_count[style] = style_count.get(style, 0) + 1
    
    if style_count:
        return max(style_count, key=style_count.get)  # Style le plus fréquent
    return None

def patch_ass_style(ass_path, orig_res=None, apply_style_profiles=True, skip_profile_styles=None):
    """apply_style_profiles=False (v3.21) : ne jamais réécrire la police/
    les couleurs/le style d'après STYLE_PROFILES (pensé pour le FR —
    "Trebuchet MS" etc.), seulement la mise à l'échelle de résolution
    (fontsize/outline/marges proportionnels si orig_res != TARGET_PLAYRES).

    v3.26 : skip_profile_styles (ensemble de noms de style EXACTS,
    optionnel) exempte CES styles précis de toute réécriture FR — direct
    ou via le repli "style principal" — sans toucher aux autres styles du
    MÊME fichier. Indispensable pour une piste bilingue (ex: coréen avec
    du FR en \\an8 ajouté par-dessus) : son style coréen porte souvent un
    nom qui matche accidentellement un profil FR par sous-chaîne (ex:
    "Default -kor" contient "default", v3.21), MAIS les styles utilisés
    pour les lignes FR ajoutées par-dessus (ex: "Default", "Sign",
    "Italique") doivent eux conserver le style FR habituel — d'où ce
    filtre par nom de style plutôt qu'un simple interrupteur global."""
    skip_profile_styles = skip_profile_styles or set()
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    out = []
    in_script_info = False
    in_styles = False
    is_ssa = False
    style_fmt = None
    
    # CORRECTIF BUG 2 : Trouver le style principal une seule fois
    main_dialogue_style = _find_main_dialogue_style(ass_path)
    
    needs_scale = orig_res and TARGET_PLAYRES and orig_res != TARGET_PLAYRES

    # Flags pour tracker les lignes vues dans [Script Info], et les insérer
    # si absentes du fichier d'origine (bug Boruto/LSCO : fichier sans
    # PlayResX/PlayResY du tout → les lecteurs retombent sur l'ancien
    # défaut SSA 384x288, rendant nos tailles de police (calibrées pour
    # 1920x1080) démesurément grandes)
    seen_scaled_border_and_shadow = False
    seen_playresx = False
    seen_playresy = False

    for line in text.splitlines():
        stripped = line.strip()

        if stripped.startswith("["):
            # Si on quitte la section Script Info et qu'il manque des lignes
            # essentielles, les ajouter avant de passer à la section suivante
            if in_script_info and TARGET_PLAYRES:
                if not seen_playresx:
                    out.append(f"PlayResX: {TARGET_PLAYRES[0]}")
                if not seen_playresy:
                    out.append(f"PlayResY: {TARGET_PLAYRES[1]}")
                if not seen_scaled_border_and_shadow:
                    out.append("ScaledBorderAndShadow: yes")
            in_script_info = stripped.lower() == "[script info]"
            in_styles = stripped.lower() in ("[v4+ styles]", "[v4 styles]")
            is_ssa = stripped.lower() == "[v4 styles]"          # v3.33 : vieux format SSA (champs différents)
            style_fmt = None
            out.append(line)
            continue

        if in_styles and stripped.lower().startswith("format:"):
            style_fmt = [f.strip().lower() for f in stripped[len("format:"):].split(",")]

        if in_script_info and TARGET_PLAYRES:
            if stripped.startswith("PlayResX:"):
                out.append(f"PlayResX: {TARGET_PLAYRES[0]}")
                seen_playresx = True
                continue
            if stripped.startswith("PlayResY:"):
                out.append(f"PlayResY: {TARGET_PLAYRES[1]}")
                seen_playresy = True
                continue
            if stripped.startswith("ScaledBorderAndShadow:"):
                # Force ScaledBorderAndShadow: yes pour que les ombres se redimensionnent correctement
                out.append("ScaledBorderAndShadow: yes")
                seen_scaled_border_and_shadow = True
                continue

        if in_styles and line.startswith("Style:"):
            raw_fields = line[len("Style:"):].strip().split(",")
            if is_ssa or len(raw_fields) < 22:
                # v3.33 : SSA (« [V4 Styles] », 18 champs) — avant, rien n'était mis à l'échelle alors que
                # PlayRes passe en 1920x1080 (texte 3x trop petit). Pas de profil FR ici (format différent),
                # seulement la mise à l'échelle, d'après la ligne « Format: ».
                if needs_scale and style_fmt and len(raw_fields) == len(style_fmt):
                    ox, oy = orig_res
                    tx, ty = TARGET_PLAYRES
                    fx, fy = tx / ox, ty / oy
                    try:
                        for key, factor in (("fontsize", fy), ("outline", fy), ("shadow", fy), ("spacing", fx),
                                            ("marginl", fx), ("marginr", fx), ("marginv", fy)):
                            if key in style_fmt:
                                k = style_fmt.index(key)
                                raw_fields[k] = _fmt_num(float(raw_fields[k]) * factor) if key in ("outline", "shadow", "spacing") else str(round(float(raw_fields[k]) * factor))
                        out.append("Style: " + ",".join(raw_fields))
                        continue
                    except ValueError:
                        pass
                out.append(line)
                continue
                
            name = raw_fields[0].strip()
            if name in skip_profile_styles:
                # v3.26 : exempté explicitement (ex: style coréen d'une
                # piste bilingue) — jamais de profil FR, ni direct ni par repli.
                profile = None
            else:
                profile = _profile_for_style(name) if apply_style_profiles else None

                # CORRECTIF BUG 2 : Si pas de match direct mais c'est le style principal
                # → on lui applique le profil dialogue
                if apply_style_profiles and not profile and name == main_dialogue_style:
                    profile = STYLE_PROFILES.get("dialogue")

            if profile:
                italic = "-1" if name in profile["italic_match"] else "0"
                out.append("Style: " + ",".join([
                    name, profile["fontname"], profile["fontsize"],
                    profile["primary_colour"], profile["secondary_colour"],
                    profile["outline_colour"], profile["back_colour"],
                    profile["bold"], italic, profile["underline"], profile["strikeout"],
                    profile["scale_x"], profile["scale_y"], profile["spacing"], profile["angle"],
                    profile["border_style"], profile["outline"], profile["shadow"],
                    profile["alignment"], profile["margin_l"], profile["margin_r"],
                    profile["margin_v"], profile["encoding"],
                ]))
                continue
            
            # Pour les styles non reconnus, on redimensionne uniquement si nécessaire
            if needs_scale:
                ox, oy = orig_res
                tx, ty = TARGET_PLAYRES
                sx, sy = tx / ox, ty / oy
                try:
                    # Fontsize (index 2)
                    raw_fields[2] = str(round(float(raw_fields[2]) * sy))
                    # Outline (index 16)
                    raw_fields[16] = str(round(float(raw_fields[16]) * sy))
                    # Shadow (index 17)
                    raw_fields[17] = str(round(float(raw_fields[17]) * sy))
                    # Espacement des lettres (index 13), en pixels horizontaux (v3.33)
                    raw_fields[13] = _fmt_num(float(raw_fields[13]) * sx)
                    # MarginL (index 19)
                    raw_fields[19] = str(round(float(raw_fields[19]) * sx))
                    # MarginR (index 20)
                    raw_fields[20] = str(round(float(raw_fields[20]) * sx))
                    # MarginV (index 21)
                    raw_fields[21] = str(round(float(raw_fields[21]) * sy))
                    out.append("Style: " + ",".join(raw_fields))
                    continue
                except (ValueError, IndexError):
                    pass

        out.append(line)
    Path(ass_path).write_text("\n".join(out), encoding="utf-8")

_BLUR_DETECT_RE = re.compile(r"\\(blur|be)([\d.]+)")

PREVIEW_DIR = WORK_ROOT / "Previews"      # créé au premier aperçu

def _ffmpeg_escape_path(p):
    p = str(p)
    return p.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")

def _normalize_ass_time(t):
    parts = t.split(":")
    if len(parts) == 3:
        h, m, s = parts
        return f"{int(h):02d}:{m}:{s}"
    return t

def generate_preview(video_path, ass_path, ass_time, out_jpg):
    """Extrait une image avec le sous-titre incrusté au bon moment.
    IMPORTANT : -ss avant -i (seek rapide) remet l'horodatage de la
    vidéo à ~0, ce qui fait que le filtre 'subtitles' (calé sur les
    horodatages ABSOLUS du .ass) ne trouve plus aucune ligne à afficher
    au moment recherché -> aucun sous-titre visible sur la capture.
    -copyts conserve l'horodatage d'origine et corrige ce problème.
    Le fichier .ass est aussi copié vers un nom neutre : un nom
    d'origine avec apostrophe/esperluette (ex: "Roji's", "&") casse le
    parseur de filtres ffmpeg même échappé correctement."""
    ts = _normalize_ass_time(ass_time)
    safe_ass = Path(ass_path).parent / "_preview_input.ass"
    shutil.copy(ass_path, safe_ass)
    vf = f"subtitles='{_ffmpeg_escape_path(safe_ass)}'"
    r = run([
        "ffmpeg", "-y", "-copyts", "-ss", ts, "-i", str(video_path),
        "-vf", vf, "-frames:v", "1", "-q:v", "3", str(out_jpg),
    ])
    return r.returncode == 0 and Path(out_jpg).exists()

def detect_blur_lines(ass_path):
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    found = []
    in_events = False
    fmt_fields = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            continue
        if in_events and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields):
                row = dict(zip(fmt_fields, parts))
                txt = row.get("text", "")
                matches = [(tag, val) for tag, val in _BLUR_DETECT_RE.findall(txt) if float(val) > 0]
                if matches:
                    clean_text = re.sub(r"\{[^}]*\}", "", txt).replace("\\N", " / ").strip()
                    found.append({
                        "start": row.get("start", "?"),
                        "style": row.get("style", "?"),
                        "tags": ", ".join(f"\\{tag}{val}" for tag, val in matches),
                        "text": clean_text,
                    })
    return found

_FN_TAG_RE = re.compile(r"\\fn([^\\}]+)")


def _normalize_font_key(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_font_file(font_name, search_dirs):
    """Cherche un fichier .ttf/.otf dont le nom correspond à font_name
    (comparaison tolérante : espaces/casse/tirets ignorés).
    CORRECTIF v2.6 : font_name est parfois passé avec son extension
    (ex: "ArialBold.ttf") — sans le Path(...).stem ci-dessous, la clé
    normalisée devenait "arialboldttf", qui ne correspond plus jamais au
    stem normalisé d'un fichier existant ("arialbold"), donc même une
    police correctement nommée et fraîchement uploadée n'était jamais
    retrouvée par wait_for_font_upload()."""
    key = _normalize_font_key(Path(font_name).stem)
    loose = None
    for d in search_dirs:
        if not d or not Path(d).exists():
            continue
        for f in sorted(Path(d).iterdir()):
            if f.suffix.lower() not in (".ttf", ".otf"):
                continue
            stem = _normalize_font_key(f.stem)
            if stem == key:
                return f                      # v3.32 : le nom exact d'abord (« Arial » ne prend plus « ArialBold » s'il existe)
            if loose is None and key in stem:
                loose = f
    return loose


def wait_for_font_upload(font_name, search_dirs=None):
    """Suspend le traitement jusqu'à ce qu'une police VALIDE soit fournie via
    l'interface web pour font_name, ou ignorée. Boucle bloquante jusqu'à
    ce que le fichier fourni soit trouvable via find_font_file()."""
    if search_dirs is None:
        search_dirs = []
    
    while True:
        uploaded_path = yield ("missing_font", font_name)
        # Si l'utilisateur a ignoré la demande (None), sortir
        if uploaded_path is None:
            return None
        # Vérifier que le fichier existe
        if not Path(uploaded_path).exists():
            continue  # Redemander si le fichier n'existe pas
        
        # Vérifier que la police est maintenant trouvable dans la biblio
        if find_font_file(font_name, search_dirs):
            return uploaded_path
        # Sinon, redemander (message implicite via la boucle)


def detect_inline_fonts(ass_path):
    """Repère les polices imposées directement sur une ligne via \\fn
    (plutôt que via un style) — ex: {\\fnImpact} — pour vérifier qu'elles
    seront bien disponibles au visionnage."""
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    return {m.group(1).strip() for m in _FN_TAG_RE.finditer(text) if m.group(1).strip()}


def detect_style_fonts(ass_path):
    """v3.21 : repère les polices déclarées dans la colonne Fontname des
    lignes Style ([V4+ Styles]) — contrairement à detect_inline_fonts(),
    qui ne voit que les \\fn placés en ligne dans le texte. Nécessaire pour
    les pistes traitées avec apply_style_profiles=False (ex: piste
    "extra::<lang>", voir patch_ass_style) : leur police d'origine n'est
    plus jamais réécrite, donc c'est la seule façon de savoir quelle
    police doit être embarquée pour que les caractères s'affichent
    (sinon : carrés/tofu sur un lecteur qui ne l'a pas en police système)."""
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    fonts = set()
    in_styles = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_styles = stripped.lower() == "[v4+ styles]"
            continue
        if in_styles and line.startswith("Style:"):
            fields = line[len("Style:"):].strip().split(",")
            if len(fields) >= 2 and fields[1].strip():
                fonts.add(fields[1].strip())
    return fonts


# v3.26 : plages Unicode des alphabets des langues "extra sous-titre"
# couramment rencontrées, pour détecter par le CONTENU réel (plutôt que
# par le nom du style) quel(s) style(s) appartiennent vraiment à la
# langue supplémentaire dans un fichier .ass bilingue (ex: coréen + FR en
# \an8 ajouté par-dessus par l'utilisateur) — voir detect_extra_lang_styles().
_SCRIPT_RANGES_BY_LANG = {
    "kor": [(0x1100, 0x11FF), (0x3130, 0x318F), (0xAC00, 0xD7A3)],
    "jpn": [(0x3040, 0x30FF), (0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
    "chi": [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
    "zho": [(0x4E00, 0x9FFF), (0x3400, 0x4DBF)],
    "rus": [(0x0400, 0x04FF)],
    "ara": [(0x0600, 0x06FF)],
    "tha": [(0x0E00, 0x0E7F)],
}


def detect_extra_lang_style_usage(ass_path, lang_code):
    """v3.28 : repère, parmi les lignes [Events]/Dialogue, quels styles
    sont utilisés pour du texte dans l'alphabet de `lang_code` (ex:
    coréen) — pas par le nom du style, mais par son contenu effectif.

    Certains épisodes donnent à la langue supplémentaire un style qui lui
    est ENTIÈREMENT dédié (ex: "Default -kor", jamais utilisé pour du FR)
    — ce style est "pur" (`pure`). D'AUTRES épisodes du même anime
    réutilisent le MÊME style à la fois pour le FR ajouté en \\an8 ET pour
    la langue d'origine, sans \\fn par ligne pour les distinguer (ex:
    "Default" utilisé par 624 lignes dont 337 en coréen et 287 en
    français, observé sur Smoking Behind the Supermarket with You
    S01E07) — ce style est "mixte" (`mixed`) : lui retirer son style FR
    habituel casserait l'affichage des lignes FR qui PARTAGENT ce style,
    donc il doit au contraire le GARDER (voir l'appelant), et seules les
    lignes du bon alphabet doivent recevoir une police forcée EN LIGNE
    (voir force_inline_font_for_script_lines()).

    Retourne (pure_styles, mixed_styles), deux sets de noms de style.
    Vides si `lang_code` n'a pas de plage Unicode connue."""
    ranges = _SCRIPT_RANGES_BY_LANG.get((lang_code or "").lower())
    if not ranges:
        return set(), set()
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    total_by_style = {}
    script_by_style = {}
    in_events = False
    fmt_fields = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            continue
        if in_events and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) != len(fmt_fields):
                continue
            row = dict(zip(fmt_fields, parts))
            style_name = row.get("style", "").strip()
            if not style_name:
                continue
            total_by_style[style_name] = total_by_style.get(style_name, 0) + 1
            clean = re.sub(r"\{[^}]*\}", "", row.get("text", ""))
            if any(any(lo <= ord(ch) <= hi for lo, hi in ranges) for ch in clean):
                script_by_style[style_name] = script_by_style.get(style_name, 0) + 1
    pure, mixed = set(), set()
    for name, total in total_by_style.items():
        script_count = script_by_style.get(name, 0)
        if script_count == 0:
            continue
        if script_count == total:
            pure.add(name)
        else:
            mixed.add(name)
    return pure, mixed


def force_inline_font_for_script_lines(ass_path, fontname, lang_code, styles):
    """v3.28 : pour un style "mixte" (voir detect_extra_lang_style_usage,
    ex: "Default" partagé entre FR et coréen sans \\fn par ligne), force
    `fontname` en préfixe ({\\fnXXX}) de CHAQUE ligne Dialogue qui (a)
    utilise un style de `styles` ET (b) contient réellement l'alphabet de
    `lang_code` — sans toucher au Style lui-même (qui garde son style FR
    habituel pour les autres lignes du même style)."""
    ranges = _SCRIPT_RANGES_BY_LANG.get((lang_code or "").lower())
    if not ranges or not styles:
        return
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    out = []
    in_events = False
    fmt_fields = None
    style_idx = text_idx = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            style_idx = text_idx = None
            out.append(line)
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            style_idx = fmt_fields.index("style") if "style" in fmt_fields else None
            text_idx = fmt_fields.index("text") if "text" in fmt_fields else None
            out.append(line)
            continue
        if (in_events and fmt_fields and style_idx is not None and text_idx is not None
                and line.startswith("Dialogue:")):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields) and parts[style_idx].strip() in styles:
                raw_text = parts[text_idx]
                clean = re.sub(r"\{[^}]*\}", "", raw_text)
                if any(any(lo <= ord(ch) <= hi for lo, hi in ranges) for ch in clean):
                    parts[text_idx] = f"{{\\fn{fontname}}}" + raw_text
                    out.append("Dialogue: " + ",".join(parts))
                    continue
        out.append(line)
    Path(ass_path).write_text("\n".join(out), encoding="utf-8")


def force_style_fontname(ass_path, fontname, only_styles=None):
    """v3.22 : remplace la colonne Fontname des lignes Style par
    `fontname`, sans toucher au reste (taille/couleurs/marges déjà gérées
    par patch_ass_style). Utilisé uniquement sur les pistes "extra::<lang>"
    pour forcer une police à large couverture Unicode (voir
    EXTRA_SUB_UNIVERSAL_FONT) — la police déclarée dans le .ass d'origine
    peut très bien exister dans la bibliothèque (donc ne déclencherait
    aucune alerte "police manquante") sans pour autant contenir les
    glyphes du bon alphabet (ex: "Trebuchet MS" n'a aucun caractère
    coréen), ce qui donnait des carrés/tofu à l'affichage sans qu'aucune
    vérification existante ne le détecte.

    v3.26 : only_styles (ensemble de noms de style EXACTS, optionnel)
    restreint le remplacement à CES styles précis — None (défaut) garde
    l'ancien comportement (tous les styles). Indispensable pour une piste
    bilingue : on ne veut forcer la police universelle QUE sur le style
    réellement coréen, jamais sur les styles utilisés par le FR ajouté
    par-dessus (ex: "Default", "Sign"), qui doivent garder leur police FR
    habituelle (Trebuchet MS/Arial, posée par patch_ass_style)."""
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    out = []
    in_styles = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("["):
            in_styles = stripped.lower() == "[v4+ styles]"
            out.append(line)
            continue
        if in_styles and line.startswith("Style:"):
            fields = line[len("Style:"):].strip().split(",")
            if len(fields) >= 2 and (only_styles is None or fields[0].strip() in only_styles):
                fields[1] = fontname
                out.append("Style: " + ",".join(fields))
                continue
        out.append(line)
    Path(ass_path).write_text("\n".join(out), encoding="utf-8")


def find_custom_margin_lines(ass_path, true_res=None):
    """Repère les lignes 'normales' (pas de dialogue à deux personnages,
    déjà géré automatiquement) qui ont une marge personnalisée non nulle
    sur la ligne elle-même — probablement calibrée pour l'ancienne
    résolution, et jamais touchée par le reste du script.
    
    Utilise true_res (résolution d'origine réelle) si fourni, sinon lit PlayResX.
    Crucial : doit être appelé AVANT patch_ass_style() pour avoir la bonne résolution."""
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    
    # Lire la résolution pour filtrer les marges aberrantes
    if true_res:
        playres_x = true_res[0]  # Utiliser la vraie résolution d'origine
    else:
        playres_x = 640  # fallback
        for line in lines:
            if line.strip().lower().startswith("playresx:"):
                try:
                    playres_x = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
                break
    
    max_reasonable_margin = playres_x // 2  # Une marge > moitié de la largeur est aberrante
    
    hits = []
    in_events = False
    fmt_fields = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            continue
        if in_events and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields):
                row = dict(zip(fmt_fields, parts))
                style_name = row.get("style", "").strip()
                text_field = row.get("text", "")
                
                # Filtrer les marges aberrantes EN PREMIER (avant is_two_person_line)
                try:
                    ml = int(float(row.get("marginl", "0") or 0))
                    mr = int(float(row.get("marginr", "0") or 0))
                    mv = int(float(row.get("marginv", "0") or 0))
                except ValueError:
                    continue
                
                if ml > max_reasonable_margin or mr > max_reasonable_margin:
                    continue  # Ignorer les marges impossibles (même pour dialogues à deux perso)
                
                if is_two_person_line(style_name, text_field):
                    continue
                if re.search(r"\\pos\(|\\move\(", text_field):
                    continue  # \pos/\move écrase la marge, la comparer n'aurait aucun sens
                
                if ml or mr or mv:
                    hits.append({
                        "line_index": i, "start": row.get("start", "?"), "style": style_name,
                        "text": re.sub(r"\{[^}]*\}", "", text_field).strip(),
                        "marginl": ml, "marginr": mr, "marginv": mv,
                    })
    return hits


def set_event_line_margins(ass_path, line_index, ml, mr, mv):
    """Remplace MarginL/MarginR/MarginV sur UNE ligne précise (repérée par
    son numéro de ligne), sans toucher au reste du fichier."""
    lines = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    fmt_fields = None
    in_events = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            continue
        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            continue
        if i == line_index and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields):
                row = dict(zip(fmt_fields, parts))
                row["marginl"], row["marginr"], row["marginv"] = str(ml), str(mr), str(mv)
                lines[i] = "Dialogue:" + ",".join(row[f] for f in fmt_fields)
            break
    Path(ass_path).write_text("\n".join(lines), encoding="utf-8")


def pick_margin_choice_gen(video_path, out_ass, group, sx, sy, margin_decisions):
    """Propose une capture avec la marge d'origine et une avec la marge
    redimensionnée pour un groupe de lignes qui partagent la même marge,
    et applique le choix retenu à toutes les lignes du groupe.
    
    Si cette marge exacte a déjà été validée dans cette série, applique
    automatiquement le même choix sans re-demander."""
    hit = group[0]
    margin_key = (hit["marginl"], hit["marginr"], hit["marginv"])
    
    # Si marge déjà validée, appliquer le choix automatiquement
    if margin_key in margin_decisions:
        choice = margin_decisions[margin_key]
        scaled_ml = round(hit["marginl"] * sx)
        scaled_mr = round(hit["marginr"] * sx)
        scaled_mv = round(hit["marginv"] * sy)
        if choice == 1:
            for h in group:
                set_event_line_margins(out_ass, h["line_index"], scaled_ml, scaled_mr, scaled_mv)
        # Log discret (juste pour la première application automatique)
        yield ("info", f"Marge {margin_key} appliquée automatiquement (choix précédent).")
        return
    
    # Sinon, demander comme avant
    scaled_ml = round(hit["marginl"] * sx)
    scaled_mr = round(hit["marginr"] * sx)
    scaled_mv = round(hit["marginv"] * sy)

    safe_time = hit["start"].replace(":", "-")
    base = f"{Path(out_ass).stem}_margin_{safe_time}"

    PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    keep_jpg = PREVIEW_DIR / f"{base}_original.jpg"
    ok_keep = generate_preview(video_path, out_ass, hit["start"], keep_jpg)

    tmp_scaled = Path(out_ass).with_name(Path(out_ass).stem + f"_margin_test_{safe_time}.ass")
    shutil.copy(out_ass, tmp_scaled)
    set_event_line_margins(tmp_scaled, hit["line_index"], scaled_ml, scaled_mr, scaled_mv)
    scaled_jpg = PREVIEW_DIR / f"{base}_redimensionne.jpg"
    ok_scaled = generate_preview(video_path, tmp_scaled, hit["start"], scaled_jpg)

    choices = [
        {"label": f"Garder telle quelle ({hit['marginl']}/{hit['marginr']}/{hit['marginv']})",
         "image": f"/preview/{_urlquote(keep_jpg.name)}" if ok_keep else None},
        {"label": f"Redimensionner ({scaled_ml}/{scaled_mr}/{scaled_mv})",
         "image": f"/preview/{_urlquote(scaled_jpg.name)}" if ok_scaled else None},
    ]
    count_note = f" ({len(group)} lignes concernées)" if len(group) > 1 else ""
    desc = (f"Marge personnalisée à vérifier{count_note} — à {hit['start']}, "
            f"style {hit['style']} : \"{hit['text']}\"")
    choice = yield ("margin", desc, choices)
    
    # Enregistrer le choix pour les prochaines fois
    margin_decisions[margin_key] = choice
    
    if choice == 1:
        for h in group:
            set_event_line_margins(out_ass, h["line_index"], scaled_ml, scaled_mr, scaled_mv)
    # choix 0 (ou par défaut) : on ne touche à rien, marge d'origine conservée


def convert_srt_to_ass(srt_path, ass_path):
    """Convertit un .srt en .ass via ffmpeg (minutage, texte, gras/italique
    de base). Le style est ensuite entièrement écrasé par patch_ass_style,
    donc peu importe le rendu par défaut de ffmpeg ici."""
    r = run(["ffmpeg", "-y", "-i", str(srt_path), str(ass_path)])
    return r.returncode == 0 and Path(ass_path).exists()


def is_two_person_line(style_name, text):
    # Vérifier si le style CONTIENT un mot-clé (pas égalité exacte)
    style_lower = style_name.strip().lower()
    for hint in DIALOGUE_STYLE_HINTS:
        if hint in style_lower:
            return True
    
    clean = re.sub(r"\{[^}]*\}", "", text)
    parts = re.split(r"\\N|\\n", clean)
    # Accepter les tirets typographiques (–, —) pas juste "-"
    dash_parts = [p for p in parts if p.strip() and p.strip()[0] in "-–—"]
    return len(dash_parts) >= 2

def normalize_event_margins(ass_path):
    text = Path(ass_path).read_text(encoding="utf-8-sig", errors="replace")
    lines = text.splitlines()
    out = []
    in_events = False
    fmt_fields = None
    for line in lines:
        stripped = line.strip()

        if stripped.startswith("["):
            in_events = stripped.lower() == "[events]"
            fmt_fields = None
            out.append(line)
            continue

        if in_events and stripped.lower().startswith("format:"):
            fmt_fields = [f.strip().lower() for f in stripped[len("format:"):].split(",")]
            out.append(line)
            continue

        if in_events and fmt_fields and line.startswith("Dialogue:"):
            rest = line[len("Dialogue:"):]
            parts = rest.split(",", len(fmt_fields) - 1)
            if len(parts) == len(fmt_fields):
                row = dict(zip(fmt_fields, parts))
                style_name = row.get("style", "").strip()
                text_field = row.get("text", "")
                if is_two_person_line(style_name, text_field):
                    for key in ("marginl", "marginr", "marginv"):
                        if key in row:
                            row[key] = "0"
                    line = "Dialogue:" + ",".join(row[f] for f in fmt_fields)
        out.append(line)
    Path(ass_path).write_text("\n".join(out), encoding="utf-8")

def _format_audio_channels(n):
    mapping = {1: "1.0", 2: "2.0", 3: "2.1", 6: "5.1", 7: "6.1", 8: "7.1"}
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "?"
    return mapping.get(n, f"{n}.0" if n else "?")


def get_audio_track_label(lang_label, track, bitrate=0, channels=0, profile=""):
    codec = (track.get("codec") or "?").upper()
    parts = [codec, _format_audio_channels(channels)]
    if bitrate and bitrate > 0:
        parts.append(f"~{round(bitrate / 1000)} kbps")
    return f"{lang_label} ({' '.join(parts)})"


def _record_candidate(record, track_id):
    if not record:
        return {}
    for c in record.get("candidates", []):
        if c.get("id") == track_id:
            return c
    return {}


def pick_best_audio_gen(path, tracks_with_ffidx, lang_label):
    ranked = []
    for track, ffidx in tracks_with_ffidx:
        bitrate, channels, profile = audio_quality_score(path, track, ffidx)
        is_default = 1 if track["properties"].get("default_track") else 0
        is_lc = 1 if profile.upper() == "LC" else 0
        ranked.append({
            "track": track, "bitrate": bitrate, "channels": channels,
            "profile": profile, "is_default": bool(is_default),
            "rank": (bitrate, is_default, is_lc, channels),
        })

    candidates = [{"id": r["track"]["id"], "channels": r["channels"], "bitrate": r["bitrate"],
                   "profile": r["profile"], "default": r["is_default"]} for r in ranked]

    if len(ranked) == 1:
        return ranked[0]["track"], {"lang": lang_label, "auto": True, "reason": "unique", "candidates": candidates}

    ranked.sort(key=lambda r: r["rank"], reverse=True)
    if ranked[0]["rank"] > ranked[1]["rank"]:
        chosen = ranked[0]["track"]
        return chosen, {"lang": lang_label, "auto": True, "reason": "heuristique (défaut/qualité)",
                         "candidates": candidates, "chosen_id": chosen["id"]}

    options = []
    for r in ranked:
        name = r["track"]["properties"].get("track_name") or "(sans nom)"
        flag = " [défaut]" if r["is_default"] else ""
        options.append(
            f'Piste {r["track"]["id"]} — {r["channels"]} canaux — {r["profile"] or "?"} — '
            f'~{r["bitrate"]} bps{flag} — "{name}"'
        )
    choice = yield ("audio", lang_label, options)
    if choice is None or choice >= len(ranked):
        choice = 0
    chosen = ranked[choice]["track"]
    return chosen, {"lang": lang_label, "auto": False, "candidates": candidates, "chosen_id": chosen["id"]}

SUBTITLE_CODECS_ASS = {"substationalpha", "ssa/ass", "ass", "ssa"}
SUBTITLE_CODECS_SRT = {"subrip/srt", "subrip", "srt"}


def is_srt_codec(codec):
    codec = (codec or "").lower()
    return any(k in codec for k in ("subrip", "srt"))


UNDETERMINED_LANGS = {None, "", "und", "undetermined", "mis", "zxx"}


SIDECAR_SUB_SUFFIXES = [".fr.ass", ".fre.ass", ".fra.ass", ".fr.srt", ".fre.srt", ".fra.srt", ".ass", ".srt"]


def find_sidecar_subtitle(path: Path):
    """Cherche un sous-titre externe à côté de la vidéo (fichier.fr.srt,
    fichier.ass, etc.) — courant sur les releases mp4 gérées par
    Sonarr/Bazarr, où le sous-titre n'est jamais intégré au conteneur."""
    for suf in SIDECAR_SUB_SUFFIXES:
        candidate = path.with_name(path.stem + suf)
        if candidate.exists():
            return candidate
    return None


def compare_subtitle_sizes(mkv_path, track_id_1, track_id_2):
    """V2.0 : Compare la taille de deux pistes extraites.
    Retourne (heavier_id, lighter_id) — la plus lourde = full, la plus légère = forced.

    CORRECTIF v2.9 (Boruto/NoName, épisode 168 — classement inversé
    systématiquement malgré le fix v2.8) : la commande mkvextract utilisait
    la syntaxe invalide "tracks=<id>:<sortie>" (le "tracks=" collé n'existe
    pas dans la CLI mkvextract — la bonne syntaxe, déjà utilisée ailleurs
    dans ce fichier à extract_subtitle_track(), est "mkvextract tracks
    <source> <id>:<sortie>"). L'extraction échouait donc SILENCIEUSEMENT
    (capture_output=True, check=False avalait l'erreur) : les deux fichiers
    de sortie n'étaient jamais créés, les deux tailles valaient 0, et
    "0 >= 0" étant toujours vrai, track_id_1 (le plus petit numéro de piste)
    gagnait à chaque fois le statut "full" — indépendamment du
    contenu réel des pistes. Fix : syntaxe mkvextract corrigée, et une
    exception est levée si l'une des deux extractions échoue réellement
    (plutôt que de comparer deux tailles à 0 et deviner un résultat faux),
    pour que l'appelant garde alors le classement d'origine au lieu d'un
    résultat silencieusement erroné.
    """
    import tempfile
    temp_dir = tempfile.mkdtemp()

    try:
        file_1 = Path(temp_dir) / "sub_1.ass"
        file_2 = Path(temp_dir) / "sub_2.ass"

        # Extraire les deux pistes (syntaxe : mkvextract tracks <source> <id>:<sortie>)
        subprocess.run(
            ["mkvextract", "tracks", str(mkv_path), f"{track_id_1}:{file_1}"],
            capture_output=True, timeout=30, check=False
        )
        subprocess.run(
            ["mkvextract", "tracks", str(mkv_path), f"{track_id_2}:{file_2}"],
            capture_output=True, timeout=30, check=False
        )

        if not file_1.exists() or not file_2.exists():
            raise RuntimeError(
                f"Échec d'extraction mkvextract pour comparaison de poids "
                f"(piste {track_id_1} ou {track_id_2} introuvable après extraction)."
            )

        # Comparer les tailles
        size_1 = file_1.stat().st_size
        size_2 = file_2.stat().st_size

        # Retourner le plus lourd (full) et le plus léger (forced)
        return (track_id_1, track_id_2) if size_1 >= size_2 else (track_id_2, track_id_1)

    finally:
        # Nettoyer les fichiers temporaires
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def _extract_subtitle_size(mkv_path, track_id):
    """V3.8 : extrait une piste de sous-titres dans un dossier temporaire
    et retourne sa taille en octets (0 si l'extraction échoue). Utilisé
    pour la vérification de poids full/forcée par _sanity_check_full_forced().
    """
    import tempfile
    temp_dir = tempfile.mkdtemp()
    try:
        out_file = Path(temp_dir) / "sub.ass"
        subprocess.run(
            ["mkvextract", "tracks", str(mkv_path), f"{track_id}:{out_file}"],
            capture_output=True, timeout=30, check=False
        )
        return out_file.stat().st_size if out_file.exists() else 0
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def _sanity_check_full_forced(mkv_path, full_track, forced_track):
    """V3.8 : (Dragon Ball S01E07, fansub DragonMax) certaines releases
    déclarent leurs métadonnées mkv (nom de piste "FR Full"/"FR Forced" ET
    flag forced_track) DANS LE MAUVAIS SENS — le conteneur lui-même ment,
    donc aucune heuristique basée sur le nom ou le flag ne peut le détecter
    (resolve_ambiguous_subs_by_weight() ne s'applique elle qu'aux pistes
    de MÊME nom, ce qui n'est pas le cas ici : les deux noms sont explicites
    mais inversés).

    Une piste "forcée" ne traduit par définition que quelques lignes
    (panneaux, dialogue en langue étrangère) — elle doit donc TOUJOURS être
    nettement plus légère que la piste complète, qui couvre tout
    l'épisode. Si la piste choisie comme "forcée" s'avère, une fois
    extraite, notablement plus lourde que celle choisie comme "full", les
    deux sont interverties. Marge de 20% pour ignorer les écarts mineurs
    sans signification.
    """
    if not full_track or not forced_track or full_track["id"] == forced_track["id"]:
        return full_track, forced_track, False
    try:
        size_full = _extract_subtitle_size(mkv_path, full_track["id"])
        size_forced = _extract_subtitle_size(mkv_path, forced_track["id"])
        if size_full and size_forced > size_full * 1.2:
            return forced_track, full_track, True
    except Exception:
        pass
    return full_track, forced_track, False


def resolve_ambiguous_subs_by_weight(mkv_path, sub_tracks):
    """V2.0 : Résout les ambiguïtés "French/French" (ou deux pistes SANS
    AUCUN nom, ex: fansub NoName) en comparant le poids.
    Modifie sub_tracks in-place pour marquer la plus lourde comme full.

    CORRECTIFS v2.8 (Boruto/NoName, épisode 168 — classement inversé à
    chaque fois) :
    (1) La condition `count >= 2 and name` excluait explicitement le cas
        où les DEUX pistes n'ont AUCUN nom (name == "" est falsy en
        Python) — c'est-à-dire précisément le cas "aucune indication du
        tout" que cette fonction devait couvrir en priorité (fansubs
        comme NoName qui ne nomment jamais leurs pistes). Fix : `name`
        retiré de la condition, un nom vide compte comme "même nom".
    (2) Même quand la résolution se déclenchait, elle ne renommait que
        track_name — jamais le flag forced_track du conteneur mkv. Or
        _is_forced() dans pick_subtitles_gen() vérifie CE FLAG en
        premier, avant même de regarder le nom : si le fansub l'avait
        mal positionné (mauvais étiquetage, déjà vu sur Boruto/LSCO en
        v2.4), la correction par poids était donc silencieusement
        écrasée par le flag d'origine. Fix : le flag forced_track est
        maintenant réécrit explicitement en cohérence avec le poids.
    """
    if not mkv_path.exists() or not sub_tracks:
        return sub_tracks

    # Grouper les pistes FR par nom
    fr_subs = [t for t in sub_tracks if t["properties"].get("language") == "fre"]
    if len(fr_subs) < 2:
        return sub_tracks

    # Chercher des pistes avec le même nom (une absence de nom des DEUX
    # côtés compte comme "même nom" — c'est le cas NoName)
    names_count = {}
    for t in fr_subs:
        name = (t["properties"].get("track_name") or "").strip().lower()
        names_count[name] = names_count.get(name, 0) + 1

    # Si on a des doublons de noms (ex: deux "french", ou deux pistes sans
    # nom), les résoudre par poids
    for name, count in names_count.items():
        if count >= 2:  # Deux ou plus avec le même nom (y compris vide)
            matching = [t for t in fr_subs if (t["properties"].get("track_name") or "").strip().lower() == name]
            if len(matching) == 2:
                # Comparer par poids
                try:
                    full_id, forced_id = compare_subtitle_sizes(mkv_path, matching[0]["id"], matching[1]["id"])
                    label = name if name else "Français"
                    # Mettre à jour les noms ET le flag forced_track pour
                    # que la décision par poids soit respectée par
                    # _is_forced(), qui vérifie le flag en priorité.
                    for t in sub_tracks:
                        if t["id"] == full_id:
                            t["properties"]["track_name"] = f"{label} (Full)"
                            t["properties"]["forced_track"] = False
                        elif t["id"] == forced_id:
                            t["properties"]["track_name"] = f"{label} (Forced)"
                            t["properties"]["forced_track"] = True
                except Exception:
                    pass  # Si ça échoue, continuer sans modification

    return sub_tracks


def pick_subtitles_gen(sub_tracks, mkv_path=None):
    def is_ass_or_srt(t):
        return t["codec"].lower() in SUBTITLE_CODECS_ASS or is_srt_codec(t["codec"])

    fr_subs = [t for t in sub_tracks
               if t["properties"].get("language") in LANGS_FRE and is_ass_or_srt(t)]

    used_fallback = False
    if not fr_subs:
        # Aucune piste taguée FR : on retente avec les pistes sans langue
        # identifiée (très courant sur les fansubs mal étiquetés).
        undetermined = [t for t in sub_tracks
                         if t["properties"].get("language") in UNDETERMINED_LANGS and is_ass_or_srt(t)]
        if undetermined:
            fr_subs = undetermined
            used_fallback = True

    if not fr_subs:
        # V3.9 (Dragon Ball S04E01, Sonarr/DBP) : certaines releases taguent
        # carrément la piste de sous-titres avec la langue de l'AUDIO
        # ("Language: Japanese", titre "Sous-titre pour Japonais" — un texte
        # FRANÇAIS décrivant "le sous-titre accompagnant la piste japonaise",
        # pas une piste en langue japonaise). Ni LANGS_FRE ni
        # UNDETERMINED_LANGS ne la couvrent, donc le fichier entier était
        # traité comme "sans sous-titres FR" alors qu'une piste ASS/SRT
        # existe bel et bien. Si le fichier ne contient QU'UNE SEULE piste
        # de sous-titres exploitable au total (quelle que soit sa langue
        # déclarée), il n'y a de toute façon rien d'autre à confondre avec
        # un sous-titre français : on la prend telle quelle.
        single_sub = [t for t in sub_tracks if is_ass_or_srt(t)]
        if len(single_sub) == 1:
            fr_subs = single_sub
            used_fallback = True

    if not fr_subs:
        return None, None, {"auto": True, "candidates": []}

    def _is_forced(t):
        if t["properties"].get("forced_track"):
            return True
        name = (t["properties"].get("track_name") or "").lower()
        # Accepte : forcé(e)(s), forcer (infinitif), forced (anglais), subforced, vf
        return bool(re.search(r"\b(?:forc[ée]e?s?|forcer|forced)\b|subforced|\bvf\b", name))

    forced = [t for t in fr_subs if _is_forced(t)]
    full = [t for t in fr_subs if t not in forced]

    # Re-classer les pistes dont le nom indique clairement qu'elles sont full
    # même si elles sont marquées forced_track dans le mkv
    full_keywords = ["complet", "intégral", "principal", "full", "vostfr"]
    for t in list(forced):  # Itérer sur une copie
        tname = (t["properties"].get("track_name") or "").lower()
        if any(k in tname for k in full_keywords):
            forced.remove(t)
            full.append(t)

    # CORRECTIF : une piste FORCÉE seule (sans piste complète à côté) n'a
    # aucun sens — une piste "forcée" accompagne toujours une piste complète.
    # Si c'est la SEULE piste de sous-titres du fichier entier, c'est donc
    # forcément la piste complète, quel que soit son flag forced_track ou
    # son nom (mauvais étiquetage du fansub, ex: Boruto/LSCO).
    if len(sub_tracks) == 1 and forced and not full:
        full = forced
        forced = []

    candidates = [{"id": t["id"], "forced": t in forced,
                   "name": t["properties"].get("track_name") or "",
                   "language_undetermined": used_fallback} for t in fr_subs]

    full_filtered = [t for t in full if not _matches_any_keyword(
        t["properties"].get("track_name"), SUB_DEPRIORITIZED_KEYWORDS)]
    if full_filtered:
        full = full_filtered

    # V3.10 (Dragon Ball Kai S02E01, Mirolo) : le même sous-titre est
    # parfois inclus en double dans le conteneur, une fois en SRT et une
    # fois en ASS (même contenu, ex: "French - SRT - KAZE" / "French - ASS
    # - KAZE", 284 événements chacune) — sans aucune piste forcée à côté.
    # Le style personnalisé de l'appli ne s'applique de toute façon qu'à
    # de l'ASS (un SRT est systématiquement converti en ASS avant tout
    # traitement), donc une piste ASS native est TOUJOURS préférée à un
    # doublon SRT plutôt que de redemander à chaque épisode — le SRT
    # redondant est simplement écarté. Même logique appliquée côté
    # "forcée" si le même doublon s'y présentait un jour.
    for group in (full, forced):
        ass_only = [t for t in group if t["codec"].lower() in SUBTITLE_CODECS_ASS]
        if ass_only and len(ass_only) < len(group):
            group[:] = ass_only

    # Si la langue n'était pas confirmée, on ne se fie pas à l'automatique
    # même s'il n'y a qu'un seul candidat — sauf si c'est carrément la
    # seule piste de sous-titres du fichier (rien d'autre à confondre).
    only_sub_track_in_file = len(sub_tracks) == len(fr_subs)
    skip_auto = used_fallback and not only_sub_track_in_file

    if len(full) <= 1 and len(forced) <= 1 and not skip_auto:
        f, fo = (full[0] if full else None), (forced[0] if forced else None)
        f, fo, swapped = _sanity_check_full_forced(mkv_path, f, fo)
        rec = {"auto": True, "candidates": candidates}
        if swapped:
            rec["weight_swap"] = True
        return f, fo, rec

    note = None
    if used_fallback:
        note = "Aucune piste marquée FR — voici celles sans langue identifiée."

    options = []
    for t in fr_subs:
        name = t["properties"].get("track_name") or "(sans nom)"
        flag = "forcée" if _is_forced(t) else "normale"
        lang = t["properties"].get("language") or "?"
        options.append(f'Piste {t["id"]} — {flag} — langue "{lang}" — "{name}"')

    # === DÉTECTION AUTOMATIQUE : chercher des mots-clés dans les noms de pistes ===
    # Patterns courants pour les pistes "full" : "Complet", "Intégral", "Principal", etc.
    # Patterns courants pour les pistes "forced" : "Forcer", "Forcées", "Signs", etc.
    
    full_track = None
    forced_track = None
    
    # Chercher automatiquement une piste "full" avec "Complet" ou "Intégral" dans le nom
    for t in full:
        tname = (t["properties"].get("track_name") or "").lower()
        if any(k in tname for k in ["complet", "intégral", "principal", "full", "vostfr"]):
            full_track = t
            break
    
    # Si pas trouvé, prendre la première piste "full"
    if not full_track and full:
        full_track = full[0]
    
    # Chercher automatiquement une piste "forced" avec "Forcer" ou "Signs" dans le nom
    for t in forced:
        tname = (t["properties"].get("track_name") or "").lower()
        if any(k in tname for k in ["forcer", "forcée", "forced", "signs", "fr forcer", "subforced"]):
            forced_track = t
            break
    
    # Si pas trouvé, prendre la première piste "forced"
    if not forced_track and forced:
        forced_track = forced[0]
    
    # Si on a réussi à déterminer automatiquement les deux pistes, ne pas demander
    if full_track and forced_track:
        full_track, forced_track, swapped = _sanity_check_full_forced(mkv_path, full_track, forced_track)
        rec = {
            "auto": True, "candidates": candidates,
            "chosen_full_id": full_track["id"],
            "chosen_forced_id": forced_track["id"],
        }
        if swapped:
            rec["weight_swap"] = True
        return full_track, forced_track, rec

    # Sinon, demander confirmation manuelle
    idx_full = yield ("sub_full", note, options)
    full_track = fr_subs[idx_full] if idx_full is not None and idx_full < len(fr_subs) else None

    idx_forced = yield ("sub_forced", note, options)
    forced_track = fr_subs[idx_forced] if idx_forced is not None and idx_forced < len(fr_subs) else None

    return full_track, forced_track, {
        "auto": False, "candidates": candidates,
        "chosen_full_id": full_track["id"] if full_track else None,
        "chosen_forced_id": forced_track["id"] if forced_track else None,
    }

def log_decision(path, status, summary=None, message=""):
    try:
        record = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "file": path.name,
            "status": status,
            "message": message,
            "summary": summary,
        }
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _skip_missing_required_font(path: Path, scan_root, req_font):
    """Une police OBLIGATOIRE (Arial/Trebuchet Bold) reste introuvable même
    après la boucle d'upload : au lieu de produire silencieusement un
    fichier de sortie incomplet, on déplace le fichier ORIGINAL (non
    traité) vers PENDING_REVIEW_DIR, en conservant la structure de
    sous-dossiers (Série/Saison) relative à scan_root pour éviter toute
    collision de nom (v2.7)."""
    try:
        PENDING_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        if scan_root:
            try:
                rel = path.relative_to(scan_root)
            except ValueError:
                rel = Path(path.name)
        else:
            rel = Path(path.name)
        dest = PENDING_REVIEW_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
        yield ("skipped_font", req_font, str(dest))
    except Exception as e:
        yield (
            "warn",
            f"⚠ Police obligatoire {req_font} introuvable, ET échec du déplacement "
            f"vers '{PENDING_REVIEW_DIR.name}' : {e}. Fichier laissé en place, NON traité.",
            None,
        )


# ==========================================================================
# V3.12 : automatisme Sonarr — surveillance du/des root folder(s) manga,
# traitement 100% automatique (aucune interface web), remplacement en place.
# ==========================================================================

def _load_sonarr_state():
    try:
        return json.loads(SONARR_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_sonarr_state(state):
    try:
        SONARR_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        SONARR_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _move_to_sonarr_review(path: Path, watch_root, reason: str):
    """Met de côté un fichier que le pipeline automatique ne peut pas
    traiter sans décision humaine (sous-titre full/forcé ambigu, marge
    ambiguë non résolue...) — même principe que _skip_missing_required_font,
    mais dans un dossier séparé (SONARR_REVIEW_DIR) puisqu'il s'agit d'un
    pipeline différent (watcher automatique, pas la session web)."""
    try:
        SONARR_REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        try:
            rel = path.relative_to(watch_root)
        except ValueError:
            rel = Path(path.name)
        dest = SONARR_REVIEW_DIR / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(dest))
        return dest
    except Exception:
        return None


def auto_process_file(path: Path, tmpdir: Path, watch_root):
    """Fait tourner process_file_gen() de bout en bout SANS interface web,
    en répondant automatiquement aux décisions à faible risque et en
    mettant le fichier de côté (+ notif Telegram) dès qu'une décision à
    fort impact visuel serait nécessaire, plutôt que de deviner :

    - "audio" : pick_best_audio_gen() ne demande déjà que lorsque les
      pistes candidates sont d'ÉGALE qualité (bitrate/canaux/défaut) —
      prendre la première ne risque donc pas de sélectionner une piste de
      moins bonne qualité, juste une piste équivalente parmi plusieurs.
    - "margin" : conserver la marge d'origine (choix "garder telle quelle",
      historiquement celui retenu manuellement dans l'immense majorité des
      cas observés).
    - "missing_font" : personne pour uploader une police manuellement ici —
      répondre None laisse le pipeline standard gérer l'absence (déjà géré :
      avertissement simple si la police n'est qu'optionnelle, mise de côté
      + notif Telegram automatique si elle est obligatoire, v2.7).
    - "sub_full"/"sub_forced" : ambiguïté réelle de contenu — mis de côté
      dans SONARR_REVIEW_DIR, jamais deviné.

    Si le traitement aboutit, le fichier produit dans "FICHIER OK" remplace
    l'ORIGINAL en place (même chemin, même nom) via os.replace() — sûr même
    avec les hardlinks qBittorrent/Sonarr déjà en place : ça ne fait que
    changer où pointe cette entrée de dossier précise, jamais les données
    seedées ailleurs. Retourne (status, message, final_path) avec status
    parmi "done", "review", "error" — final_path (v3.17) est le chemin
    RÉEL du fichier après un éventuel renommage Sonarr déclenché en fin de
    traitement (None si inconnu/inchangé), pour que l'appelant sauvegarde
    l'état "déjà traité" sous le bon nom et ne reprenne pas le fichier
    renommé pour un fichier neuf au prochain passage du watcher."""
    # v3.23 : apply_extra_sub_lang=False — la piste sous-titre supplémentaire
    # (ex: coréen) n'est voulue que ponctuellement, jamais sur tout le flux
    # automatique Sonarr d'une série ; le traitement de base (FR) reste inchangé.
    AUTO_OUT_DIR.mkdir(parents=True, exist_ok=True)
    gen = process_file_gen(path, tmpdir, mirror_root=None, scan_root=None, apply_extra_sub_lang=False, output_dir=AUTO_OUT_DIR)
    send_value = None
    notes = []
    while True:
        try:
            item = gen.send(send_value)
        except StopIteration:
            return "error", "Fin de traitement inattendue (générateur terminé sans résultat).", None
        except Exception as e:
            return "error", f"Erreur pendant le traitement : {e}", None
        send_value = None
        kind = item[0]

        if kind == "audio":
            notes.append(f"piste audio ({item[1]}) ambiguë entre pistes équivalentes, 1ère retenue")
            send_value = 0
        elif kind == "margin":
            send_value = 0
        elif kind == "missing_font":
            send_value = None
        elif kind in ("sub_full", "sub_forced"):
            dest = _move_to_sonarr_review(path, watch_root, "sous-titre ambigu")
            msg = f"Sous-titre full/forcé ambigu, aucune détection automatique fiable — mis de côté{f' : {dest}' if dest else ' (échec du déplacement, fichier laissé en place)'}."
            try:
                gen.close()
            except Exception:
                pass
            return "review", msg, None
        elif kind == "skipped_font":
            # Déjà déplacé vers PENDING_REVIEW_DIR par _skip_missing_required_font.
            return "review", f"Police obligatoire manquante ({item[1]}), fichier mis de côté.", None
        elif kind == "error":
            return "error", item[1], None
        elif kind == "done":
            produced = AUTO_OUT_DIR / (path.stem + ".mkv")
            if not produced.exists():
                return "error", "Fichier traité introuvable après remux (chemin inattendu).", None
            try:
                os.replace(str(produced), str(path))
            except Exception as e:
                return "error", f"Échec du remplacement en place du fichier original : {e}", None
            # v3.15 : le nom de fichier imposé par Sonarr peut contenir l'ordre
            # des langues audio (ex: [FR+JA]) — désormais périmé après le
            # remux. On demande à Sonarr de rescanner puis renommer lui-même
            # (best-effort, ne fait jamais échouer le "done" ci-dessous).
            # v3.17 : on récupère le chemin final réel pour que l'état du
            # watcher ne pointe jamais vers un chemin qui n'existe plus.
            final_path = trigger_sonarr_rescan_and_rename(path)
            return "done", "; ".join(notes) if notes else "traité sans intervention", final_path
        # "info" / "warn" : déjà journalisés par log_decision côté pipeline
        # standard, ignorés ici puisqu'il n'y a pas d'interface à mettre à jour.


def _iter_mkv_files(root):
    """v3.29 : parcourt récursivement `root` à la recherche de fichiers
    .mkv, de façon RÉSILIENTE aux dossiers qui disparaissent EN COURS DE
    SCAN (ex: Sonarr renomme/déplace un dossier de série pendant que le
    watcher le parcourt) — contrairement à Path.rglob(), dont le
    générateur interne laisse remonter une FileNotFoundError non
    récupérable dans ce cas précis (observé en prod : "Smoking Behind the
    Supermarket with You" disparu entre deux appels os.scandir() internes
    → crash complet du process watcher, plus aucune notification Telegram
    envoyée, jusqu'au prochain déclenchement cron). os.walk(onerror=...)
    avale l'erreur et continue avec les dossiers suivants."""
    for dirpath, dirnames, filenames in os.walk(root, onerror=lambda e: None):
        for name in filenames:
            if name.lower().endswith(".mkv"):
                yield Path(dirpath) / name


def _sonarr_find_stable_new_files(watch_dirs, state, excluded_series=None):
    """Parcourt les dossiers surveillés et retourne les .mkv qui : (1) ne
    sont pas déjà connus dans l'état sauvegardé avec le même mtime (déjà
    traités sans avoir été retouchés depuis), (2) sont stables depuis au
    moins SONARR_STABLE_SECONDS (pour ne jamais toucher un import Sonarr
    encore en cours d'écriture), et (3) n'appartiennent pas à une série
    exclue (V3.14 — même liste EXCLUDED_SERIES_PATH que l'interface web,
    ex: séries dont le style personnalisé n'est délibérément PAS voulu,
    comme One Piece)."""
    if excluded_series is None:
        excluded_series = load_excluded_series()
    now = time.time()
    candidates = []
    state_changed = False
    for watch_dir in watch_dirs:
        if not watch_dir.exists():
            continue
        for f in _iter_mkv_files(watch_dir):
            try:
                st = f.stat()
            except OSError:
                continue
            key = str(f)
            if state.get(key) == st.st_mtime:
                continue  # déjà traité, inchangé depuis
            if now - st.st_mtime < SONARR_STABLE_SECONDS:
                continue  # probablement encore en cours d'import par Sonarr
            if extract_series_name(f) in excluded_series:
                continue  # série explicitement exclue (style perso à conserver)
            # v3.24 : mtime changé (ex: remplacement manuel par l'utilisateur
            # après vérification visuelle) ne veut pas forcément dire
            # "fichier neuf" — si le marqueur mouflanimexer est déjà présent,
            # c'est un fichier DÉJÀ traité (peu importe par qui/comment) :
            # on l'enregistre sous son mtime actuel et on ne le retraite pas.
            if is_already_processed(f):
                state[key] = st.st_mtime
                state_changed = True
                continue
            candidates.append(f)
    if state_changed and not candidates:
        # Si on retraite aussi des candidats réels, c'est l'appelant
        # (run_sonarr_watch_once) qui sauvegardera l'état complet à la fin —
        # mais s'il n'y a QUE des fichiers marqueur-skippés, personne d'autre
        # ne sauvegarderait cette mise à jour (l'appelant s'arrête tôt sur
        # une liste de candidats vide).
        _save_sonarr_state(state)
    return candidates


def cli_list_series_in(watch_dirs):
    """`--list-series` : affiche le nom EXACT (tel que reconnu par
    extract_series_name) de chaque série présente dans SONARR_WATCH_DIRS,
    pour savoir quoi passer à --exclude-series sans se tromper (une série
    avec des sous-dossiers de saison peut apparaître comme "Nom / S01",
    "Nom / S02", etc. — chacune doit être exclue séparément)."""
    names = set()
    for watch_dir in watch_dirs:
        if not watch_dir.exists():
            continue
        for f in _iter_mkv_files(watch_dir):
            names.add(extract_series_name(f))
    excluded = load_excluded_series()
    for name in sorted(names):
        marker = " [EXCLUE]" if name in excluded else ""
        print(f"  {name}{marker}")
    if not names:
        print("  (aucun fichier .mkv trouvé)")


def cli_set_series_excluded(series_name, exclude):
    """`--exclude-series "Nom"` / `--include-series "Nom"` : ajoute ou
    retire une série de la liste d'exclusion PARTAGÉE entre l'interface
    web et le watcher Sonarr (EXCLUDED_SERIES_PATH), sans lancer aucun
    traitement — utile pour bloquer une série au style personnalisé
    délibérément conservé (ex: One Piece) sans passer par le bouton
    "Démarrer" de l'interface web."""
    excluded = load_excluded_series()
    if exclude:
        excluded.add(series_name)
    else:
        excluded.discard(series_name)
    save_excluded_series(excluded)
    state = "exclue du traitement (interface web ET watcher Sonarr)" if exclude else "de nouveau incluse"
    print(f"'{series_name}' est maintenant {state}.")


def cli_set_extra_sub_lang(series_name, lang_code, add):
    """(v3.19) `--add-extra-sub-lang "Nom" <code>` / `--remove-extra-sub-
    lang "Nom" <code>` : ajoute ou retire un code langue (ISO 639-2, ex:
    "kor") à la liste des sous-titres supplémentaires à CONSERVER pour
    cette série, en plus de la piste FR traitée normalement. Partagé entre
    l'interface web manuelle et le watcher Sonarr (même clé que
    EXCLUDED_SERIES_PATH : nom exact renvoyé par extract_series_name())."""
    mapping = load_extra_sub_lang()
    lang_code = lang_code.strip().lower()
    langs = set(mapping.get(series_name, []))
    if add:
        langs.add(lang_code)
    else:
        langs.discard(lang_code)
    if langs:
        mapping[series_name] = sorted(langs)
    else:
        mapping.pop(series_name, None)
    save_extra_sub_lang(mapping)
    if add:
        print(f"'{series_name}' : la piste de sous-titres '{lang_code}' sera désormais conservée en plus du FR.")
    else:
        print(f"'{series_name}' : la piste '{lang_code}' n'est plus conservée automatiquement (langues restantes : {sorted(langs) or 'aucune'}).")


def seed_sonarr_state():
    """Commande ponctuelle à lancer UNE FOIS avant d'activer le cron du
    watcher (`python3 mouflanimexer.py --seed-sonarr-state`) : enregistre
    le mtime de TOUS les .mkv déjà présents dans SONARR_WATCH_DIRS comme
    "déjà connus", SANS les toucher ni les traiter. Sans cette étape, le
    premier passage du watcher croirait que tout le catalogue existant est
    "nouveau" et tenterait de tout retraiter d'un coup."""
    state = _load_sonarr_state()
    count = 0
    for watch_dir in SONARR_WATCH_DIRS:
        if not watch_dir.exists():
            print(f"[!] Dossier introuvable, ignoré : {watch_dir}")
            continue
        for f in _iter_mkv_files(watch_dir):
            try:
                state[str(f)] = f.stat().st_mtime
                count += 1
            except OSError:
                continue
    _save_sonarr_state(state)
    print(f"{count} fichier(s) existant(s) marqué(s) comme déjà connus (non traités). "
          f"Le watcher ne s'occupera désormais que des nouveaux épisodes.")


SONARR_FAIL_PATH = SONARR_STATE_PATH.with_name("sonarr_watch_failures.json")
WATCH_LOCK_PATH = SONARR_STATE_PATH.with_name("sonarr_watch.lock")


def _load_failures():
    try:
        data = json.loads(SONARR_FAIL_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_failures(data):
    try:
        SONARR_FAIL_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def run_sonarr_watch_once():
    """Point d'entrée du watcher (appelé via cron : `python3 mouflanimexer.py
    --watch-sonarr`). Traite tous les fichiers stables et nouveaux trouvés
    dans SONARR_WATCH_DIRS, puis s'arrête (ne tourne pas en tâche de fond —
    c'est cron qui fixe la fréquence).
    v3.32 : un seul passage à la fois (verrou) ; un fichier en échec n'est
    retenté qu'après un délai croissant (30 min, 1 h, 2 h… 24 h max) et
    n'envoie qu'UNE notification, au lieu d'être retraité toutes les 2 minutes."""
    import fcntl
    try:
        WATCH_LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
        lock_file = open(WATCH_LOCK_PATH, "w")
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return          # le passage précédent travaille encore : on le laisse finir
    except OSError:
        lock_file = None
    missing = [d for d in SONARR_WATCH_DIRS if not d.exists()]
    if not SONARR_WATCH_DIRS or len(missing) == len(SONARR_WATCH_DIRS):
        return          # partage réseau non monté : rien à faire (et surtout rien à créer en local)
    state = _load_sonarr_state()
    failures = _load_failures()
    now = time.time()
    files = []
    for f in _sonarr_find_stable_new_files(SONARR_WATCH_DIRS, state):
        fail = failures.get(str(f))
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if fail and fail.get("mtime") == mtime and now < fail.get("next", 0):
            continue    # déjà en échec, pas encore l'heure de réessayer
        files.append(f)
    if not files:
        _save_sonarr_state(state)      # fichiers reconnus « déjà traités » pendant le parcours : on les retient
        return

    tmpdir = Path(tempfile.mkdtemp(prefix="mouflanimexer_sonarr_"))
    try:
        def _is_under(child, parent):
            try:
                child.relative_to(parent)
                return True
            except ValueError:
                return False

        for f in files:
            watch_root = next((d for d in SONARR_WATCH_DIRS if _is_under(f, d)), f.parent)
            log_decision(f, "sonarr_watch_start", message=f"Détecté par le watcher Sonarr : {f}")
            try:
                status, message, final_path = auto_process_file(f, tmpdir, watch_root)
            except Exception as e:
                status, message, final_path = "error", f"Exception inattendue : {e}", None

            if status == "done":
                # v3.17 : si Sonarr a renommé le fichier (RenameSeries),
                # final_path pointe vers son nom RÉEL actuel — on enregistre
                # l'état sous CE chemin, sinon le fichier renommé ne serait
                # plus reconnu comme "déjà traité" au prochain passage et
                # serait repris pour un fichier neuf (boucle de retraitement
                # inutile, potentiellement dangereuse).
                tracked_path = final_path if final_path is not None else f
                try:
                    state[str(tracked_path)] = tracked_path.stat().st_mtime
                except OSError:
                    pass
                if final_path is not None and final_path != f:
                    # L'ancien chemin n'existe plus (renommé) : on l'enlève
                    # de l'état s'il y traînait d'un passage précédent, pour
                    # ne pas laisser d'entrée morte s'accumuler.
                    state.pop(str(f), None)
                log_decision(f, "sonarr_watch_done", message=message)
                failures.pop(str(f), None)
            elif status == "review":
                log_decision(f, "sonarr_watch_review", message=message)
            else:
                log_decision(f, "sonarr_watch_error", message=message)

            notify = True
            if status != "done" and f.exists():        # toujours là (échec, ou mise de côté impossible) : on espace les essais
                prev = failures.get(str(f)) or {}
                try:
                    mtime = f.stat().st_mtime
                except OSError:
                    mtime = None
                n = (prev.get("n", 0) + 1) if prev.get("mtime") == mtime else 1
                failures[str(f)] = {"mtime": mtime, "n": n, "next": time.time() + min(30 * 60 * 2 ** (n - 1), 24 * 3600), "message": message}
                notify = n == 1                         # une seule notification par fichier en échec
            _save_failures(failures)

            # v3.25 : notification Telegram immédiate par fichier (succès,
            # mis de côté, ou erreur) — on utilise le nom final (post-
            # renommage Sonarr) quand il est connu, sinon le nom détecté.
            if notify:
                notify_sonarr_result(final_path if (status == "done" and final_path is not None) else f, status, message)
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    _save_sonarr_state(state)


def process_file_gen(path: Path, tmpdir: Path, mirror_root=None, scan_root=None, apply_extra_sub_lang=True, output_dir=None):
    """v3.32 : chaque fichier a son propre dossier temporaire (polices, sous-titres), effacé à la fin :
    une police extraite d'un épisode ne peut plus faire croire qu'elle est présente dans le suivant."""
    file_tmp = Path(tempfile.mkdtemp(prefix="fichier_", dir=str(tmpdir)))
    try:
        result = yield from _process_file_gen(path, file_tmp, mirror_root, scan_root, apply_extra_sub_lang, output_dir)
        return result
    finally:
        shutil.rmtree(file_tmp, ignore_errors=True)


def _process_file_gen(path: Path, tmpdir: Path, mirror_root=None, scan_root=None, apply_extra_sub_lang=True, output_dir=None):
    yield ("info", f"Début du traitement de : {path.name}")
    info = mkvmerge_json(path)
    
    # Mémoriser les marges déjà validées dans cette série pour éviter re-demander
    margin_decisions = {}  # key: (marginl, marginr, marginv) → value: choice (0=keep, 1=resize)
    
    audio_tracks, sub_tracks, jpn, fre, chi = classify_tracks(info)
    
    # Accepter les fichiers avec au moins une piste japonaise, française OU chinoise
    if not jpn and not fre and not chi:
        msg = "Aucune piste audio valide (ni japonaise, ni française, ni chinoise)."
        log_decision(path, "error", message=msg)
        yield ("error", msg)
        return

    best_jpn, rec_jpn = (None, None)
    if jpn:
        best_jpn, rec_jpn = yield from pick_best_audio_gen(path, jpn, "japonais")
        
    best_fre, rec_fre = (None, None)
    if fre:
        best_fre, rec_fre = yield from pick_best_audio_gen(path, fre, "français")
    
    best_chi, rec_chi = (None, None)
    if chi:
        best_chi, rec_chi = yield from pick_best_audio_gen(path, chi, "chinois")

    # V2.0 : Résoudre les ambiguïtés (ex: deux "French") par poids avant pick_subtitles_gen
    sub_tracks = resolve_ambiguous_subs_by_weight(path, sub_tracks)
    
    full_sub, forced_sub, rec_sub = yield from pick_subtitles_gen(sub_tracks, path)
    if rec_sub.get("weight_swap"):
        yield ("info", "⚠ Métadonnées full/forcée incohérentes avec le contenu réel (piste 'forcée' plus lourde que la piste 'full') — pistes interverties automatiquement.")
    if not full_sub:
        sidecar = find_sidecar_subtitle(path)
        if sidecar:
            yield ("info", f"Aucun sous-titre FR dans le conteneur — piste externe trouvée : {sidecar.name}")
            full_sub = {
                "id": None, "codec": "ass" if sidecar.suffix.lower() == ".ass" else "SubRip/SRT",
                "properties": {"track_name": "", "forced_track": False, "language": "fre"},
                "_sidecar_path": sidecar,
            }
        else:
            yield ("info", "Attention : aucun sous-titre FR trouvé (ni dans le fichier, ni en externe), le fichier sera remuxé sans sous-titres.")
    
    anime_name = extract_series_name(path)

    # v3.19/v3.20 : exception par série — conserver une ou plusieurs
    # pistes de sous-titres d'une autre langue que le français (ex:
    # coréen), en plus de la piste FR traitée normalement ci-dessus.
    # v3.20 : ces pistes passent maintenant par le MÊME traitement que la
    # piste FR (extraction, lecture de SA PROPRE résolution/marges
    # d'origine, patch de style, polices) au lieu d'être copiées brutes
    # depuis la source — nécessaire pour un cas comme celui-ci : piste
    # coréenne où l'utilisateur a lui-même ajouté le FR en \an8 (en haut)
    # par-dessus le coréen (en bas) pour regarder à deux, et qui doit donc
    # être recalée/stylée comme n'importe quel autre sous-titre.
    # v3.23 : apply_extra_sub_lang=False (watcher Sonarr automatique
    # uniquement) désactive complètement cette exception — besoin
    # seulement ponctuel (ex: un épisode précis regardé avec sa femme),
    # jamais voulu sur tout le flux automatique d'une série entière.
    extra_sub_lang_codes = set(load_extra_sub_lang().get(anime_name, [])) if apply_extra_sub_lang else set()
    extra_sub_tracks = [t for t in sub_tracks if t["properties"].get("language") in extra_sub_lang_codes] \
        if extra_sub_lang_codes else []
    if extra_sub_tracks:
        found_codes = sorted({t["properties"].get("language") for t in extra_sub_tracks})
        yield ("info", f"Piste(s) de sous-titres supplémentaire(s) conservée(s) et traitée(s) pour cette série : {', '.join(found_codes)}.")

    LANGUAGE_DISPLAY_NAMES = {
        "kor": "Coréen", "eng": "Anglais", "chi": "Chinois", "jpn": "Japonais",
        "ger": "Allemand", "spa": "Espagnol", "ita": "Italien", "por": "Portugais",
        "rus": "Russe", "ara": "Arabe", "vie": "Vietnamien", "tha": "Thaï",
    }

    if mirror_root and scan_root:
        try:
            rel = path.relative_to(scan_root)
        except ValueError:
            rel = Path(path.name)
        # Le mode miroir reproduit tel quel l'arborescence du dossier scanné
        # (rel.parent contient déjà "Série/Saison") — ne PAS y rajouter
        # anime_name par-dessus, sinon la structure série/saison se retrouve
        # dupliquée (ex: .../Boruto/S1/Boruto/S1/...)
        output_dir = mirror_root / rel.parent
    elif output_dir is None:
        output_dir = OK_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / (path.stem + ".mkv")

    sub_paths = {}
    ass_target_dir = series_path(ASS_DIR, anime_name)
    ass_target_dir.mkdir(parents=True, exist_ok=True)

    # v3.20 : les pistes supplémentaires (extra_sub_tracks) passent par
    # EXACTEMENT la même boucle de traitement que "full"/"forced" — label
    # préfixé "extra::<code_langue>" pour les distinguer au moment de
    # construire la commande mkvmerge finale, plus bas.
    extra_sub_entries = [(f"extra::{t['properties'].get('language', '')}", t) for t in extra_sub_tracks]

    for label, t in [("full", full_sub), ("forced", forced_sub)] + extra_sub_entries:
        if t is None:
            continue

        orig_ass = tmpdir / f"{path.stem}_{label}_original.ass"
        saved_orig_ass = ass_target_dir / f"{path.stem}_{label}_original.ass"

        if saved_orig_ass.exists():
            yield ("info", f"Utilisation du sous-titre brut original sauvegardé : {saved_orig_ass.name}")
            shutil.copy(saved_orig_ass, orig_ass)
        elif t.get("_sidecar_path"):
            sidecar = t["_sidecar_path"]
            if sidecar.suffix.lower() == ".ass":
                shutil.copy(sidecar, orig_ass)
            else:
                yield ("info", f"Piste {label} externe au format SRT — conversion en ASS avec le style personnalisé...")
                if not convert_srt_to_ass(sidecar, orig_ass):
                    yield ("warn", f"⚠ Échec de la conversion SRT->ASS pour la piste externe {label}, ignorée.", None)
                    continue
            shutil.copy(orig_ass, saved_orig_ass)
        elif is_srt_codec(t.get("codec")):
            yield ("info", f"Piste {label} au format SRT détectée — conversion en ASS avec le style personnalisé...")
            orig_srt = tmpdir / f"{path.stem}_{label}_original.srt"
            try:
                extract_subtitle(path, t["id"], orig_srt)
            except RuntimeError as e:
                yield ("warn", f"⚠ Échec d'extraction de la piste {label} : {e}", None)
                continue
            if not convert_srt_to_ass(orig_srt, orig_ass):
                yield ("warn", f"⚠ Échec de la conversion SRT->ASS pour la piste {label}, ignorée.", None)
                continue
            shutil.copy(orig_ass, saved_orig_ass)
        else:
            try:
                extract_subtitle(path, t["id"], orig_ass)
            except RuntimeError as e:
                yield ("warn", f"⚠ Échec d'extraction de la piste {label} : {e}", None)
                continue
            shutil.copy(orig_ass, saved_orig_ass)

        out_ass = tmpdir / f"{path.stem}_{label}.ass"
        shutil.copy(orig_ass, out_ass)

        declared_res = read_play_res(out_ass)
        true_res = get_true_orig_res(out_ass, declared_res)
        if true_res != declared_res:
            yield ("info", f"⚠ Faux {declared_res[0]}x{declared_res[1]} détecté. Forçage de l'échelle depuis {true_res[0]}x{true_res[1]}")
        else:
            yield ("info", f"Résolution d'origine validée : {true_res[0]}x{true_res[1]}")

        sx = (TARGET_PLAYRES[0] / true_res[0]) if TARGET_PLAYRES and true_res[0] else 1.0
        sy = (TARGET_PLAYRES[1] / true_res[1]) if TARGET_PLAYRES and true_res[1] else 1.0

        # Vérifier les marges AVANT patch_ass_style (qui modifie PlayResX)
        if true_res != TARGET_PLAYRES:
            margin_hits = find_custom_margin_lines(out_ass, true_res)
            margin_groups = {}
            for h in margin_hits:
                key = (h["marginl"], h["marginr"], h["marginv"])
                margin_groups.setdefault(key, []).append(h)
            for group in margin_groups.values():
                yield from pick_margin_choice_gen(path, out_ass, group, sx, sy, margin_decisions)
        # si true_res == TARGET_PLAYRES, sx=sy=1 : "garder" et "redimensionner"
        # donneraient exactement la même valeur, la question n'a pas de sens.

        scale_positioning_tags(out_ass, true_res, TARGET_PLAYRES)
        # v3.28 : pour une piste "extra::<lang>" (ex: coréen), un fichier
        # .ass bilingue peut soit donner à la langue supplémentaire un
        # style ENTIÈREMENT dédié ("pur", ex: "Default -kor" — jamais
        # utilisé pour du FR), soit RÉUTILISER le même style pour le FR
        # ajouté en \an8 ET la langue d'origine, sans \fn par ligne pour
        # les distinguer ("mixte", ex: "Default" partagé entre FR et
        # coréen sur Smoking Behind the Supermarket with You S01E07).
        # detect_extra_lang_style_usage() distingue les deux par le
        # CONTENU réel des lignes (pas le nom du style) :
        #  - un style "pur" est exempté du style FR (STYLE_PROFILES) et
        #    reçoit la police universelle sur TOUT le style (comme v3.26).
        #  - un style "mixte" GARDE son style FR habituel (ses lignes FR
        #    en dépendent), et seules les lignes contenant réellement
        #    l'alphabet voulu reçoivent la police universelle EN LIGNE
        #    (force_inline_font_for_script_lines), sans toucher au Style.
        if label.startswith("extra::"):
            lang_code = label.split("::", 1)[1]
            pure_lang_styles, mixed_lang_styles = detect_extra_lang_style_usage(out_ass, lang_code)
        else:
            lang_code = None
            pure_lang_styles, mixed_lang_styles = set(), set()
        patch_ass_style(out_ass, true_res, apply_style_profiles=True, skip_profile_styles=pure_lang_styles)
        if pure_lang_styles:
            # v3.22 : police d'origine potentiellement incapable d'afficher
            # l'alphabet de la piste (ex: "Trebuchet MS" sans glyphes
            # coréens) → forcée vers une police à large couverture Unicode,
            # automatiquement, sans dépendre d'une correction du .ass
            # source — v3.26 : uniquement sur le(s) style(s) vraiment
            # concerné(s), jamais sur les styles FR du même fichier.
            force_style_fontname(out_ass, EXTRA_SUB_UNIVERSAL_FONT, only_styles=pure_lang_styles)
        if mixed_lang_styles:
            force_inline_font_for_script_lines(out_ass, EXTRA_SUB_UNIVERSAL_FONT, lang_code, mixed_lang_styles)
        normalize_event_margins(out_ass)

        sub_paths[label] = out_ass

        for hit in detect_blur_lines(out_ass):
            msg = (f"✓ Flou préservé ({label}, style {hit['style']}, à {hit['start']}) : "
                   f"{hit['tags']}")
            # Plus de preview du flou (simplifié) — juste un log discret
            yield ("info", msg)

        current_mod_file = ass_target_dir / f"{path.stem}_{label}_modifie.ass"
        shutil.copy(out_ass, current_mod_file)

    font_paths = []
    attachments = info.get("attachments", [])
    if attachments:
        yield ("info", f"{len(attachments)} pièce(s) jointe(s) détectée(s), analyse des polices...")
        fonts_dir = tmpdir / "fonts"
        fonts_dir.mkdir(exist_ok=True)
        for att in attachments:
            fname = att.get("file_name", "")
            if any(fname.lower().endswith(ext) for ext in (".ttf", ".otf")):
                safe_name = Path(fname.replace("\\", "/")).name      # v3.32 : jamais de chemin dans un nom de pièce jointe (« ../x.ttf »)
                if not safe_name or safe_name in (".", ".."):
                    continue
                font_out = fonts_dir / safe_name
                r_font = run(["mkvextract", "attachments", str(path), f"{att['id']}:{font_out}"])
                if r_font.returncode == 0 and font_out.exists():
                    font_paths.append(font_out)
                    # Constitue une bibliothèque locale : toute police pas
                    # encore connue est copiée pour être réutilisable plus tard.
                    if not find_font_file(font_out.stem, [REFERENCE_FONTS_DIR]):
                        try:
                            shutil.copy(font_out, REFERENCE_FONTS_DIR / font_out.name)
                            yield ("info", f"Police '{font_out.name}' inconnue ajoutée à la bibliothèque locale.")
                        except Exception:
                            pass

    # Polices imposées directement sur une ligne (\fn) : à compléter
    # depuis la bibliothèque locale si elles manquent, ou à signaler.
    inline_fonts = set()
    for label, p in sub_paths.items():
        inline_fonts |= detect_inline_fonts(p)
        # v3.21 : une piste "extra::<lang>" (ex: coréen) ne passe plus par
        # STYLE_PROFILES (apply_style_profiles=False) — sa police d'origine
        # (déclarée au niveau du Style, pas forcément en \fn) doit donc
        # aussi être vérifiée/embarquée, sinon tofu/carrés au visionnage.
        if label.startswith("extra::"):
            inline_fonts |= detect_style_fonts(p)

    for font_name in sorted(inline_fonts):
        if find_font_file(font_name, [tmpdir / "fonts"]):
            continue  # déjà embarquée dans ce fichier
        ref_match = find_font_file(font_name, [REFERENCE_FONTS_DIR])
        if ref_match and not any(_normalize_font_key(font_name) in _normalize_font_key(f.stem) for f in font_paths):
            yield ("info", f"Police en ligne '{font_name}' absente du fichier, ajoutée depuis la bibliothèque locale.")
            font_paths.append(ref_match)
        elif not ref_match:
            uploaded = yield from wait_for_font_upload(font_name, [REFERENCE_FONTS_DIR])
            if uploaded:
                # Vérifier que la police est trouvable via find_font_file (boucle jusqu'au succès)
                final_font = find_font_file(font_name, [REFERENCE_FONTS_DIR])
                if final_font:
                    font_paths.append(final_font)
                    yield ("info", f"Police '{font_name}' ajoutée manuellement, poursuite du traitement.")
                else:
                    yield ("warn", f"⚠ Police en ligne '{font_name}' uploadée mais pas trouvable, ignorée.", None)
            else:
                yield ("warn", f"⚠ Police en ligne '{font_name}' toujours introuvable, ignorée.", None)

    required_fonts = ["ArialBold.ttf", "TrebuchetMSBold.ttf", "TrebuchetMSBoldItalic.ttf"]

    for req_font in required_fonts:
        already_present = any(req_font.lower() in f.name.lower() for f in font_paths)
        if not already_present:
            ref_path = REFERENCE_FONTS_DIR / req_font
            if ref_path.exists():
                yield ("info", f"Police manquante détectée ({req_font}), ajout depuis le LXC...")
                font_paths.append(ref_path)
            else:
                uploaded = yield from wait_for_font_upload(req_font, [REFERENCE_FONTS_DIR])
                if uploaded:
                    # Vérifier que la police est trouvable via find_font_file
                    final_font = find_font_file(req_font, [REFERENCE_FONTS_DIR])
                    if final_font:
                        font_paths.append(final_font)
                        yield ("info", f"Police obligatoire '{req_font}' ajoutée manuellement, poursuite du traitement.")
                    else:
                        yield from _skip_missing_required_font(path, scan_root, req_font)
                        return
                else:
                    yield from _skip_missing_required_font(path, scan_root, req_font)
                    return

    part_file = out_file.with_name(f"{out_file.stem}.partiel-{os.getpid()}.mkv")    # v3.32 : écrit à côté, vérifié, puis renommé
    args = ["mkvmerge", "-o", str(part_file)]
    
    # V3.6 : la piste "langue d'origine" (celle placée en premier et
    # marquée par défaut) était toujours le japonais s'il existait, sinon
    # PERSONNE — un fichier sans piste jpn (donghua/manhua chinois, ex:
    # seulement chi+fre) se retrouvait donc avec le français en première
    # position et AUCUNE piste par défaut. La piste chinoise est
    # maintenant traitée comme le japonais : "originale", donc placée en
    # premier et par défaut dès lors qu'il n'y a pas de japonais.
    if best_jpn:
        original_audio = best_jpn
    elif best_chi:
        original_audio = best_chi
    else:
        original_audio = None
    default_audio_id = original_audio["id"] if original_audio else (best_fre["id"] if best_fre else None)

    # Ordre : langue d'origine en premier (jpn, ou chi à défaut), puis fre,
    # puis chi restant si jpn était la langue d'origine.
    audio_ids = []
    if original_audio is not None:
        audio_ids.append(str(original_audio["id"]))
    if best_fre:
        audio_ids.append(str(best_fre["id"]))
    if best_chi and original_audio is not best_chi:
        audio_ids.append(str(best_chi["id"]))

    if audio_ids:
        args += ["-a", ",".join(audio_ids)]
        if best_jpn:
            c = _record_candidate(rec_jpn, best_jpn["id"])
            label_jpn = get_audio_track_label("Japanese", best_jpn, c.get("bitrate", 0), c.get("channels", 0), c.get("profile", ""))
            args += ["--track-name", f'{best_jpn["id"]}:{label_jpn}']
            args += ["--default-track", f'{best_jpn["id"]}:{"yes" if best_jpn["id"] == default_audio_id else "no"}']
        if best_fre:
            c = _record_candidate(rec_fre, best_fre["id"])
            label_fre = get_audio_track_label("French", best_fre, c.get("bitrate", 0), c.get("channels", 0), c.get("profile", ""))
            args += ["--track-name", f'{best_fre["id"]}:{label_fre}']
            args += ["--default-track", f'{best_fre["id"]}:{"yes" if best_fre["id"] == default_audio_id else "no"}']
        if best_chi:
            c = _record_candidate(rec_chi, best_chi["id"])
            label_chi = get_audio_track_label("Chinese", best_chi, c.get("bitrate", 0), c.get("channels", 0), c.get("profile", ""))
            args += ["--track-name", f'{best_chi["id"]}:{label_chi}']
            args += ["--default-track", f'{best_chi["id"]}:{"yes" if best_chi["id"] == default_audio_id else "no"}']

    # v3.20 : toutes les pistes de sous-titres de la source sont exclues
    # (-S) — la piste FR ET les éventuelles pistes supplémentaires (ex:
    # coréen) sont désormais TOUTES extraites, traitées (résolution,
    # marges, style, polices) et réinjectées comme fichiers ASS externes
    # ci-dessous, jamais copiées brutes depuis la source.
    args += ["-S", str(path)]

    if "full" in sub_paths:
        args += ["--language", "0:fre", "--track-name", "0:French",
                 "--default-track", "0:yes", "--forced-track", "0:no", str(sub_paths["full"])]
    if "forced" in sub_paths:
        args += ["--language", "0:fre", "--track-name", "0:French forced",
                 "--default-track", "0:no", "--forced-track", "0:yes", str(sub_paths["forced"])]
    for label, out_ass in sub_paths.items():
        if not label.startswith("extra::"):
            continue
        lang_code = label.split("::", 1)[1] or "und"
        display_name = LANGUAGE_DISPLAY_NAMES.get(lang_code, lang_code.upper())
        args += ["--language", f"0:{lang_code}", "--track-name", f"0:{display_name}",
                 "--default-track", "0:no", "--forced-track", "0:no", str(out_ass)]

    for fpath in font_paths:
        args += ["--attachment-name", fpath.name, "--attachment-mime-type", "application/x-truetype-font", "--attach-file", str(fpath)]

    # v3.24 : marqueur invisible posé sur CHAQUE fichier produit (manuel ET
    # automatique) — voir is_already_processed() / MOUFLANIMEXER_MARKER_NAME.
    marker_path = tmpdir / MOUFLANIMEXER_MARKER_NAME
    marker_path.write_text(APP_VERSION, encoding="utf-8")
    args += ["--attachment-name", MOUFLANIMEXER_MARKER_NAME, "--attachment-mime-type", "text/plain", "--attach-file", str(marker_path)]

    video_tracks = [t for t in info["tracks"] if t["type"] == "video"]
    track_order_items = []
    for v in video_tracks:
        track_order_items.append(f"0:{v['id']}")
    
    if not track_order_items:
        track_order_items = ["0:0"]

    if original_audio is not None:
        track_order_items.append(f"0:{original_audio['id']}")
    if best_fre:
        track_order_items.append(f"0:{best_fre['id']}")
    if best_chi and original_audio is not best_chi:
        track_order_items.append(f"0:{best_chi['id']}")
        
    ext_track_idx = 1
    if "full" in sub_paths:
        track_order_items.append(f"{ext_track_idx}:0")
        ext_track_idx += 1
    if "forced" in sub_paths:
        track_order_items.append(f"{ext_track_idx}:0")
        ext_track_idx += 1

    # v3.20 : pistes de sous-titres supplémentaires (ex: coréen) — chacune
    # est son propre fichier ASS externe traité, exactement comme "full"/
    # "forced" ci-dessus, donc même logique d'incrémentation d'index.
    for label in sub_paths:
        if label.startswith("extra::"):
            track_order_items.append(f"{ext_track_idx}:0")
            ext_track_idx += 1

    args += ["--track-order", ",".join(track_order_items)]

    yield ("info", "Lancement du remux mkvmerge vers FICHIER OK...")
    try:
        r = run(args)
        if r.returncode != 0:
            raise RuntimeError(f"Le remux final a échoué : {r.stderr}")
        problem = verify_remux(info, part_file)
        if problem:
            raise RuntimeError(f"Fichier produit incorrect, l'original n'est pas touché : {problem}")
        os.replace(part_file, out_file)
    finally:
        if part_file.exists():
            try:
                part_file.unlink()
            except OSError:
                pass

    summary = {"subtitles": rec_sub}
    if rec_jpn:
        summary["audio_jpn"] = rec_jpn
    if rec_fre:
        summary["audio_fre"] = rec_fre
    if rec_chi:
        summary["audio_chi"] = rec_chi
    log_decision(path, "done", summary=summary, message=f"Fichier créé avec succès : {out_file.name}")
    yield ("done", f"Fichier créé : {out_file.name}")

STATE = {
    "folder": DEFAULT_FOLDER,
    "recursive": False,
    "files": [],
    "series_map": {},
    "excluded_series": set(),
    "queue": [],
    "idx": 0,
    "gen": None,
    "tmpdir": None,
    "log": _LoggedList(),
    "pending": None,
    "is_running": False,
    "stop_requested": False,
    "pause_requested": False,
    "paused": False,
    "send_value": None,
    "mirror_mode": False,
    "mirror_dest": None,
    "mirror_synced": False,
    "skipped_font_files": [],
}

def worker_loop():
    if STATE["mirror_mode"] and not STATE["mirror_synced"]:
        STATE["log"].append({"text": "Synchronisation du dossier miroir (fichiers annexes)...", "alert": False})
        try:
            # v3.18 : ne synchroniser que les dossiers de PREMIER NIVEAU qui
            # contiennent au moins un fichier réellement en file (donc une
            # série cochée) — avant, toutes les séries présentes dans le
            # dossier scanné étaient parcourues, cochées ou non.
            folder = Path(STATE["folder"])
            only_top_dirs = set()
            for f in STATE["queue"]:
                try:
                    rel = f.relative_to(folder)
                except ValueError:
                    continue
                if rel.parts:
                    only_top_dirs.add(rel.parts[0])
            sync_mirror_tree(folder, STATE["mirror_dest"],
                              lambda t: STATE["log"].append({"text": t, "alert": False}),
                              only_top_dirs=only_top_dirs)
        except Exception as e:
            STATE["log"].append({"text": f"⚠ Erreur synchronisation miroir : {e}", "alert": True})
        STATE["mirror_synced"] = True

    while STATE["is_running"]:
        if STATE["stop_requested"]:
            STATE["log"].append({"text": "⏹ Traitement arrêté par l'utilisateur.", "alert": True})
            STATE["is_running"] = False
            STATE["stop_requested"] = False
            STATE["paused"] = False
            STATE["gen"] = None
            STATE["pending"] = None
            return
        if STATE["pause_requested"]:
            STATE["log"].append({"text": "⏸ Traitement mis en pause.", "alert": False})
            STATE["is_running"] = False
            STATE["pause_requested"] = False
            STATE["paused"] = True
            return  # gen/idx/queue restent intacts pour pouvoir reprendre
        if STATE["gen"] is None:
            if STATE["idx"] >= len(STATE["queue"]):
                if STATE["skipped_font_files"]:
                    lines = [
                        f"⚠️ {len(STATE['skipped_font_files'])} fichier(s) zappé(s) — "
                        f"police(s) obligatoire(s) manquante(s) :"
                    ]
                    for entry in STATE["skipped_font_files"]:
                        lines.append(f"   • {entry['file']} ({entry['font']})")
                    summary_text = "\n".join(lines)
                    STATE["log"].append({"text": summary_text, "alert": True})
                    send_telegram_notification(f"MouFlanimeXer\n{summary_text}")
                    STATE["skipped_font_files"] = []
                STATE["is_running"] = False
                STATE["pending"] = None
                return
            path = STATE["queue"][STATE["idx"]]
            STATE["log"].append({"text": f"=== {path.name} ===", "alert": False})
            mirror_root = STATE["mirror_dest"] if STATE["mirror_mode"] else None
            scan_root = Path(STATE["folder"]) if STATE["mirror_mode"] else None
            STATE["gen"] = process_file_gen(path, STATE["tmpdir"], mirror_root=mirror_root, scan_root=scan_root)
        
        try:
            item = STATE["gen"].send(STATE["send_value"])
            STATE["send_value"] = None
        except StopIteration:
            item = ("error", "Fin de traitement inattendue.")
        except Exception as e:
            item = ("error", f"Erreur : {e}")

        kind = item[0]
        if kind in ("audio", "sub_full", "sub_forced", "margin", "missing_font"):
            if kind == "audio":
                q_text = f"⚠ Intervention nécessaire — plusieurs pistes audio en {item[1]}"
            elif kind == "margin":
                q_text = f"⚠ Intervention nécessaire — {item[1]}"
            elif kind == "missing_font":
                q_text = f"⚠ Police manquante — {item[1]}"
            else:
                label = "COMPLÈTE" if kind == "sub_full" else "FORCÉE"
                q_text = f"⚠ Intervention nécessaire — sous-titre {label} ambigu"
                if item[1]:
                    q_text += f" ({item[1]})"
            STATE["log"].append({"text": q_text, "alert": True})
            STATE["pending"] = item
            STATE["is_running"] = False
            return
        elif kind == "info":
            STATE["log"].append({"text": item[1], "alert": False})
        elif kind == "warn":
            entry = {"text": item[1], "alert": True}
            if len(item) > 2 and item[2]:
                entry["image"] = item[2]
            STATE["log"].append(entry)
        elif kind == "skipped_font":
            req_font = item[1]
            current_path = STATE["queue"][STATE["idx"]]
            STATE["log"].append({
                "text": f"⏭ Fichier ZAPPÉ (police obligatoire '{req_font}' manquante) — "
                        f"déplacé vers '{PENDING_REVIEW_DIR.name}', non traité.",
                "alert": True,
            })
            STATE["skipped_font_files"].append({"file": current_path.name, "font": req_font})
            log_decision(current_path, "skipped_missing_font", message=req_font)
            STATE["gen"] = None
            STATE["idx"] += 1
        else:
            text = item[1] if len(item) > 1 else str(item)
            STATE["log"].append({"text": text, "alert": kind == "error"})
            STATE["gen"] = None
            STATE["idx"] += 1

def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not auth.is_logged_in():
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

TEMPLATE = """
<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MouFlanimeXer</title>
<link rel="icon" type="image/svg+xml" href="/icons/mouflanimexer.svg"><link rel="icon" type="image/png" sizes="32x32" href="/icons/favicon-32.png"><link rel="apple-touch-icon" href="/icons/apple-touch-icon.png"><link rel="manifest" href="/icons/manifest.webmanifest"><meta name="theme-color" content="#121315">
<style>
  * { box-sizing: border-box; }
  :root {
    --bg: #fff; --fg: #111; --muted: #888;
    --box-bg: #fff; --box-border: #ccc;
    --input-bg: #fff; --input-fg: #111; --input-border: #ccc;
    --log-bg: #111; --log-fg: #0f0;
    --alert-bg: #fff3f3; --alert-border: #b71c1c; --alert-fg: #b71c1c;
    --thumb-border: #444;
  }
  :root[data-theme="dark"] {
    --bg: #121212; --fg: #e8e8e8; --muted: #999;
    --box-bg: #1e1e1e; --box-border: #3a3a3a;
    --input-bg: #2a2a2a; --input-fg: #eee; --input-border: #444;
    --log-bg: #000; --log-fg: #0f0;
    --alert-bg: #2a1414; --alert-border: #e57373; --alert-fg: #ff8a80;
    --thumb-border: #555;
  }
  body { max-width: 1200px; margin: 0 auto; padding: 16px; }
  a { color: var(--accent); }
  .box { background: var(--card); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
  .box-alert { border: 1px solid var(--alert-border); background: var(--alert-bg); }
  .box-alert b { color: var(--alert-fg); }
  input[type=text] { width: 100%; }
  button { margin: 4px 4px 4px 0; }
  .progress-track { background: var(--field); border-radius: 6px; overflow: hidden; height: 10px; }
  .progress-fill { background: var(--accent); height: 100%; }
  .ok-text { color: var(--accent); font-weight: bold; }
  .warn-text { color: var(--warn); font-weight: bold; }
  input[type=file] { color: var(--muted); max-width: 100%; }
  ul.options { list-style: none; padding: 0; }
  ul.options li { margin: 10px 0; }
  ul.options label { display: block; padding: 6px 0; }
  input[type=radio], input[type=checkbox] { width: 18px; height: 18px; vertical-align: middle; margin-right: 6px; }
  #log { background: var(--log-bg); color: var(--log-fg); padding: 10px; height: 350px; overflow-y: auto;
         font-family: monospace; font-size: 0.85em; border-radius: 6px; white-space: pre-wrap;
         overflow-x: hidden; word-break: break-word; }
  .warn { color: var(--err); font-weight: bold; }
  .preview-thumb { max-width: 160px; width: 100%; display: block; margin-top: 6px; border-radius: 4px; border: 1px solid var(--thumb-border); }
  @media (max-width: 480px) {
    body { padding: 10px; }
    form button { width: 100%; }
  }
</style>
<link rel="stylesheet" href="/ui/mou-ui.css?v={{ version|urlencode }}">
<script src="/ui/mou-ui.js?v={{ version|urlencode }}" defer></script>
</head>
<body>
<div id="mou-header" data-app="mouflanimexer" data-prefix="MouFl" data-rest="animeXer" data-version="v{{ version }}" data-settings="1"
     data-sub="Remux automatique d'animes : pistes audio, sous-titres et polices"></div>

{% if missing_tools %}
<div class="box warn">
  Outils manquants : {{ missing_tools|join(", ") }}.<br>
  Installe-les dans ce conteneur (mkvtoolnix + ffmpeg) puis relance le script.
</div>
{% endif %}

<div class="box">
  <form method="post" action="/scan">
    <label>Dossier à traiter (chemin sur ce serveur) :</label><br>
    <input type="text" name="folder" value="{{ folder }}">
    <label style="display:block; margin-top:8px;">
      <input type="checkbox" name="recursive" {% if recursive %}checked{% endif %}>
      Inclure les sous-dossiers
    </label>
    <label style="display:block; margin-top:8px;">
      <input type="checkbox" name="mirror_mode" {% if mirror_mode %}checked{% endif %}>
      Copier tout le dossier (nfo, images, sous-dossiers...) dans une copie miroir avec les épisodes traités
    </label>
    <p style="font-size:0.8em; color:var(--muted); margin:4px 0 0;">Ne touche jamais le dossier d'origine. Coche aussi "Inclure les sous-dossiers" pour une série avec des dossiers de saison.</p>
    <button class="primary" type="submit">Scanner ce dossier</button>
  </form>
</div>

{% if files %}
<div class="box">
  <b>{{ files|length }} fichier(s) trouvé(s) :</b>
  <ul>{% for f in files %}<li>{{ f }}</li>{% endfor %}</ul>

  {% if series_map %}
  <form method="post" action="/start">
    <b>Séries détectées — décoche celles à ignorer :</b>
    <ul class="options">
    {% for series, count in series_map.items() %}
      <li>
        <label>
          <input type="checkbox" name="series::{{ series }}"
                 {% if series not in excluded_series %}checked{% endif %}>
          {{ series }} ({{ count }} fichier(s))
        </label>
        <span style="margin-left:12px; font-size:0.85em; color:var(--muted);">
          sous-titre(s) suppl. à garder :
          <input type="text" name="extra_sub_lang::{{ series }}" placeholder="ex: kor"
                 value="{{ extra_sub_lang.get(series, [])|join(',') }}"
                 style="width:80px; font-size:0.9em;">
        </span>
      </li>
    {% endfor %}
    </ul>
    {% if not is_running and not pending and not paused %}
    <button class="primary" type="submit">Lancer le traitement</button>
    {% elif is_running %}
    <p class="ok-text">Traitement en cours... (actualisation auto)</p>
    {% elif paused %}
    <p class="warn-text">⏸ En pause.</p>
    {% endif %}
  </form>

  {% if (is_running or pending or paused) and queue_len > 0 %}
  <div style="margin-top:10px;">
    <div style="display:flex; justify-content:space-between; font-size:0.9em; margin-bottom:4px;">
      <span>Fichier {{ [idx + 1, queue_len]|min }} / {{ queue_len }}</span>
      <span>{{ ((idx / queue_len) * 100) | round | int }}%</span>
    </div>
    <div class="progress-track">
      <div class="progress-fill" style="width:{{ ((idx / queue_len) * 100) | round | int }}%;"></div>
    </div>
  </div>
  <div style="display:flex; gap:8px; margin-top:10px;">
    {% if is_running %}
    <form method="post" action="/pause" style="flex:1;">
      <button type="submit" class="warn" style="width:100%;">⏸ Pause</button>
    </form>
    {% elif paused %}
    <form method="post" action="/resume" style="flex:1;">
      <button type="submit" style="width:100%;">▶ Reprendre</button>
    </form>
    {% endif %}
    <form method="post" action="/stop" style="flex:1;">
      <button type="submit" class="danger" style="width:100%;">⏹ Arrêter</button>
    </form>
  </div>
  {% endif %}
  {% endif %}
</div>
{% endif %}

{% if pending %}
<div id="pending-box"></div>
  {% if pending[0] == "audio" %}
  <div class="box box-alert">
    <b>Plusieurs pistes audio en {{ pending[1] }} ont été trouvées. Laquelle garder ?</b>
    <form method="post" action="/decide">
      <ul class="options">
      {% for opt in pending[2] %}
        <li><label><input type="radio" name="choice" value="{{ loop.index0 }}" {% if loop.first %}checked{% endif %}> {{ opt }}</label></li>
      {% endfor %}
      </ul>
      <button class="primary" type="submit">Valider</button>
    </form>
  </div>
  {% elif pending[0] == "sub_full" %}
  <div class="box box-alert">
    <b>Plusieurs sous-titres FR possibles. Laquelle est la piste COMPLÈTE (non forcée) ?</b>
    {% if pending[1] %}<p style="margin:6px 0 0;">{{ pending[1] }}</p>{% endif %}
    <form method="post" action="/decide">
      <ul class="options">
      {% for opt in pending[2] %}
        <li><label><input type="radio" name="choice" value="{{ loop.index0 }}" {% if loop.first %}checked{% endif %}> {{ opt }}</label></li>
      {% endfor %}
        <li><label><input type="radio" name="choice" value="none"> Aucune piste complète</label></li>
      </ul>
      <button class="primary" type="submit">Valider</button>
    </form>
  </div>
  {% elif pending[0] == "sub_forced" %}
  <div class="box box-alert">
    <b>Laquelle est la piste FORCÉE (dialogues étrangers uniquement) ?</b>
    {% if pending[1] %}<p style="margin:6px 0 0;">{{ pending[1] }}</p>{% endif %}
    <form method="post" action="/decide">
      <ul class="options">
      {% for opt in pending[2] %}
        <li><label><input type="radio" name="choice" value="{{ loop.index0 }}" {% if loop.first %}checked{% endif %}> {{ opt }}</label></li>
      {% endfor %}
        <li><label><input type="radio" name="choice" value="none"> Aucune piste forcée</label></li>
      </ul>
      <button class="primary" type="submit">Valider</button>
    </form>
  </div>
  {% elif pending[0] == "margin" %}
  <div class="box box-alert">
    <b>{{ pending[1] }}</b>
    <form method="post" action="/decide">
      <ul class="options">
      {% for opt in pending[2] %}
        <li>
          <label><input type="radio" name="choice" value="{{ loop.index0 }}" {% if loop.first %}checked{% endif %}> {{ opt.label }}</label>
          {% if opt.image %}<a href="{{ opt.image }}" target="_blank"><img class="preview-thumb" src="{{ opt.image }}" alt="aperçu"></a>{% endif %}
        </li>
      {% endfor %}
      </ul>
      <button class="primary" type="submit">Valider</button>
    </form>
  </div>
  {% elif pending[0] == "missing_font" %}
  <div class="box box-alert">
    <b>Police manquante : "{{ pending[1] }}"</b>
    <p style="margin:6px 0 0;">Introuvable dans le fichier et dans la bibliothèque locale. Ajoute le fichier (.ttf/.otf) pour continuer, ou ignore pour remuxer sans elle.</p>
    <form method="post" action="/upload_font" enctype="multipart/form-data" style="margin-top:10px;">
      <input type="file" name="font_file" accept=".ttf,.otf" multiple>
      <div style="display:flex; gap:8px; margin-top:10px;">
        <button class="primary" type="submit" style="flex:1;">Ajouter et continuer</button>
        <button type="submit" name="skip" value="1" class="ghost" style="flex:1;">Ignorer</button>
      </div>
    </form>
  </div>
  {% endif %}
{% endif %}

{% if not is_running and not pending and queue_len > 0 and idx >= queue_len %}
<div class="box" style="border-left:3px solid var(--accent);">
  <b>Traitement terminé.</b>
</div>
{% endif %}

{% if log %}
<div class="box" id="log-box">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:8px;">
    <b>Journal :</b>
    <div>
      <a href="/download_log" target="_blank" class="mou-btn ghost small" style="text-decoration:none;display:inline-block;">Télécharger</a>
      <form method="post" action="/clear_log" style="display:inline;">
        <button type="submit" class="ghost" style="padding:6px 12px;font-size:.85rem;">Effacer l'affichage</button>
      </form>
    </div>
  </div>
  <div id="log">{% for entry in log %}<div{% if entry.alert %} style="color:var(--err);font-weight:bold;"{% endif %}>{{ entry.text }}{% if entry.image %}<br><a href="{{ entry.image }}" target="_blank"><img class="preview-thumb" src="{{ entry.image }}" alt="capture"></a>{% endif %}</div>{% endfor %}</div>
</div>
{% endif %}

<script>
  var logDiv = document.getElementById("log");
  if (logDiv) {
      logDiv.scrollTop = logDiv.scrollHeight;
  }
  {% if is_running or pending %}
  {% if pending %}
  var target = document.getElementById("pending-box");
  {% else %}
  var target = document.getElementById("log-box");
  {% endif %}
  if (target) {
      target.scrollIntoView({block: "start"});
  }
  {% endif %}
  {% if is_running %}
  // actualisation automatique pendant un traitement (suspendue si une fenêtre est ouverte)
  setInterval(function () { if (!(window.MouModalOpen && window.MouModalOpen())) location.reload(); }, 2000);
  {% endif %}
</script>
</body>
</html>
"""

def _natural_sort_key(path):
    """Tri qui comprend les nombres (S01E2 avant S01E10, S01E10 avant
    S01E100) au lieu d'un tri alphabétique pur sur le texte."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", str(path))]


def missing_tools():
    return [t for t in ("mkvmerge", "mkvextract", "ffprobe") if shutil.which(t) is None]

def _already_handled(f: Path, anime_name=None, mirror_root=None, scan_root=None) -> bool:
    if mirror_root and scan_root:
        try:
            rel = f.relative_to(scan_root)
        except ValueError:
            rel = Path(f.name)
        return (mirror_root / rel.parent / (f.stem + ".mkv")).exists()
    return (OK_DIR / (f.stem + ".mkv")).exists()

@app.route("/", methods=["GET"])
@requires_auth
def index():
    return render_template_string(
        TEMPLATE,
        folder=STATE["folder"], recursive=STATE["recursive"], mirror_mode=STATE["mirror_mode"],
        files=[f.name for f in STATE["files"]],
        series_map={k: len(v) for k, v in STATE["series_map"].items()},
        excluded_series=STATE["excluded_series"],
        extra_sub_lang=load_extra_sub_lang(),
        queue_len=len(STATE["queue"]),
        is_running=STATE["is_running"], paused=STATE["paused"],
        idx=STATE["idx"], pending=STATE["pending"], log=STATE["log"],
        missing_tools=missing_tools(), version=APP_VERSION,
    )

@app.route("/preview/<path:filename>")
@requires_auth
def preview(filename):
    return send_from_directory(PREVIEW_DIR, filename)

# ---------------------------------------------------------------------------
# v3.30 : page « Diagnostic » — un rapport complet (état du serveur, des
# outils, des dossiers, journal de la session, décisions récentes, journal
# système du service) à copier-coller d'un clic, sans avoir à se connecter
# au serveur pour chercher les fichiers de log. Les mots de passe, jetons et
# clés d'API sont masqués automatiquement.
# ---------------------------------------------------------------------------
_REDACTIONS = [
    (re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{30,}\b"), "***jeton-telegram***"),
    (re.compile(r"(api[_-]?key[\"'=: ]+)[A-Za-z0-9._-]{8,}", re.I), r"\1***"),
    (re.compile(r"(X-Api-Key[\"'=: ]+)[A-Za-z0-9._-]+", re.I), r"\1***"),
    (re.compile(r"((?:password|passwd|mot_de_passe|token)[\"'=: ]+)[^\s\"'&]+", re.I), r"\1***"),
    (re.compile(r"(bot)\d{6,}:[A-Za-z0-9_-]+", re.I), r"\1***"),
]


def _redact(text):
    for pattern, repl in _REDACTIONS:
        text = pattern.sub(repl, text)
    return text


def _tail_file(path, lines, max_bytes=200_000):
    try:
        path = Path(path)
        size = path.stat().st_size
        with open(path, "rb") as f:
            f.seek(max(0, size - max_bytes))
            data = f.read().decode("utf-8", errors="replace")
        return "\n".join(data.splitlines()[-lines:])
    except OSError:
        return "(aucun fichier pour le moment)"


def _run_cmd(cmd, timeout=8):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return (out.stdout or out.stderr or "").strip()
    except FileNotFoundError:
        return "(commande indisponible)"
    except subprocess.TimeoutExpired:
        return "(délai dépassé)"
    except Exception as e:
        return f"(erreur : {e})"


def _meminfo():
    try:
        info = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            k, v = line.split(":", 1)
            info[k] = int(v.split()[0])
        return f"{info['MemAvailable'] // 1024} Mo libres sur {info['MemTotal'] // 1024} Mo"
    except Exception:
        return "inconnue"


def _disk_info(path):
    try:
        u = shutil.disk_usage(path)
        return f"{u.free / 1e9:.1f} Go libres sur {u.total / 1e9:.0f} Go"
    except OSError as e:
        return f"inaccessible ({e})"


def _path_state(path):
    path = Path(path)
    if not path.exists():
        return "INTROUVABLE"
    rw = "lecture+écriture" if os.access(path, os.W_OK) else "lecture seule"
    return f"OK ({rw})"


def build_diagnostic_report():
    import platform
    now = time.strftime("%d/%m/%Y %H:%M:%S")
    lines = [
        f"=== Rapport MouFlanimeXer · {now} ===",
        f"Version : v{APP_VERSION}",
        f"Python  : {sys.version.split()[0]} · {platform.platform()} · {os.cpu_count()} cœurs",
        f"Mémoire : {_meminfo()}",
        f"Disque  : appli {_disk_info('/opt/mouflanimexer')} · médiathèque {_disk_info(DEFAULT_FOLDER)}",
        "",
        "--- Outils ---",
    ]
    for tool in ("mkvmerge", "mkvextract", "ffprobe"):
        path = shutil.which(tool)
        if path:
            first = (_run_cmd([tool, "--version"], 5).splitlines() or ["?"])[0]
            lines.append(f"{tool} : {first}")
        else:
            lines.append(f"{tool} : MANQUANT")
    lines += [
        "",
        "--- Dossiers ---",
        f"Dossier par défaut : {DEFAULT_FOLDER} → {_path_state(DEFAULT_FOLDER)}",
        f"Journal des décisions : {LOG_PATH.parent} → {_path_state(LOG_PATH.parent)}",
        f"« À traiter (police manquante) » : {_path_state(PENDING_REVIEW_DIR.parent)}",
        f"Bibliothèque de polices : {REFERENCE_FONTS_DIR} → {_path_state(REFERENCE_FONTS_DIR)}"
        f" ({len(list(REFERENCE_FONTS_DIR.glob('*'))) if REFERENCE_FONTS_DIR.exists() else 0} fichiers)",
    ]
    for d in SONARR_WATCH_DIRS:
        lines.append(f"Surveillance Sonarr : {d} → {_path_state(d)}")
    token, chat_id = load_telegram_config()
    lines += [
        f"Telegram : {'configuré' if token and chat_id else 'non configuré'} · Connexion : {'identifiant défini' if auth.configured() else 'AUCUN identifiant défini (bash set-login.sh)'}",
        "",
        "--- État du traitement ---",
        f"En cours : {'oui' if STATE['is_running'] else 'non'} · pause : {'oui' if STATE['paused'] else 'non'}"
        f" · avancement : {STATE['idx']}/{len(STATE['queue'])} · dossier scanné : {STATE['folder']}",
        "",
        "--- Journal affiché dans la page (60 dernières lignes) ---",
        "\n".join(e.get("text", "") for e in STATE["log"][-60:]) or "(vide)",
        "",
        "--- Décisions récentes (journal .jsonl, 40 dernières) ---",
    ]
    for raw in _tail_file(LOG_PATH, 40).splitlines():
        try:
            rec = json.loads(raw)
            lines.append(f"{rec.get('time', '')} [{rec.get('status', '')}] {rec.get('file', '')} — {rec.get('message', '')}")
        except ValueError:
            lines.append(raw)
    watch_log = Path("/opt/mouflanimexer/sonarr_watch.log")
    if watch_log.exists():
        lines += ["", "--- sonarr_watch.log (40 dernières lignes) ---", _tail_file(watch_log, 40)]
    lines += [
        "",
        "--- Journal de l'appli (150 dernières lignes) ---",
        diag.tail(diag.LOG_FILE, 150),
        "",
        "--- Déploiement automatique (40 dernières lignes) ---",
        _tail_file("/var/log/mouflanimexer-deploy.log", 40),
        "",
        "--- Journal système du service (150 dernières lignes, erreurs Python comprises) ---",
        _run_cmd(["journalctl", "-u", "mouflanimexer", "-n", "150", "--no-pager", "-o", "short-iso"]),
    ]
    return _redact("\n".join(lines))


@app.route("/diagnostic")
@requires_auth
def diagnostic():
    return redirect("/")   # le journal s'ouvre maintenant dans la fenêtre « Journal » de la page d'accueil


diag.init_app(app, APP_VERSION, build_diagnostic_report)

import settings_page
settings_page.init_app(
    app, lambda: APP_VERSION, TELEGRAM_CONFIG_PATH, SONARR_API_CONFIG_PATH,
    lambda: [("Fichiers terminés", OK_DIR), ("Copies miroir", MIRROR_ROOT_BASE), ("Sous-titres d'origine", ASS_DIR),
             ("Journal des décisions", LOG_PATH.parent), ("À traiter (police manquante)", PENDING_REVIEW_DIR),
             ("À traiter (intervention manuelle)", SONARR_REVIEW_DIR), ("Aperçus", PREVIEW_DIR),
             ("Bibliothèque de polices", REFERENCE_FONTS_DIR)],
    paths_file=PATHS_FILE, paths_defaults={"work_root": DEFAULT_WORK_ROOT, "sonarr_watch_dirs": DEFAULT_WATCH_DIRS},
    busy_fn=lambda: bool(STATE["is_running"] or STATE["paused"] or STATE["pending"]))


@app.route("/download_log")
@requires_auth
def download_log():
    content = "\n".join(e["text"] for e in STATE["log"])
    ts = time.strftime("%Y%m%d_%H%M%S")
    return Response(
        content, mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename=journal_{ts}.txt"},
    )

@app.route("/clear_log", methods=["POST"])
@requires_auth
def clear_log():
    STATE["log"] = _LoggedList([])
    return redirect(url_for("index"))

_CONTROL_LOCK = threading.Lock()


def _serialized(f):
    """v3.32 : les boutons (scanner, lancer, reprendre, répondre…) passent un par un : un double clic ne lance plus deux traitements."""
    @wraps(f)
    def wrapper(*a, **k):
        with _CONTROL_LOCK:
            return f(*a, **k)
    return wrapper


@app.route("/scan", methods=["POST"])
@requires_auth
@_serialized
def scan():
    if STATE["is_running"]:
        STATE["log"].append({"text": "⚠ Un traitement est en cours : mets-le en pause ou arrête-le avant de scanner un autre dossier.", "alert": True})
        return redirect(url_for("index"))
    folder = request.form.get("folder", "").strip()
    recursive = request.form.get("recursive") == "on"
    mirror_mode = request.form.get("mirror_mode") == "on"
    STATE["folder"] = folder
    STATE["recursive"] = recursive
    STATE["mirror_mode"] = mirror_mode
    STATE["mirror_synced"] = False
    p = Path(folder)
    STATE["mirror_dest"] = (MIRROR_ROOT_BASE / p.name) if mirror_mode else None
    if not p.is_dir():
        STATE["files"] = []
        STATE["series_map"] = {}
        STATE["log"] = _LoggedList([{"text": f"Dossier introuvable : {folder}", "alert": True}])
    else:
        patterns = ["**/*.mkv", "**/*.mp4"] if recursive else ["*.mkv", "*.mp4"]
        found = sorted((f for pat in patterns for f in p.glob(pat)), key=_natural_sort_key)
        
        # EXCLUSION des dossiers système (Synology @eaDir, @tmp, etc.)
        found_filtered = [
            f for f in found
            if not any(part.lower() in SYSTEM_DIRS_EXCLUDED for part in f.parts)
        ]
        
        # LOGS DÉTAILLÉS : afficher chaque fichier trouvé + son chemin
        log_lines = []
        log_lines.append({"text": f"🔍 Scan en cours dans : {folder}", "alert": False})
        log_lines.append({"text": f"   Mode récursif : {'✓ OUI' if recursive else '✗ NON'}", "alert": False})
        if mirror_mode:
            log_lines.append({"text": f"   Mode miroir : ✓ OUI → {STATE['mirror_dest']}", "alert": False})
        log_lines.append({"text": "", "alert": False})
        
        # Résumé des découvertes
        excluded_count = len(found) - len(found_filtered)
        if excluded_count > 0:
            log_lines.append({"text": f"⊘ {excluded_count} fichier(s) dans dossiers système (@eaDir, @tmp, etc.) — ignoré(s)", "alert": False})
            log_lines.append({"text": "", "alert": False})
        
        # Lister les fichiers trouvés avec vérification
        log_lines.append({"text": f"📁 Fichiers valides trouvés ({len(found_filtered)}) :", "alert": False})
        
        checked_files = []
        for f in found_filtered:
            # Vérifier que le fichier existe toujours (les "fantômes" n'existent plus)
            exists_check = "✓" if f.exists() else "✗ DISPARU"
            rel_path = f.relative_to(p) if f.is_relative_to(p) else f
            log_lines.append({"text": f"   {exists_check} {rel_path}", "alert": not f.exists()})
            if f.exists():
                checked_files.append(f)
        
        log_lines.append({"text": "", "alert": False})
        
        # Fichiers qui ont disparu entre le scan et maintenant
        vanished = len(found_filtered) - len(checked_files)
        if vanished > 0:
            log_lines.append({"text": f"⚠ {vanished} fichier(s) ont disparu entre le scan et la vérification !", "alert": True})
            log_lines.append({"text": "", "alert": False})
        
        kept = [f for f in checked_files if not _already_handled(f, extract_series_name(f), STATE["mirror_dest"], p)]
        skipped = len(checked_files) - len(kept)
        STATE["files"] = kept
        
        # Résumé
        log_lines.append({"text": f"✓ {len(kept)} fichier(s) à traiter", "alert": False})
        if skipped:
            log_lines.append({"text": f"⊘ {skipped} fichier(s) déjà traité(s) — ignoré(s)", "alert": False})
        
        log_lines.append({"text": "", "alert": False})
        
        # Groupement par série
        series_map = {}
        for f in kept:
            series_name = extract_series_name(f)
            series_map.setdefault(series_name, []).append(f)
        STATE["series_map"] = series_map
        
        log_lines.append({"text": f"📊 Séries détectées ({len(series_map)}) :", "alert": False})
        for series, files in sorted(series_map.items()):
            log_lines.append({"text": f"   • {series} ({len(files)} fic.)", "alert": False})
        
        STATE["log"] = _LoggedList(log_lines)
    STATE["excluded_series"] = load_excluded_series()
    STATE["queue"] = []
    STATE["idx"] = 0
    STATE["skipped_font_files"] = []
    STATE["gen"] = None
    STATE["pending"] = None
    STATE["is_running"] = False
    STATE["paused"] = False                 # v3.32 : un nouveau scan efface une pause précédente (sinon plus aucun bouton)
    STATE["pause_requested"] = False
    STATE["stop_requested"] = False
    if STATE["tmpdir"] is not None:
        shutil.rmtree(STATE["tmpdir"], ignore_errors=True)
    STATE["tmpdir"] = Path(tempfile.mkdtemp(prefix="mkv_remux_"))
    return redirect(url_for("index"))

@app.route("/upload_font", methods=["POST"])
@requires_auth
@_serialized
def upload_font():
    if STATE["is_running"] or not STATE["pending"] or STATE["pending"][0] != "missing_font":
        return redirect(url_for("index"))

    font_name = STATE["pending"][1]
    files = request.files.getlist("font_file")
    saved_any = False
    if not request.form.get("skip"):
        REFERENCE_FONTS_DIR.mkdir(parents=True, exist_ok=True)
        for file in files:
            if file and file.filename:
                safe_name = re.sub(r"[^A-Za-z0-9_.\-]", "_", Path(file.filename).name)
                if not safe_name.lower().endswith((".ttf", ".otf")) or safe_name.startswith("."):
                    STATE["log"].append({"text": f"⚠ « {file.filename} » ignoré : seules les polices .ttf et .otf sont acceptées.", "alert": True})
                    continue
                file.save(REFERENCE_FONTS_DIR / safe_name)
                STATE["log"].append({"text": f"✓ Police '{safe_name}' ajoutée à la bibliothèque.", "alert": False})
                saved_any = True

    uploaded_path = find_font_file(font_name, [REFERENCE_FONTS_DIR]) if saved_any else None
    if saved_any and not uploaded_path:
        STATE["log"].append({"text": f"Aucun des fichiers envoyés ne correspond à '{font_name}', poursuite sans elle.", "alert": False})
    elif not saved_any:
        STATE["log"].append({"text": "Police ignorée, poursuite sans elle.", "alert": False})

    STATE["send_value"] = uploaded_path
    STATE["pending"] = None
    STATE["is_running"] = True
    threading.Thread(target=worker_loop, daemon=True).start()
    return redirect(url_for("index"))

@app.route("/stop", methods=["POST"])
@requires_auth
@_serialized
def stop():
    if STATE["is_running"]:
        STATE["stop_requested"] = True  # le worker s'arrêtera à la prochaine étape
    else:
        # rien ne tourne activement (en pause sur une question, ou en pause manuelle) : arrêt immédiat
        STATE["pending"] = None
        STATE["gen"] = None
        STATE["paused"] = False
        STATE["idx"] = len(STATE["queue"])
        STATE["log"].append({"text": "⏹ Traitement arrêté par l'utilisateur.", "alert": True})
    return redirect(url_for("index"))

@app.route("/pause", methods=["POST"])
@requires_auth
@_serialized
def pause():
    if STATE["is_running"]:
        STATE["pause_requested"] = True  # le worker se met en pause à la prochaine étape
    return redirect(url_for("index"))

@app.route("/resume", methods=["POST"])
@requires_auth
@_serialized
def resume():
    if STATE["paused"] and not STATE["is_running"]:
        STATE["paused"] = False
        STATE["is_running"] = True
        threading.Thread(target=worker_loop, daemon=True).start()
    return redirect(url_for("index"))

@app.route("/start", methods=["POST"])
@requires_auth
@_serialized
def start():
    if STATE["is_running"]:
        return redirect(url_for("index"))

    excluded = load_excluded_series()
    for series in STATE["series_map"]:
        key = f"series::{series}"
        if request.form.get(key) == "on":
            excluded.discard(series)
        else:
            excluded.add(series)
    save_excluded_series(excluded)
    STATE["excluded_series"] = excluded

    # v3.20 : champ "sous-titre(s) suppl. à garder" par série, saisi
    # directement dans l'interface web (plus besoin de SSH/CLI pour
    # activer l'exception — ex: "kor" pour un anime FR+coréen).
    extra_sub_lang = load_extra_sub_lang()
    for series in STATE["series_map"]:
        raw = (request.form.get(f"extra_sub_lang::{series}") or "").strip().lower()
        codes = sorted({c.strip() for c in raw.split(",") if c.strip()})
        if codes:
            extra_sub_lang[series] = codes
        else:
            extra_sub_lang.pop(series, None)
    save_extra_sub_lang(extra_sub_lang)

    STATE["queue"] = [f for f in STATE["files"] if extract_series_name(f) not in excluded]

    STATE["idx"] = 0
    STATE["log"] = _LoggedList([])
    STATE["gen"] = None
    STATE["pending"] = None
    STATE["send_value"] = None
    STATE["stop_requested"] = False
    STATE["pause_requested"] = False
    STATE["paused"] = False
    STATE["is_running"] = True
    threading.Thread(target=worker_loop, daemon=True).start()
    return redirect(url_for("index"))

@app.route("/decide", methods=["POST"])
@requires_auth
@_serialized
def decide():
    if STATE["is_running"]:
        return redirect(url_for("index"))
    raw = request.form.get("choice")
    try:
        value = None if raw == "none" else int(raw)
    except (TypeError, ValueError):
        return redirect(url_for("index"))          # réponse incomplète : la question reste affichée

    if STATE["pending"]:
        kind = STATE["pending"][0]
        options = STATE["pending"][2] if kind in ("audio", "margin", "sub_full", "sub_forced") else STATE["pending"][1]
        if value is None:
            chosen_label = "aucune"
        elif 0 <= value < len(options):
            opt = options[value]
            chosen_label = opt["label"] if isinstance(opt, dict) else opt
        else:
            chosen_label = "?"
        STATE["log"].append({"text": f"✓ Choix retenu : {chosen_label}", "alert": False})

    STATE["send_value"] = value
    STATE["pending"] = None
    STATE["is_running"] = True
    threading.Thread(target=worker_loop, daemon=True).start()
    return redirect(url_for("index"))

if __name__ == "__main__":
    # V3.12 : mode watcher Sonarr, appelé périodiquement par cron —
    # `python3 mouflanimexer.py --watch-sonarr` — traite les nouveaux
    # fichiers stables puis quitte immédiatement (pas de serveur Flask
    # lancé dans ce mode).
    if "--seed-sonarr-state" in sys.argv:
        seed_sonarr_state()
        sys.exit(0)
    if "--watch-sonarr" in sys.argv:
        # v3.29 : filet de sécurité — toute exception non prévue qui
        # remonte jusqu'ici tuait le process SANS aucune notification
        # Telegram (seule la trace dans sonarr_watch.log en témoignait,
        # invisible jusqu'à ce qu'on aille la lire à la main). On
        # continue de laisser planter le process (comportement cron
        # inchangé), mais on prévient maintenant aussi par Telegram.
        try:
            run_sonarr_watch_once()
        except Exception as e:
            import traceback as _traceback
            send_telegram_notification(
                f"🔥 MouFlanimeXer — Watcher Sonarr plante\n"
                f"💬 {e}\n\n{_traceback.format_exc()[-500:]}"
            )
            raise
        sys.exit(0)
    if "--list-series" in sys.argv:
        cli_list_series_in(SONARR_WATCH_DIRS)
        sys.exit(0)
    if "--exclude-series" in sys.argv or "--include-series" in sys.argv:
        exclude = "--exclude-series" in sys.argv
        flag = "--exclude-series" if exclude else "--include-series"
        idx = sys.argv.index(flag)
        if idx + 1 >= len(sys.argv):
            print(f'Usage : python3 mouflanimexer.py {flag} "Nom exact de la série"')
            sys.exit(1)
        cli_set_series_excluded(sys.argv[idx + 1], exclude)
        sys.exit(0)
    if "--list-series-in" in sys.argv:
        idx = sys.argv.index("--list-series-in")
        if idx + 1 >= len(sys.argv):
            print('Usage : python3 mouflanimexer.py --list-series-in "/chemin/du/dossier"')
            sys.exit(1)
        cli_list_series_in([Path(sys.argv[idx + 1])])
        sys.exit(0)
    if "--add-extra-sub-lang" in sys.argv or "--remove-extra-sub-lang" in sys.argv:
        add = "--add-extra-sub-lang" in sys.argv
        flag = "--add-extra-sub-lang" if add else "--remove-extra-sub-lang"
        idx = sys.argv.index(flag)
        if idx + 2 >= len(sys.argv):
            print(f'Usage : python3 mouflanimexer.py {flag} "Nom exact de la série" <code_langue>')
            print('Exemple : python3 mouflanimexer.py --add-extra-sub-lang "Totally Spies / S01" kor')
            sys.exit(1)
        cli_set_extra_sub_lang(sys.argv[idx + 1], sys.argv[idx + 2], add)
        sys.exit(0)

    tools_missing = missing_tools()
    if tools_missing:
        print(f"[!] Attention, outils manquants : {', '.join(tools_missing)}")
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "<ip-de-ce-serveur>"
    print(f"Ouvre ton navigateur sur : http://{ip}:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=False)
