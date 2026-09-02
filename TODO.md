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

- [ ] **Cartes de films non affichées quand un seul film est trouvé.**
  L'API renvoie `film` (FilmDetail) quand `len(movies) == 1` et
  `recommendations` (liste) quand il y en a plusieurs
  ([api/routes.py:200-224](api/routes.py:200)). Le frontend ne lit jamais
  `event.get("film")` ([frontend/app.py:509-510](frontend/app.py:509)) : dans
  ce cas `films = []` et l'UI affiche « Aucun film ne correspond à vos
  critères » alors que l'agent a bien trouvé le film.
  → Corriger `app.py` pour intégrer `event.get("film")` dans les films à
  afficher.

- [ ] **Affiches (posters) jamais correctement affichées.**
  `poster_url=f"{film.poster_path}"` dans
  [database/queries.py:119](database/queries.py:119) et
  [:212](database/queries.py:212) réutilise le chemin relatif TMDB
  (`/xxx.jpg`) sans préfixer `https://image.tmdb.org/t/p/w500`. L'`<img>`
  généré dans [frontend/components/components.py:95](frontend/components/components.py:95)
  pointe vers une ressource inexistante sur le domaine Streamlit.
  → Préfixer `poster_url` (et vérifier `backdrop_url`) avec l'URL de base du
  CDN TMDB.

- [ ] **Sidebar des filtres (réalisateur, genres) toujours cassée.**
  [frontend/components/components.py:364](frontend/components/components.py:364)
  et [:396](frontend/components/components.py:396) appellent
  `{API_URL}/list_real` et `{API_URL}/list_genre` sur l'**API IA** (port
  8000). Ces routes n'existent que sur l'**API Database** (port 8001, préfixe
  `/db/`, voir [database/routes_db.py](database/routes_db.py)). Résultat :
  404 systématique, le sélecteur reste bloqué sur « Tous ».
  → Soit exposer un proxy `/list_real` et `/list_genre` sur l'API IA, soit
  donner au frontend une deuxième variable d'env (`DATABASE_API_URL`) pour
  cibler directement l'API Database.

- [ ] **Fonctions mortes et cassées dans `api_client.py`** (non appelées par
  `app.py` aujourd'hui, mais cassées si utilisées un jour, et couvertes par
  des tests d'intégration qui échoueraient si `--run-integration` était
  activé) :
  - `get_film_by_id`, `get_realisateurs`, `get_genres` → visent l'API IA au
    lieu de l'API Database (même bug que la sidebar).
  - `send_chat_query` (version non-streaming) → appelle `POST /chat/response`,
    entièrement commenté côté serveur ([api/routes.py:65-118](api/routes.py:65))
    → 404 garanti.
  → Décider : les corriger et les câbler, ou les supprimer avec leurs tests.

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

- [ ] Authentification par **Refresh Tokens** entre le frontend et l'API IA —
  aucune trace de code, `pyjwt` présent uniquement comme dépendance
  transitive dans [api/uv.lock](api/uv.lock).
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

- [ ] Aucune trace de Sphinx (`conf.py`, `.rst`). À mettre en place : doc
  auto des deux API, schéma relationnel de la base
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
