# TODO HorRAGor

Suivi des manquements identifiés par rapport au cahier des charges
(`HorRAGor BOT Partie 3.pdf`) et de bugs relevés par relecture de code.
Mis à jour au fil des sessions.

## 🐛 Bugs confirmés — agent LangGraph

- [x] **Boucle de retry sans plafond réel → `GraphRecursionError`.**
  Observé en usage réel (logs Docker, requête "films de science-fiction
  note > 7 entre 1990 et 2000") : la boucle
  `merge_filters_node → search_vector_node → validation_film_node →
  route_validation_hybrid` tourne indéfiniment sans jamais atteindre le
  plafond métier prévu (`retry_count >= 2`), jusqu'à la limite globale de
  LangGraph, qui bascule sur un fallback narratif dégradé au lieu de la
  réponse attendue.
  - Cause : [agents/nodes_rag.py:451](agents/nodes_rag.py:451)
    (`search_vector_node`) remet `retry_count` à **0** dès que FAISS renvoie
    des résultats non vides, sans savoir si ces résultats passeront la
    validation. [agents/nodes_rag.py:820](agents/nodes_rag.py:820)
    (`validation_film_node`) le remonte à 1 en cas d'échec, mais le tour
    suivant le remet à 0 avant que le routeur ne le revoie — le compteur ne
    dépasse donc jamais 1.
  - Déclencheur observé : un film candidat au titre mal formé en base
    (`"Frankenstein's Planet of Monsters!"`, sans suffixe année) rejeté en
    boucle par la validation stricte de format `Titre Année`.
  - Correctif appliqué : `search_vector_node` ne touche plus `retry_count`
    quand FAISS trouve des résultats (seul un échec de recherche
    l'incrémente désormais) — c'est uniquement `validation_film_node` qui
    l'incrémente sur un échec de validation. `intent_classifier_node` le
    remet explicitement à 0 à chaque nouveau tour de conversation, pour
    qu'il ne s'accumule pas ni ne reste figé d'un tour à l'autre.
  - Non traité : la validation stricte de format de titre
    (`"Frankenstein's Planet of Monsters!"` rejeté faute de suffixe année)
    qui déclenchait concrètement les retries — hors du périmètre de ce
    correctif, à traiter séparément si le cas se reproduit.

- [x] **Poser une question sur un film déjà affiché relançait une RECHERCHE
  au lieu d'une DISCUSSION.** Observé en usage réel : citer le titre d'un des
  films proposés dans la question suivante ("Get Out, quel est le
  réalisateur ?") faisait parfois retomber le bot sur la même liste de films
  au lieu de répondre sur ce film précis.
  - Cause : [agents/prompts.py:120](agents/prompts.py:120) (`INTENTION_PROMPT`)
    contenait deux règles contradictoires — la règle absolue disait "question
    sur un film + contexte actif → toujours DISCUSSION", tandis que la règle 3
    disait "titre explicite mentionné → toujours RECHERCHE, même si contexte
    actif". Le LLM n'avait aucun moyen de savoir si le titre cité était déjà
    l'un des films affichés, car [agents/nodes_rag.py:136](agents/nodes_rag.py:136)
    (`intent_classifier_node`) ne transmettait qu'un booléen (`HAS_CONTEXT`),
    jamais les titres réels.
  - Correctif appliqué : `intent_classifier_node` extrait maintenant les
    titres déjà en mémoire depuis `state.retrieved_movies` (déjà hydraté par
    `card_node`/`format_cards_node`, aucun appel base supplémentaire) et les
    injecte dans le prompt via `CONTEXT_TITLES`. Les règles 1 et 3 du prompt
    tranchent désormais sur l'appartenance du titre cité à cette liste, au
    lieu d'un simple booléen — la contradiction est levée.

- [x] **DISCUSSION sur un film déjà affiché plantait le stream si plusieurs
  films étaient en mémoire (crash Pydantic).** Observé en usage réel :
  demander le réalisateur de "Welcome to Japan" alors que 5 films japonais
  étaient en contexte faisait planter le SSE après que le narrateur ait déjà
  généré la bonne réponse — jamais livrée au frontend.
  - Cause : [api/routes.py:226-240](api/routes.py:226) décide du type
    Pydantic (`FilmDetail` vs `FilmShort`) uniquement sur le **nombre** de
    films (`len(movies) == 1` vs `> 1`), pas sur leur type réel.
    `load_film_node` ([agents/nodes_rag.py:829](agents/nodes_rag.py:829))
    charge toujours des `FilmDetail` complets quel que soit leur nombre → à
    5 films en contexte, `len(movies) > 1` déclenche
    `FilmShort.model_validate(FilmDetail_instance)`, qui lève
    `pydantic_core.ValidationError` (`Input should be a valid dictionary or
    instance of FilmShort`).
  - Bug symétrique identifié en même temps : la branche hybride RAG
    (`format_cards_node`) produit toujours des `FilmShort`, même quand un
    seul film reste après validation → `len(movies) == 1` déclenche alors
    `FilmDetail.model_validate(FilmShort_instance)`, qui plante pareil.
  - Correctif appliqué : normalisation par `movie.model_dump()` avant
    revalidation dans les deux branches, qui fonctionne quel que soit le
    modèle Pydantic source.
  - Limite connue du correctif : quand la branche hybride ne renvoie qu'un
    seul `FilmShort`, le `FilmDetail` reconstruit à partir de son
    `model_dump()` a les champs absents de `FilmShort` (réalisateur, durée,
    budget...) à `None` — pas un crash, mais une carte incomplète. Une
    ré-hydratation complète via `get_films_details_by_ids` serait plus
    correcte si ce cas s'avère fréquent.

- [x] **`validation_film_node` valide par défaut quand le LLM ne remplit pas
  `valid_titles`/`invalid_titles`.** Observé en usage réel (requête "Films
  japonais avec une note supérieure à 8") : le LLM a renvoyé
  `valid_titles: []`, `invalid_titles: []` et son verdict réel
  (`is_relevant: False`, films non pertinents listés un par un) uniquement
  dans le champ texte libre `feedback`. Le code
  ([agents/nodes_rag.py:790](agents/nodes_rag.py:790)) ne teste que
  `len(invalid_titles) == 0` pour décider du PASS → liste entière (dont des
  films indonésien/philippin non-horreur) validée et présentée à
  l'utilisateur comme cohérente.
  - Cause structurelle : `ValidationFilmListResult`
    ([agents/nodes_rag.py:80](agents/nodes_rag.py:80)) n'a pas de champ
    booléen de verdict global (`is_relevant`) — seulement deux listes de
    titres à recomposer, fragiles dès que le LLM local ne les remplit pas.
  - Correctif appliqué : ajout du champ `is_relevant: bool` (obligatoire)
    au schéma, prompt aligné sur les champs réellement attendus par le
    schéma (il en décrivait d'autres, `has_missing_info`/`corrected_title`,
    qui n'existent pas sur `ValidationFilmListResult`), et le PASS total
    exige désormais `is_relevant is True` **et** `invalid_titles` vide —
    un verdict incomplet (listes vides sans `is_relevant`) tombe en PASS
    partiel/FAIL au lieu d'un PASS implicite.

- [x] **DISCUSSION sur un film précis renvoyait toujours les N films en
  mémoire, pas seulement celui cité.** Observé en usage réel : "Welcome to
  Japan nom du réalisateur ?" avec 5 films japonais en mémoire → les 5 films
  étaient rechargés, revalidés, enrichis et renvoyés dans la réponse finale,
  alors que la question ne portait que sur un seul titre.
  - Cause : [agents/nodes_rag.py:838](agents/nodes_rag.py:838)
    (`load_film_node`, branche DISCUSSION) charge inconditionnellement
    **tous** les `tmdb_id` de `last_displayed_movies_id`, sans jamais les
    filtrer sur le titre cité — contrairement à la branche RECHERCHE qui
    passe par `title_router_node`. Le film cité par l'utilisateur n'est
    jamais isolé du reste du contexte.
  - Correctif appliqué : quand plusieurs films sont en mémoire,
    `load_film_node` filtre `retrieved_movies` sur les films dont le titre
    apparaît (recherche de sous-chaîne insensible à la casse) dans
    `user_query`. Si aucun titre ne correspond (question par pronom, "il
    est sorti quand ?"), tous les films restent en contexte — comportement
    inchangé pour ce cas.
  - Limite connue : matching par sous-chaîne simple, pas de gestion des
    accents/ponctuation/casse avancée ni des fautes de frappe (ex :
    "welcome to japn" ne matcherait pas "Welcome to Japan") — même limite
    que le point suivant.
  - Complément appliqué : le filtrage ne portait que sur la réponse du tour
    en cours — `last_displayed_movies_id` (mémoire de session) restait
    inchangé, donc le tour suivant sans titre explicite ("qui est
    l'actrice principale ?") rechargeait de nouveau tous les films
    d'origine. `load_film_node` réécrit maintenant aussi
    `last_displayed_movies_id` sur le sous-ensemble retenu quand le
    filtrage par titre a réduit le contexte, pour que les questions par
    pronom du tour suivant restent recalées sur le bon film.
  - Vérifié séparément : le réalisateur "non disponible" pour "Welcome to
    Japan" n'est pas un bug — `director_id` est réellement `NULL` en base
    pour ce film (jeu de données de test).

- [x] **Matching de titres par égalité de chaîne fragile dans
  `validation_film_node`.** [agents/nodes_rag.py:784](agents/nodes_rag.py:784)
  compare `valid_titles`/`invalid_titles` (texte libre du LLM) à `f.title`
  par égalité stricte après un hack `split(" (")[0]`. Un titre reformulé
  différemment par le LLM (accent, casse, ponctuation) est silencieusement
  exclu du `valid_partial`, sans log de l'écart.
  - Correctif appliqué : comparaison normalisée en minuscules des deux
    côtés, et log d'avertissement listant les titres validés par le LLM
    introuvables dans `retrieved_movies` (reformulation/hallucination),
    pour garder la visibilité sur les écarts qui subsistent malgré la
    normalisation (accents, ponctuation).

## 🟠 Dette de lisibilité — agent LangGraph

- [x] Code mort laissé en commentaire dans
  [agents/nodes_narrateur.py:191-200](agents/nodes_narrateur.py:191)
  (contraire à la règle du socle commun : « pas de code mort en commentaire,
  git le retrouve »). Supprimé.
- [x] Log trompeur : [agents/nodes_narrateur.py:72](agents/nodes_narrateur.py:72)
  tague `[format_cards_node]` alors que la ligne s'exécute dans
  `narrator_node` — gêne la lecture des logs Docker en production. Tag
  corrigé.
- [x] En-têtes de docstring obsolètes : `agents/nodes_wikipedia.py` et
  `agents/nodes_narrateur.py` commencent tous les deux par
  `"""agents/nodes.py` (copié-collé d'un fichier renommé/scindé depuis).
  Réécrits pour décrire le contenu réel de chaque fichier.
- [x] `agents/state.py` est un fichier mort : entièrement composé de code
  commenté (ancienne définition de `AgentState`/`AgentStep`, remplacée par
  `shared/schemas.py`), aucune référence ailleurs dans le dépôt
  (`grep -rn "agents.state"` ne remonte rien hors de lui-même). À supprimer
  (`git rm agents/state.py`) — non fait cette session : la suppression de
  fichier a été bloquée par le classifieur de permissions de l'environnement
  d'exécution, à faire manuellement.
- [x] Coquille dans un message de log :
  [agents/router.py:536](agents/router.py:536)
  `"[Rouroute_validation_hybridte]"`. Corrigé en `[route_validation_hybrid]`.
- [x] Script de test cassé dans
  [agents/tools/vector_tools.py:241-375](agents/tools/vector_tools.py:241)
  (bloc `if __name__ == "__main__"`) : appelle des `@tool async def` via
  `.func(...)` sans `await` — plante s'il est exécuté directement. Logique
  déplacée dans `async def _run_manual_tests()`, appels convertis en
  `.ainvoke(...)`, exécutée via `asyncio.run()`.
- [ ] `_checkpointer = InMemorySaver()`
  ([agents/graph.py:63](agents/graph.py:63)) : toute la mémoire de
  conversation (dont `last_displayed_movies_id`, nécessaire pour discuter
  d'un film déjà affiché) est perdue à chaque redémarrage du conteneur — pas
  de backend de persistance configuré. Non traité : nécessite de choisir et
  d'ajouter un backend de checkpoint persistant (SQLite/Postgres via
  `langgraph-checkpoint-*`), une dépendance nouvelle à valider avant tout
  ajout (socle commun § priorité 2).
- [x] Contexte potentiellement surdimensionné envoyé à `llm_synthesis`
  ([agents/nodes_wikipedia.py:184](agents/nodes_wikipedia.py:184)) : jusqu'à
  10 000 caractères de synopsis Wikipédia par film, sans troncature globale
  si plusieurs films sont enrichis en DISCUSSION. Plafond global
  `MAX_SYNTHESIS_CONTEXT_CHARS = 8000` ajouté sur le contexte total
  (tous films confondus) avant l'appel LLM.
- [x] Mauvais usage de loguru dans
  [agents/tools/wiki_tools.py](agents/tools/wiki_tools.py) : `print()` au
  lieu du logger, `logger.error("SUMMARY ERROR:", repr(e))` (args positionnels
  sans `{}`, le détail de l'erreur était silencieusement perdu), et un
  `except Exception:` final qui ne journalisait rien avant de renvoyer
  `{"error": "UNKNOWN_ERROR"}`. Remplacés par `logger.exception(...)` avec
  placeholders `{}` dans les trois cas.
- [x] Génération du diagramme au démarrage sans gestion d'erreur
  ([agents/graph.py:273-283](agents/graph.py:273)) : `graph()` est appelée une
  fois à l'import par `api/modules/chat_service.py` et écrivait
  inconditionnellement `graph.mmd` puis `HorRAGor_graph.png` via
  `draw_mermaid_png()` — un appel réseau vers l'API externe mermaid.ink. Une
  indisponibilité réseau (proxy, coupure) faisait planter tout le démarrage
  de l'API pour un simple artefact de développement. `print()` remplacé par
  le logger. Génération encadrée par un `try/except` : un échec journalise un
  warning sans empêcher le graphe compilé d'être retourné et utilisé.
- [ ] `os.environ["LANGGRAPH_STRICT_MSGPACK"] = "false"`
  ([agents/graph.py:58](agents/graph.py:58)) : désactive globalement la
  vérification stricte du msgpack pour faire taire les avertissements
  « Deserializing unregistered type... This will be blocked in a future
  version » (vus en logs pour `ChatFilters`, `AgentStep`, `FilmShort`) au lieu
  d'enregistrer ces types comme modules msgpack autorisés. Non traité :
  contournement qui cassera silencieusement dès qu'une version future de
  LangGraph rendra le mode strict obligatoire ; nécessite d'identifier
  précisément les types à enregistrer plutôt que de désactiver le contrôle.

## 🐛 Bugs confirmés — câblage frontend / backend

- [x] **Cartes de films non affichées quand un seul film est trouvé.**
  L'API renvoie `film` (FilmDetail) quand `len(movies) == 1` et
  `recommendations` (liste) quand il y en a plusieurs
  ([api/routes.py:200-224](api/routes.py:200)). Le frontend intègre désormais
  `event.get("film")` dans la liste des films à afficher.

- [x] **Affiches (posters) jamais correctement affichées.**
  Les requêtes SQL transforment désormais les chemins relatifs en URLs CDN
  complètes via `TMDB_IMAGE_BASE_URL` avant de les transmettre au frontend.

- [x] **Sidebar des filtres (réalisateur, genres) toujours cassée.**
  La sidebar utilise désormais `DATABASE_API_URL` et les endpoints
  `/db/list_real` et `/db/list_genre` de l'API Database.

- [x] **Fonctions mortes et cassées dans `api_client.py`** (non appelées par
  `app.py` aujourd'hui, mais cassées si utilisées un jour, et couvertes par
  des tests d'intégration qui échoueraient si `--run-integration` était
  activé) :
  - `get_film_by_id`, `get_realisateurs`, `get_genres` ciblent désormais l'API
    Database.
  - `send_chat_query` consomme désormais le flux SSE de
    `POST /chat/response_stream`.

## 🟠 Robustesse au démarrage

- [ ] **Pas de reconstruction automatique de l'index FAISS.**
  [api/main.py](api/main.py:51) appelle uniquement `load_index()` au
  démarrage et lève `RuntimeError` si les fichiers sont absents.
  `build_index()` est du code mort, commenté dans
  [database/faiss_service.py:49](database/faiss_service.py:49). Sur un clone
  neuf sans `faiss_data/` pré-généré, le conteneur `api` ne démarre pas —
  contrairement à ce que documente le QUICKSTART ("déclenche la première
  synchronisation... depuis Supabase").
  → Soit documenter l'étape manuelle (`uv run database/populate.py` avant le
  premier `docker compose up`), soit ré-activer `build_index()` au démarrage
  si l'index est absent.

## 🔴 Sécurité (Épilogue MLOps du cahier des charges)

- [x] Authentification par **Refresh Tokens** entre le frontend et l'API IA —
  implémentée : [api/auth_routes.py](api/auth_routes.py) expose
  `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`,
  `/auth/me` ; [api/auth_utils.py](api/auth_utils.py) gère création,
  validation et révocation des refresh tokens, stockés en base
  (`database/tables/refresh_tokens.py`) ; `python-jose` est une dépendance
  directe (pas seulement transitive).
- [ ] Communication **chiffrée** frontend → API — HTTP simple actuellement.
- [ ] **Réseau privé étanche pour `database_api`** — le port est publié
  directement sur l'hôte (`8001:8000` dans
  [docker-compose.yml:65](docker-compose.yml:65)) alors que le cahier des
  charges exige qu'il soit strictement inaccessible depuis l'extérieur du
  cluster.

## 🟠 Tests — couverture ≥ 80% (API IA, API Database, UI)

- [x] `database` : 100% (htmlcov).
- [ ] `api` (API IA) : aucun rapport de couverture généré, à vérifier.
- [ ] `frontend` (UI) : `pytest`/`pytest-cov` **absents** de
  [frontend/pyproject.toml](frontend/pyproject.toml) malgré l'existence de
  tests ([frontend/tests/](frontend/tests/), [frontend/test_app.py](frontend/test_app.py))
  — à déclarer avant de pouvoir mesurer la couverture.
- [ ] CI ([.github/workflows/docker.yml](.github/workflows/docker.yml)) ne
  lance les tests que pour `agents` avant le build/push Docker — `api`,
  `database`, `frontend` ne sont jamais testés en CI.
- [ ] Aucun seuil de couverture appliqué en CI.

## 🟡 Documentation

- [x] Sphinx en place : [docs/source/](docs/source/) (`conf.py`, `index.rst`,
  `api.rst`, `agents.rst`, `database.rst`, `langgraph.rst`,
  `database_schema.rst`), généré en CI (`sphinx-build`). Sortie `docs/build/`
  volontairement non commitée (`.gitignore:60`, régénérable). Doc auto des
  deux API, schéma relationnel de la base
  ([database/tables/](database/tables/)), cartographie du graphe multi-agent
  ([agents/graph.py](agents/graph.py)).

## 🟡 Monitoring

- [ ] [monitoring/docker-compose.yml](monitoring/docker-compose.yml)
  (Langfuse full stack + Uptime Kuma) est **séparé** de la stack principale
  ([docker-compose.yml](docker-compose.yml)) — pas de "stack Docker unifiée"
  au sens du cahier des charges.
- [ ] Uptime Kuma présent mais pas de confirmation que les 3 composants
  (API IA, API Database, Frontend) sont effectivement sondés.

## 🟡 Gouvernance

- [ ] Aucun template d'issue GitHub (`.github/ISSUE_TEMPLATE/`) — le cahier
  des charges demande que chaque anomalie soit archivée en GitHub Issues.

## Dette déjà connue (hors scope Partie 3, cf. CLAUDE.md)

- [ ] `SUPABASE_PASSWORD` avec valeur par défaut placeholder dans
  [database/connection.py](database/connection.py) au lieu d'un refus de
  démarrage explicite (fail-closed).

---

# Relecture du dossier complet — 3 septembre 2026

Observations issues d'une relecture de **l'intégralité du répertoire de
travail**, fichiers non suivis par git compris (`.env` locaux, `.dockerignore`,
Dockerfiles, configuration du hook, artefacts sur disque) — donc de choses
qu'une lecture du seul contenu commité ne montre pas.

## 🔴 Sécurité — critique, non listé jusqu'ici

- [ ] **Clé de signature JWT en dur dans le dépôt, et effectivement utilisée.**
  [api/auth_config.py:19](api/auth_config.py:19) :
  `os.getenv("JWT_SECRET_KEY", "votre_cle_secrete_tres_longue_et_complexe_changez_moi_en_production")`.
  Or `JWT_SECRET_KEY` est **absent du `.env` de ce poste** (il n'existe que dans
  `.env.example`) : l'API signe et accepte donc aujourd'hui ses access/refresh
  tokens avec une valeur publiquement lisible dans le dépôt — n'importe qui
  peut forger un token valide pour n'importe quel utilisateur.
  - Plus grave que le `SUPABASE_PASSWORD` déjà listé en dette : un mot de passe
    de base faux fait échouer la connexion bruyamment, une clé de signature par
    défaut fonctionne silencieusement. Le défaut n'est pas un pense-bête, c'est
    une porte ouverte.
  - À corriger : fail-closed explicite (refus de démarrage si la variable est
    absente, cf. socle § Secrets), et ajout de `JWT_SECRET_KEY` au `.env` local.
  - La clé étant commitée, elle est à considérer comme divulguée : tous les
    tokens émis jusqu'ici sont à invalider une fois la nouvelle clé posée.

## 🔴 Conteneurisation — écarts confirmés

- [x] **Deux volumes montés sur le même point dans le service `api`.**
  [docker-compose.yml:102-103](docker-compose.yml:102) montait à la fois le
  volume nommé `faiss_data` et le bind `./api/faiss_data` sur
  `/app/faiss_data`. Le second l'emportait : le volume `horragor_faiss_data`
  n'était jamais lu ni écrit, et le « piège déjà payé » du `CLAUDE.md`
  (`docker volume rm horragor_faiss_data`) était sans effet.
  - **Correctif appliqué** : les deux montages sont retirés, ainsi que la
    déclaration du volume nommé (plus aucun consommateur). L'index embarqué
    dans l'image `api` devient la **source unique** — c'est le choix retenu,
    la sauvegarde du volume ne se comportant pas de façon fiable.
  - `RUN mkdir -p /app/faiss_data` retiré de [Dockerfile.api](Dockerfile.api) :
    devenu inatteignable, `COPY . .` fournit déjà le dossier.
  - Documentation réalignée dans le même lot, puisque le comportement change :
    le piège FAISS de [CLAUDE.md](CLAUDE.md) est réécrit (l'index vient de
    l'image ; ne pas remonter de volume sur ce chemin ; rafraîchir = régénérer
    `faiss_data/` **puis** `docker compose build api`), et les sections
    « Démarrages suivants » / « Forcer un rebuild » de
    [QUICKSTART.md](QUICKSTART.md) ne parlent plus d'un volume inexistant.
  - **Vérifié de bout en bout sur la stack réellement démarrée** :
    - `docker inspect horragor_api` → **aucun montage** ;
    - `/app/faiss_data/horragor.index` dans le conteneur = `a84da881…`, soit
      l'octet pour octet de `faiss_data/` du dépôt ;
    - logs de démarrage : « Index FAISS chargé : **63325 films** » ;
    - `GET /health` → `{"status":"ok"}` ;
    - requête RAG réelle sur `POST /chat/response_stream`
      (« un film de zombies des années 80 ») : filtres consolidés
      `Horror` / 1980-1989, recherche vectorielle exécutée, deux films
      retournés (*Night of the Zombies*, *Killer Zombies*) avec affiches et
      synopsis, flux clos par `{"type":"done"}`.
  - Conséquence assumée : l'index est figé dans l'image. Un rafraîchissement
    impose un rebuild de l'image `api`, et chaque image publiée porte les
    ~250 Mo de l'index.

- [ ] **Les `uv.lock` sont copiés dans les images puis jamais utilisés.**
  Les trois Dockerfiles copient `pyproject.toml` + `uv.lock`
  ([Dockerfile.api:25-26](Dockerfile.api:25),
  [Dockerfile.database:22](Dockerfile.database:22),
  [Dockerfile.frontend:14](Dockerfile.frontend:14)) « pour profiter du cache
  Docker », puis installent via une liste `uv pip install --system` écrite à la
  main et **sans aucune version épinglée**. Les images ne tournent donc pas sur
  les versions verrouillées testées en local et en CI — exactement ce que le
  socle commun interdit (« une CI qui installe sans verrou ne teste plus la même
  chose que le poste de développement »).
  - Conséquence directe : la liste manuelle dérive déjà du `pyproject.toml`.
    `supabase` (déclaré dans [api/pyproject.toml:24](api/pyproject.toml:24))
    n'est pas installé dans l'image ; `pillow` (déclaré côté frontend) non plus.
  - → `uv sync --frozen --no-dev` (ou `uv pip install --system -r`) à partir du
    lock, et suppression de la liste manuelle.

- [x] **`.dockerignore` quasi vide : ~1 Go envoyé au démon à chaque build.**
  [.dockerignore](.dockerignore) ne contient que `.git`, `.venv`,
  `__pycache__/`, `*.pyc`, `.env`. Les motifs sans `**/` ne s'appliquent qu'à la
  racine, donc **rien n'exclut** :
  - `agents/.venv`, `api/.venv`, `frontend/.venv`, `database/.venv` (≈ 900 Mo à
    eux seuls, dont 363 Mo pour le seul frontend) ;
  - `faiss_data/horragor.index` **et** `api/faiss_data/horragor.index`
    (248 Mo chacun, soit 496 Mo dupliqués sur le disque) ;
  - `database/data_backup/horror_db.sqlite` (42 Mo) ;
  - `MERISE HORRAGOR.pptx` (4,5 Mo), `HorRAGor BOT Partie 3.pdf` (1,3 Mo),
    `agents/htmlcov/`, `database/htmlcov/`, `docs/build/`, `logs/`,
    `.pytest_cache/`, `*.env` des sous-dossiers.
  - Le `.env` des sous-dossiers n'est pas couvert non plus : `.env` n'exclut que
    celui de la racine, `agents/tools/.env` et `database/.env` partent dans le
    contexte de build (et `COPY . .` les fait entrer dans l'image).
  - **Correctif appliqué** : [.dockerignore](.dockerignore) réécrit par
    catégories, motifs préfixés par `**/`, et
    [Dockerfile.api.dockerignore](Dockerfile.api.dockerignore) ajouté pour la
    seule différence qui compte — l'index FAISS, nécessaire à l'image `api`
    et inutile aux deux autres. BuildKit lit `<Dockerfile>.dockerignore` en
    *remplacement* du fichier racine, pas en complément : les deux fichiers
    sont donc une copie délibérée l'un de l'autre et évoluent ensemble
    (commenté en en-tête des deux).
  - Mesuré avant/après sur les trois images réellement reconstruites
    (`docker compose build`) :

    | Image | Avant | Après |
    |---|---|---|
    | `horragor_2-api` | 2,96 Go | **1,56 Go** |
    | `horragor_2-database_api` | 2,30 Go | **368 Mo** |
    | `horragor_2-frontend` | 1,26 Go | **765 Mo** |

    Contexte transféré au démon : **1,39 Mo** pour `database`/`frontend`,
    260 Mo pour `api` (l'index seul), contre ~1 Go pour chacune des trois.
  - Vérifié dans les images reconstruites : plus aucun `.env`, aucun `.venv`,
    aucun `htmlcov/` ni `logs/` ; `/app/faiss_data/horragor.index` bien présent
    dans la seule image `api`, à l'emplacement exact que pointe
    `FAISS_INDEX_PATH`.
  - `logs/` exclu du contexte sans risque : [logger.py](logger.py:38) crée le
    dossier à l'import (`LOG_DIR.mkdir(exist_ok=True)`).
  - Complément traité ensuite : les deux montages qui masquaient
    `/app/faiss_data` ont été retirés, de sorte que l'index embarqué est
    bien celui que lit le conteneur (cf. item « Deux volumes montés sur le
    même point »).

- [x] **Secrets copiés dans les images.** `Dockerfile.api:54` et
  `Dockerfile.database:36` font `COPY . .` sur un contexte qui contient
  `agents/tools/.env` et `database/.env` (identifiants Supabase en clair, non
  exclus par le `.dockerignore` — point précédent).
  - **Fuite confirmée, puis délimitée.** Reproduction des anciennes règles
    d'exclusion sur le contexte réel : **trois** fichiers entraient dans
    l'image, un de plus que ce que cet item annonçait —
    `/app/agents/tools/.env`, `/app/database/.env` et surtout
    `/app/monitoring/.env`, qui porte bien plus que Supabase (clés Langfuse,
    `MINIO_ROOT_PASSWORD`, `REDIS_PASSWORD`, `NEXTAUTH_SECRET`, `SALT`,
    `LANGFUSE_INIT_USER_PASSWORD`).
  - **Correction de l'analyse initiale : les images GHCR ne sont pas
    concernées.** Aucun fichier `.env` n'a jamais été commité sur les
    176 commits de l'historique (`git log --all --diff-filter=A -- '*.env'`),
    donc le checkout de la CI ne les a jamais contenus, donc les images
    publiées par [.github/workflows/docker.yml](.github/workflows/docker.yml)
    ne les ont jamais embarqués. La fuite était **strictement locale**.
  - Conséquence pratique : **pas de révocation d'identifiants nécessaire**,
    sauf si une image construite localement a été poussée ou transmise à un
    tiers en dehors de la CI — à confirmer par l'utilisateur, c'est le seul
    chemin de fuite qui reste.
  - Correctif appliqué : les motifs `**/.env`, `**/.env.*` et `**/*.env` du
    nouveau `.dockerignore` (et de son homologue `api`) excluent tout fichier
    d'environnement à n'importe quelle profondeur. Vérifié dans les trois
    images reconstruites : zéro fichier `.env`.
  - Non régressif : les valeurs des trois `.env` sont **octet pour octet
    identiques** à celles du `.env` racine, que `docker-compose.yml` injecte
    déjà par `env_file`. Le conteneur lisait `database/.env` depuis l'image
    (`load_dotenv()` remonte depuis le fichier appelant) ; il lit désormais
    les mêmes valeurs depuis l'environnement.

- [ ] `sqlalchemy` installé deux fois dans [Dockerfile.database:27](Dockerfile.database:27)
  et [Dockerfile.database:33](Dockerfile.database:33) (`sqlalchemy` puis
  `SQLAlchemy`) — sans effet mais signe que la liste manuelle n'est pas relue.

- [ ] Incohérence de lancement entre images : `api` et `database` démarrent via
  `uv run uvicorn ...` alors que les dépendances ont été installées avec
  `uv pip install --system` (aucun projet uv à `/app`), tandis que `frontend`
  appelle `streamlit` directement. Un seul mécanisme suffirait.

## 🟠 Trois sources de vérité pour les secrets

- [ ] `.env` (racine), `database/.env` et `agents/tools/.env` déclarent **les
  mêmes** identifiants Supabase/Postgres, dupliqués à l'identique. Trois copies
  divergent, et c'est la mauvaise qui reste (socle § DRY). Les sous-projets
  appellent tous `load_dotenv()` sans chemin explicite, donc la copie prise
  dépend du répertoire courant au lancement — comportement différent entre
  `docker compose` (racine) et un `uv run` depuis `database/`.
  → Un seul `.env` à la racine, chargé par chemin explicite.

- [ ] `.env.example` désynchronisé du code, dans les deux sens :
  - **Utilisées par le code, absentes du modèle** : `API_URL`,
    `DATABASE_API_URL`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`,
    `LANGFUSE_SECRET_KEY`, `LANGGRAPH_STRICT_MSGPACK`.
  - **Dans le modèle, lues nulle part** : `POSTGRES_USER/PASSWORD/DB/HOST/PORT`
    (aucun service Postgres local dans `docker-compose.yml` — le bloc est
    commenté), `SUPABASE_PROJECT`, `SUPABASE_PUBLISHABLE_KEY`,
    `OLLAMA_MODELS_PATH`.
  - `JWT_SECRET_KEY` est le cas inverse du précédent : présent dans le modèle,
    absent du `.env` réel (cf. § Sécurité).

## 🟠 Outillage déclaré mais inexistant

- [ ] **`ruff` n'est une dépendance d'aucun des quatre sous-projets.**
  `CLAUDE.md` documente `uv run ruff check` / `uv run ruff format` comme la
  commande de lint « dans `api/`, `agents/`, `database/`, `frontend/` », mais
  ruff n'apparaît dans aucun `pyproject.toml`, aucun `uv.lock`, aucun `.venv`,
  et il n'existe aucune section `[tool.ruff]`. La commande documentée échoue.
  → Soit ajouter `ruff` en dépendance de dev des quatre sous-projets (ajout
  d'outil : à valider avant, socle § priorité 2), soit retirer la commande du
  `CLAUDE.md`.

- [ ] **Le hook pre-commit est actif mais sa configuration est le modèle
  d'exemple, non adaptée au projet.** `core.hooksPath` pointe bien sur
  `.githooks`, mais [.githooks/standards.conf](.githooks/standards.conf) est
  livré tel quel :
  - `INTERDIRE_PRINT=0`, `INTERDIRE_LOGGING=0`, `MODULE_LOGGER=""`, `RUFF=0` —
    soit les quatre garde-fous désactivés, alors que ce sont précisément les
    règles que le `CLAUDE.md` de ce dépôt énonce (loguru obligatoire, jamais de
    `print()` ni de `logging`, configuration centralisée dans `logger.py`).
  - `CHEMINS_EXCLUS="Reference/* donnees/*"` et
    `MOTIFS_INTERDITS="sources/* *.xlsx config.json .env"` : chemins d'un autre
    projet, aucun de ces dossiers n'existe ici.
  - Le hook ne vérifie donc aujourd'hui **que** l'interdiction de commit direct
    sur `main`/`master`.
  - Effet mesurable : **165 `print()`** subsistent hors tests dans le code suivi
    — `start.py` (39), `test_auth.py` (42), `test_synopsis_enrichment.py` (29),
    `agents/tools/vector_tools.py` (17), `database/faiss_service.py` (13),
    `database/queries.py` (13), `frontend/start.py` (13),
    `agents/chat_terminal.py` (11), `database/populate.py` (10),
    `frontend/utils/api_client.py` (8), `frontend/utils/auth_client.py` (5),
    `database/create_auth_tables.py` (5).
  - Point positif vérifié : aucun `import logging`, et `logger.add/remove`
    n'apparaît que dans [logger.py](logger.py) — les deux règles tiennent
    d'elles-mêmes malgré le hook muet.

## 🟠 Duplication de code — `api/schemas.py` est un fork périmé de `shared/schemas.py`

- [ ] [api/schemas.py](api/schemas.py) redéfinit **15 classes** déjà présentes
  dans [shared/schemas.py](shared/schemas.py) (`HealthResponse`,
  `ErrorResponse`, `DirectorsResponse`, `GenresResponse`, `FilmShort`,
  `FilmSearchResponse`, `FilmDetail`, `ChatFilters`, `AgentStep`, `AgentState`,
  `ChatRequest`, `ChatStatusResponse`, `ChatResponse`, `WikipediaResponse`,
  `WikipediaRequest`) et n'ajoute réellement que les six schémas
  d'authentification (`UserRegister`, `UserLogin`, `Token`, `TokenRefresh`,
  `UserResponse`, `AuthResponse`).
  - **Les deux copies ont déjà divergé** : le `FilmShort` de `api/schemas.py`
    n'a ni `synopsis` ni `judge_feedback`, et tout le fichier est resté à
    l'ancien style `Optional[X]` / `List[X]` quand `shared/schemas.py` est passé
    à `X | None` / `list[X]`.
  - Seul [api/auth_routes.py:28](api/auth_routes.py:28) importe
    `api.schemas` — et uniquement pour les schémas d'auth. Tout le reste du
    dépôt (api, agents, database, tests) importe `shared.schemas`.
  - → Réduire `api/schemas.py` aux seuls schémas d'authentification (ou les
    déplacer dans `shared/`), et supprimer les 15 doublons.
  - Docstring à corriger dans le même lot : [agents/router.py:110](agents/router.py:110)
    référence encore `api.schemas (AgentState)` alors que le fichier importe
    `shared.schemas`.

## 🟠 Code mort et en-têtes périmés (suite de la section « Dette de lisibilité »)

- [ ] [agents/nodes_rag.py:68-69](agents/nodes_rag.py:68) : `BASE_DIR` et
  `FAISS_INDEX_PATH = str(BASE_DIR / "data" / "faiss_index")` ne sont utilisés
  nulle part dans le fichier, et le chemin pointé (`data/faiss_index`) n'existe
  pas dans le dépôt. Pire, la constante porte le nom de la variable
  d'environnement réellement utilisée ailleurs
  ([api/main.py:39](api/main.py:39)) avec une valeur différente — piège de
  lecture.
- [ ] [agents/nodes_rag.py:2](agents/nodes_rag.py:2) : même en-tête périmé que
  celui déjà corrigé sur `nodes_wikipedia.py` et `nodes_narrateur.py` — le
  fichier commence par `"""agents/nodes.py`. La docstring décrit en plus des
  « nœuds principaux **à implémenter** » sous des noms qui n'existent plus
  (`node_classifier`, `node_extractor`, `node_sql_query`,
  `node_wikipedia_enrich`) alors que les nœuds réels s'appellent
  `intent_classifier_node`, `merge_filters_node`, `search_vector_node`…
  C'est une spécification abandonnée présentée comme de la documentation.
- [x] `agents/state.py` : confirmé supprimé du disque et de l'index git — la
  réserve « à faire manuellement » de la section précédente est levée.
- [ ] [api/README.md](api/README.md) est **vide (0 octet)** alors que
  [api/pyproject.toml](api/pyproject.toml) le déclare en `readme = "README.md"`.

## 🟡 Scripts et tests orphelins à la racine

- [ ] Trois scripts à la racine doublonnent le chemin de lancement de
  `docker-compose.yml` et ne sont couverts par rien :
  - [start.py](start.py) + [start_with_auth.sh](start_with_auth.sh) +
    [start_with_auth.bat](start_with_auth.bat) : lanceur alternatif hors Docker
    (création des tables d'auth, API en arrière-plan, tests, Streamlit), avec
    39 `print()`. Un quatrième lanceur existe en plus dans
    [frontend/start.py](frontend/start.py).
  - [test_auth.py](test_auth.py) et
    [test_synopsis_enrichment.py](test_synopsis_enrichment.py) : scripts
    manuels tapant sur une API **déjà lancée** (`http://localhost:8000`), mais
    nommés `test_*.py` et contenant des fonctions `test_*` au niveau module.
    Un `pytest` lancé depuis la racine les collecte et échoue faute d'API — et
    un `.pytest_cache/` traîne justement à la racine, signe que le cas s'est
    produit. Le `CLAUDE.md` place les tests « par sous-projet, dans son propre
    dossier `tests/` ».
  - → Soit les ranger en `scripts/` avec un nom qui n'est pas `test_*`, soit
    les supprimer si `docker compose` couvre le besoin.
- [ ] [frontend/test_app.py](frontend/test_app.py) : 11 tests jamais exécutés —
  [frontend/pytest.ini](frontend/pytest.ini) fixe `testpaths = tests`, et le
  fichier est à la racine de `frontend/`. Sa docstring documente en plus une
  installation `pip install pytest pytest-mock` absente du `pyproject.toml`
  (cf. l'item couverture frontend déjà listé).
- [ ] Coquille de nom de fichier : `api/tests/test_chat_servise.py`
  → `test_chat_service.py`.
- [ ] `api/tests/test_wiki.py` (47 lignes) et `agents/tests/test_wiki.py`
  (22 lignes) testent le même outil Wikipédia (`agents/tools/wiki_tools.py`)
  depuis deux sous-projets, avec des contenus différents. À consolider côté
  `agents/`, propriétaire de l'outil.
- [ ] `frontend/pytest.ini` cohabite avec `frontend/pyproject.toml` alors que
  les trois autres sous-projets configurent pytest dans le `pyproject.toml`
  (`[tool.pytest.ini_options]`). Deux emplacements pour la même configuration.

## 🟡 Déclarations de dépendances incohérentes entre sous-projets

- [ ] [frontend/requirements.txt](frontend/requirements.txt) duplique les
  dépendances du `pyproject.toml` en s'annonçant comme « alternative » — et a
  déjà dérivé (`httpx` manquant). Le `uv.lock` existe : le `requirements.txt`
  est une troisième source de vérité sans utilisateur.
- [ ] `pytest-asyncio` est déclaré en dépendance **d'exécution** (pas de dev)
  dans [api/pyproject.toml:28](api/pyproject.toml:28) et
  [agents/pyproject.toml:17](agents/pyproject.toml:17) — il part donc en image.
- [ ] `supabase>=2.30.1` ([api/pyproject.toml:24](api/pyproject.toml:24)) n'est
  importé nulle part dans le dépôt (`grep -rn "import supabase"` ne remonte
  rien) : l'accès Supabase passe par SQLAlchemy/psycopg2. Dépendance à retirer.
- [ ] `psycopg2` (compilation depuis les sources) côté `agents/` et
  `database/`, `psycopg2-binary` côté `api/` et dans les trois Dockerfiles —
  même besoin, deux paquets.
- [ ] `dotenv>=0.9.9` dans `agents/` et `database/` là où `api/` et `frontend/`
  utilisent `python-dotenv` : `dotenv` est un paquet tiers distinct (simple
  redirection vers `python-dotenv`), à ne pas laisser dans un lock.
- [ ] `[tool.setuptools]` déclare des périmètres qui se chevauchent :
  `agents/pyproject.toml` empaquette `["database", "agents", "api",
  "frontend"]`, `database/pyproject.toml` empaquette `["database", "agents"]`,
  `api/pyproject.toml` inclut `api*`, `database*`, `agents*`. Chaque
  sous-projet prétend empaqueter les autres.
- [ ] `frontend/` n'a pas de `.python-version` alors que les trois autres
  épinglent `3.11`.
- [ ] `api/monitoring/` n'a pas de `__init__.py` (contrairement à
  `api/modules/`) : l'import ne tient qu'aux packages implicites et
  `[tool.setuptools.packages.find]` ne le retiendrait pas dans une roue.

## 🟡 Monitoring — couplages fragiles

- [ ] [monitoring/docker-compose.yml:233](monitoring/docker-compose.yml:233)
  attache la stack au réseau externe `horragor_2_horragor_net`, nom **dérivé du
  nom du répertoire de travail** (`HorRAGor_2`). Un clone dans un dossier
  nommé autrement, ou un `docker compose -p`, et la stack de monitoring refuse
  de démarrer sans message explicite. → Fixer `name:` sur le réseau dans le
  `docker-compose.yml` principal et le référencer.
- [ ] [monitoring/prometheus/prometheus.yml:8](monitoring/prometheus/prometheus.yml:8)
  ne scrape que `horragor_api:8000`. `database_api` n'expose d'ailleurs aucune
  métrique : `Instrumentator()` n'est branché que sur
  [api/main.py:81](api/main.py:81). Complète l'item « les 3 composants sont-ils
  sondés » déjà listé.
- [ ] [monitoring/.gitignore](monitoring/.gitignore) est le `.gitignore` du
  dépôt **Langfuse** recopié tel quel (~120 lignes de Next.js, pnpm, Prisma,
  Vercel, Turbo, Playwright, `.claude/settings.json`, `.superset/`…). Une
  seule ligne y sert réellement (`.env*`, qui masque `monitoring/.env`). À
  réduire à ce qui concerne ce projet, ou à supprimer au profit du
  `.gitignore` racine.
- [ ] `uid: afwve5oglmvwgb` ajouté en dur dans
  [monitoring/grafana/provisioning/datasources/prometheus.yml](monitoring/grafana/provisioning/datasources/prometheus.yml)
  (modification non commitée à ce jour) : un UID généré par une instance
  Grafana locale, figé dans le provisioning. À conserver seulement s'il est
  référencé par [monitoring/grafana/dashboards/horragor.json](monitoring/grafana/dashboards/horragor.json),
  et à documenter dans ce cas.

## 🟡 `.gitignore` — motifs trop larges

- [ ] `bin/`, `lib/`, `include/`, `env/` ([.gitignore:9-13](.gitignore:9))
  ignorent ces noms **à n'importe quel niveau** : un futur `frontend/lib/` ou
  `database/bin/` de code source disparaîtrait de `git status` sans un mot.
  À restreindre à la racine (`/bin/`, `/lib/`…) comme c'est déjà fait pour
  `/build/` et `/dist/`.
- [ ] `*.env` ignore tout fichier finissant par `.env` (`prod.env`,
  `staging.env`) : voulu ici, mais à ne pas confondre avec `.env*`, qui aurait
  au contraire masqué `.env.example`. Rien à corriger, à ne pas « simplifier ».
- [ ] Le cahier des charges lui-même
  (`HorRAGor BOT Partie 3.pdf`, 1,3 Mo) est **non suivi et non ignoré** : il
  apparaît en `??` dans chaque `git status`. À ignorer explicitement (il n'a pas
  à entrer dans le dépôt) ou à ranger hors du répertoire de travail.

## 🟡 Artefacts régénérables commités

- [ ] Quatre copies du diagramme du graphe sont suivies :
  `HorRAGor_graph.png` (racine), `api/HorRAGor_graph.png`,
  `docs/HorRAGor_graph.png` (les trois **identiques**, 168 Ko chacune) et
  `agents/HorRAGor_graph.png` (32 Ko, version périmée). Idem pour `graph.mmd` :
  racine, `api/` et `docs/` identiques, `agents/graph.mmd` différent.
  Ces fichiers sont **générés au démarrage** par
  [agents/graph.py](agents/graph.py:273) — donc régénérables, donc à ignorer
  (socle § « artefacts régénérables »), avec une seule copie de référence si
  la documentation Sphinx en a besoin.
- [ ] `agents/Capture d’écran 2026-06-06 000734.png` : capture de travail
  suivie dans git, avec une apostrophe typographique dans le nom (pénible en
  ligne de commande et sur d'autres systèmes de fichiers). À retirer.
- [ ] `MERISE HORRAGOR.pptx` (4,5 Mo) et `HorRAGor_presentation.pptx` : binaires
  de présentation dans le dépôt de code, non diffables, alourdissant chaque
  clone et chaque contexte de build.
- [ ] `slide4_corrections.png` / `slide6_corrections.png` traînent sur le disque
  bien qu'ignorés depuis peu ([.gitignore:63](.gitignore:63)) : à supprimer du
  répertoire de travail.

## 🟡 Documentation — dérive constatée

- [ ] L'arborescence de [README.md](README.md:22) liste encore
  `agents/state.py` (fichier supprimé) et omet des modules qui existent :
  `agents/config.py`, `agents/chat_terminal.py`, `api/auth_config.py`,
  `api/auth_routes.py`, `api/auth_utils.py`, `api/schemas.py`,
  `database/create_auth_tables.py`, `database/models.py`,
  `shared/embeddings.py`, ainsi que les lanceurs de la racine.
- [ ] Deux QUICKSTART concurrents : [QUICKSTART.md](QUICKSTART.md) (121 lignes,
  chemin Docker) et [frontend/QUICKSTART.md](frontend/QUICKSTART.md)
  (224 lignes, chemin local). Rien n'indique lequel fait foi.
- [ ] [CHANGELOG_FLAVIE.md](CHANGELOG_FLAVIE.md) est un journal de travail
  nominatif commité à la racine : il redit ce que l'historique git contient
  déjà (socle § Commentaires — « cette information vit dans le message de
  commit »), et référence comme « créé » un `EPIC_FLAVIE_RESUME.md` qui
  n'existe pas dans le dépôt. À supprimer, ou à fondre dans un CHANGELOG
  unique et non nominatif.
- [ ] Sphinx ne documente pas `frontend/` ni `shared/` :
  [docs/source/index.rst](docs/source/index.rst) n'a pas de `frontend.rst`
  alors que le cahier des charges demande la documentation de l'UI.

## 🟡 CI — angles morts confirmés en relisant le workflow

- [ ] Aucun lint en CI ([.github/workflows/docker.yml](.github/workflows/docker.yml)) —
  cohérent avec l'absence de ruff, mais à traiter en même temps.
- [ ] Les images sont poussées sur GHCR en `:latest` **dès un push sur `dev`**,
  sans distinction de canal entre `dev` et `main` : un `:latest` peut donc
  provenir de `dev`. → Tag distinct par branche, ou push `:latest` réservé à
  `main`.
- [ ] Le job `docker` ne dépend que d'un job `test` qui ne teste que `agents`
  (déjà listé) : un échec `api`/`database`/`frontend` n'empêche aucune
  publication d'image.
