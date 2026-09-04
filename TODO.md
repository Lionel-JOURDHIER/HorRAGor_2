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
- [x] `_checkpointer = InMemorySaver()`
  ([agents/graph.py:63](agents/graph.py:63)) : toute la mémoire de
  conversation (dont `last_displayed_movies_id`, nécessaire pour discuter
  d'un film déjà affiché) était perdue à chaque redémarrage du conteneur.
  Corrigé : `SqliteSaver` (`langgraph-checkpoint-sqlite`, ajouté en
  dépendance de `agents/` et `api/` après validation), fichier persisté via
  `CHECKPOINT_DB_PATH` (défaut `data/checkpoints.sqlite`), monté en volume
  nommé `horragor_checkpoints` sur `/app/data` dans
  [docker-compose.yml](docker-compose.yml) — survit à `docker compose down`,
  contrairement à l'index FAISS qui reste volontairement embarqué dans
  l'image. Traité en même temps que le bug de mémoire partagée entre
  utilisateurs (section Sécurité ci-dessus), puisque les deux se recoupaient
  sur le même mécanisme de `thread_id`.
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
- [x] `os.environ["LANGGRAPH_STRICT_MSGPACK"] = "false"`
  ([agents/graph.py](agents/graph.py)) : remplacé par un enregistrement
  explicite des types Pydantic sérialisés dans `AgentState` (`ChatFilters`,
  `AgentStep`, `FilmShort`) via
  `JsonPlusSerializer(allowed_msgpack_modules=[...])`, injecté dans le
  `SqliteSaver` synchrone (`agents/graph.py`) et dans l'`AsyncSqliteSaver` de
  l'API (`api/main.py`). Vérifié par un round-trip de sérialisation
  (avertissements en erreurs) et en conditions réelles (rebuild Docker,
  aucun avertissement « Deserializing unregistered type » dans les logs).

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

- [x] **Fil de discussion d'un compte visible après connexion sur un autre,
  dans le même onglet Streamlit.** Signalé en usage réel après le fix de
  mémoire par utilisateur ci-dessous : la mémoire de l'agent (checkpointer
  SQLite) était bien isolée par compte, mais l'affichage
  (`st.session_state.messages` dans
  [frontend/components/auth_components.py](frontend/components/auth_components.py))
  n'était jamais réinitialisé au changement d'identité — seuls
  `access_token`/`refresh_token`/`user` l'étaient à la déconnexion.
  Corrigé : `messages` et les statistiques affichées sont vidés à chaque
  connexion, inscription et déconnexion.
- [x] **Aucune restauration de l'historique affiché à la reconnexion.**
  Conséquence attendue du point précédent une fois corrigé : l'écran repart
  vide à chaque connexion, alors que la mémoire de l'agent, elle, est
  conservée côté serveur. `AgentState` n'accumule pas les tours
  (`user_query`/`answer` sont écrasés à chaque appel), donc pas d'historique
  direct à lire. Ajouté : `get_conversation_history()`
  ([api/modules/chat_service.py](api/modules/chat_service.py)) rejoue
  l'historique des checkpoints du thread pour reconstruire les paires
  question/réponse, exposé via `GET /chat/history`
  ([api/routes.py](api/routes.py)) et consommé par le frontend à la
  connexion pour repeupler l'affichage.

## 🟠 Robustesse au démarrage

- [x] **Pas de reconstruction automatique de l'index FAISS.**
  `build_index()` et `load_or_build()` implémentés dans
  [database/faiss_service.py](database/faiss_service.py) (les trois tests
  déjà écrits pour cette fonctionnalité étaient commentés, réactivés sans
  changement). [api/main.py](api/main.py) lève désormais un fallback : si
  `load_index()` échoue au démarrage, l'index est reconstruit depuis Supabase
  (`db_session()` + `build_index()`) puis persisté sur disque
  (`save_index()`) avant de démarrer l'API ; une base Supabase vide fait
  toujours échouer le démarrage, avec un message explicite. Corrige au
  passage un bug réel dans `agents/chat_terminal.py`, qui appelait déjà
  `build_index()` alors que la méthode n'existait pas.

## 🔴 Sécurité (Épilogue MLOps du cahier des charges)

- [x] Authentification par **Refresh Tokens** entre le frontend et l'API IA —
  implémentée : [api/auth_routes.py](api/auth_routes.py) expose
  `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/logout`,
  `/auth/me` ; [api/auth_utils.py](api/auth_utils.py) gère création,
  validation et révocation des refresh tokens, stockés en base
  (`database/tables/refresh_tokens.py`) ; `python-jose` est une dépendance
  directe (pas seulement transitive).
- [x] Communication **chiffrée** frontend → API — résolu par la mise en place
  de Traefik (`chore : place la stack derrière un reverse proxy Traefik`) :
  plus aucun service applicatif n'expose de port, seul `127.0.0.1:80` l'est,
  ce qui remplace le TLS tant que le trafic ne quitte pas la machine (cf.
  [CLAUDE.md](CLAUDE.md) § Pièges déjà payés). Un vrai TLS reste à poser le
  jour d'un déploiement multi-machines.
- [x] **Mot de passe protégé en transit malgré l'absence de TLS.** Une
  tentative de TLS sur Traefik (certificat auto-signé, provider `file`,
  persisté sur disque pour ne plus se régénérer à chaque redémarrage) a été
  implémentée, testée, puis explicitement abandonnée sur demande de
  l'utilisateur après un avertissement navigateur
  `net::ERR_CERT_AUTHORITY_INVALID` — un certificat auto-signé n'est jamais
  approuvé par une CA de confiance, seul `mkcert` (CA locale installée sur
  chaque poste dev) l'aurait supprimé. Revert propre
  (`git revert -m 1 --no-edit`), stack repassée entièrement en HTTP.
  - Correctif retenu à la place : chiffrement RSA-2048/OAEP-SHA256 du seul
    champ mot de passe, scope volontairement limité à `/auth/login` et
    `/auth/register` (pas `/auth/token`, endpoint Swagger de debug, choix
    explicite de l'utilisateur). [api/auth_crypto.py](api/auth_crypto.py)
    génère une paire de clés en mémoire au démarrage du processus API —
    jamais persistée, régénérée à chaque redémarrage sans conséquence
    puisqu'elle ne protège que l'échange en cours, pas les comptes déjà en
    base — et expose la clé publique via `GET /auth/public-key`.
    [frontend/utils/auth_crypto_client.py](frontend/utils/auth_crypto_client.py)
    la récupère à chaque connexion, sans mise en cache, pour éviter un échec
    de déchiffrement après un redémarrage de l'API.
  - Vérifié de bout en bout par de vrais appels HTTP sur la stack Docker
    démarrée (register + login).
  - Limite assumée : seul le mot de passe est protégé, pas le reste des
    échanges (jeton JWT compris) ni `/auth/token`.

- [x] **Réseau privé étanche pour `database_api`** — résolu par le même
  changement Traefik : `database_api` n'a plus de section `ports:`, il n'est
  joignable qu'en interne (`http://database_api:8000`) et via
  `http://localhost/dbapi`.
- [x] **Clé de signature JWT en dur et divulguée** (voir section « Relecture
  du dossier complet » ci-dessous) — corrigé : fail-closed sur
  `JWT_SECRET_KEY` dans [api/auth_config.py](api/auth_config.py), nouvelle
  clé générée et posée dans le `.env` local, les 10 refresh tokens actifs
  émis sous l'ancienne clé ont été révoqués.
- [x] **Mémoire de conversation partagée entre tous les utilisateurs.** Bug
  trouvé en creusant l'item `InMemorySaver()` ci-dessous, plus grave que
  prévu : [api/modules/chat_service.py:86-96](api/modules/chat_service.py:86)
  calculait le `thread_id` depuis `chat_request.session_id`, un champ que
  `ChatRequest` ne définit pas — `getattr` échouait donc toujours et
  retombait sur une constante fixe `"thread_de_test_fixe_12345"` : tous les
  utilisateurs partageaient la même mémoire de conversation, et
  `/chat/response_stream` n'était protégé par aucune authentification.
  Corrigé : `/chat/response_stream` exige désormais un utilisateur
  authentifié (`Depends(get_current_user)`), et le `thread_id` est dérivé de
  son id (`f"user_{user.id}"`) — un thread par utilisateur. Frontend mis à
  jour pour transmettre l'access token (`Authorization: Bearer`) sur cet
  appel, déjà disponible en session puisque le login est obligatoire pour
  accéder au chat.

## 🟠 Tests — couverture ≥ 80% (API IA, API Database, UI)

**Remesuré le 4 septembre 2026** (`uv run pytest --cov=. --cov-report=term`
dans chaque sous-projet) — les trois entrées ci-dessous étaient périmées :

| Composant | Couverture réelle | Cible du cahier des charges |
|---|---|---|
| `agents` | 95% | — (non visé explicitement) |
| `database` (API Database) | **81%** | 80% ✅ |
| `api` (API IA) | **93%** | 80% ✅ |
| `frontend` (UI) | **57%** sur `utils/` + `components/` | 80% ❌ |

Chiffres `api` et `frontend` remesurés le 4 septembre 2026 après l'ajout des
tests d'authentification (64 tests : 35 sur `api/`, 38 sur `frontend/`).

- [x] `database` : entrée corrigée — 81%, et non 100%. Au-dessus de la cible.
- [x] `api` (API IA) : **74% → 93%** (96 tests). L'authentification, qui
  concentrait le manque, est désormais couverte :
  [auth_utils.py](api/auth_utils.py) 30% → **100%**,
  [auth_routes.py](api/auth_routes.py) 30% → **97%**,
  [auth_crypto.py](api/auth_crypto.py) → **100%**. Restent en dessous
  [main.py](api/main.py) 58% (câblage de démarrage) et
  [modules/chat_service.py](api/modules/chat_service.py) 38%.
- [ ] `frontend` (UI) : **46% → 57%** sur le code applicatif.
  [utils/auth_client.py](frontend/utils/auth_client.py) et
  [utils/auth_crypto_client.py](frontend/utils/auth_crypto_client.py) sont
  passés de **0% à 100%**. Il reste
  [components/auth_components.py](frontend/components/auth_components.py) à
  **0%** (97 instructions, formulaires Streamlit),
  [components/components.py](frontend/components/components.py) à 67% et
  [utils/api_client.py](frontend/utils/api_client.py) à 63% — c'est
  `auth_components.py` qui pèse le plus dans les 23 points manquants.
- [x] CI ([.github/workflows/docker.yml](.github/workflows/docker.yml)) :
  entrée périmée — lance déjà `uv sync` + `uv run pytest --cov=...` pour les
  **quatre** sous-projets (`agents`, `api`, `database`, `frontend`), chacun
  avec ses propres artefacts de couverture.
- [ ] **Le seuil CI ne protège pas la cible.** `--cov-fail-under=40` sur les
  quatre sous-projets, alors que le cahier des charges demande 80% pour les
  deux API et l'UI. À remonter à 80 une fois `api` et `frontend` au niveau —
  le remonter avant ferait échouer la CI sur un défaut déjà connu.
- [x] `agents` : couverture réelle passée de 49% à 95%
  (`uv run pytest --cov=. --cov-report=term-missing`, 178 tests). Trois
  fichiers de test portaient `pytestmark = pytest.mark.skip(reason="Временно
  отключено")` depuis le commit `d61aa9b` (« fix: tests agents », même jour que
  l'extension CI aux quatre sous-projets), masquant des tests réellement cassés
  plutôt que de les corriger :
  - [tests/test_nodes_rag.py](agents/tests/test_nodes_rag.py) et
    [tests/test_vector_tools.py](agents/tests/test_vector_tools.py) appelaient
    `.func(...)` sur des `@tool` **async** (`search_vector_node`,
    `hydratation_node`, `format_cards_node`, `load_film_node` dans
    `nodes_rag.py` ; `search_vector_catalog`, `search_similar_movies_by_id`
    dans `vector_tools.py`) — `.func` ne porte que la forme synchrone d'un
    `@tool` et vaut `None` sur un `@tool async def`, d'où
    `TypeError: 'NoneType' object is not callable`. Corrigé en `.ainvoke({...})`
    + `async def test_...` + `@pytest.mark.asyncio`, seule forme déjà en usage
    dans `test_sql_tools.py`.
  - Les tests de `validation_node` et `validation_film_node` patchaient
    `agents.nodes_rag.structured_llm` alors que ces deux nœuds appellent
    `validation_llm` (deux instances LLM distinctes importées dans
    `nodes_rag.py`) : le mock n'interceptait rien, et l'appel réel — non
    mocké — bloquait la suite plus de deux minutes. Corrigé en patchant
    `validation_llm`.
  - Les tests de `format_cards_node` patchaient un `agents.nodes_rag.db_session`
    qui n'existe plus dans le module (`patch` lève une `AttributeError`
    immédiate sans `create=True`) ; le nœud appelle directement
    `get_films_short_by_ids`, désormais le bon patch cible.
  - [tests/test_nodes_wikipedia.py](agents/tests/test_nodes_wikipedia.py) :
    un seul test cassé, qui vérifiait une troncature du synopsis Wikipedia à
    3000 caractères alors que le code tronque à 10000
    (`nodes_wikipedia.py:186`) — et cette valeur seule n'est de toute façon
    jamais observable : un second plafond (`MAX_SYNTHESIS_CONTEXT_CHARS =
    8000`, tout le contexte envoyé au LLM, tous films confondus) s'applique
    après coup et masque le premier dès qu'un seul synopsis dépasse 8000
    caractères. Réécrit pour vérifier ce second plafond, seul réellement
    observable en sortie.
  - `tests/test_vector_tools.py` appelait aussi la Database API réelle
    (`filter_films_by_criteria`, URL par défaut `http://database_api:8000`,
    résolvable seulement depuis le réseau Docker) et Ollama via
    `http://host.docker.internal:11434` (résolvable seulement depuis un
    conteneur) pour l'embedding de la requête — deux appels réseau réels dans
    ce qui doit rester une suite unitaire (`rules/tests-python.md` §
    Isolation ; CLAUDE.md confirme qu'aucun test d'intégration Docker Compose
    n'existe pour l'instant). Corrigé en mockant `OLLAMA_CLIENT_EMBEDD` et
    `get_films_short_by_ids`, en ne laissant réelle que la recherche FAISS
    elle-même. **Correction suivante (même jour) :** cette recherche
    s'appuyait encore sur l'index et le mapping réels chargés depuis
    `faiss_data/` — un dossier ignoré par git (l'index est embarqué dans
    l'image Docker `api`, jamais commité, voir CLAUDE.md § Pièges déjà
    payés) et donc absent d'un checkout CI frais. 14 tests passaient en
    local et échouaient systématiquement sur GitHub Actions
    (`FileNotFoundError`). Corrigé en construisant l'index FAISS de manière
    synthétique en mémoire (graine fixe, dimension 1024, volume dépassant
    `SMALL_POOL_THRESHOLD` pour couvrir aussi le scénario grand pool), sans
    dépendre d'aucun fichier du dépôt — conforme à `rules/tests-python.md` §
    Fixtures. Vérifié en reproduisant la condition CI (`faiss_data/` retiré
    localement) avant de committer.
  - Cinq tests (`test_build_filtered_ids_*`) appelaient une fonction
    `_build_filtered_ids` et un `db_session` jamais importables depuis
    `agents/` (import commenté, fonction inexistante dans
    `agents/tools/sql_tools.py` — la logique de filtrage réelle,
    `get_filtered_ids`, vit dans `database/queries.py`, un sous-projet
    indépendant qu'`agents/` n'installe pas). Supprimés : ils testaient du
    code d'un autre sous-projet, inatteignable par construction ici.
    **Gap réel laissé ouvert** : `get_filtered_ids` (`database/queries.py`)
    n'a aucun test dans `database/tests/test_queries.py` — à couvrir dans ce
    sous-projet, pas dans `agents/`.
  - Reste non couvert dans `agents/` : `chat_terminal.py` (0%, CLI manuelle
    hors scope), `tools/vector_tools.py` lignes 248-384
    (`_run_manual_tests`, harnais de vérification manuelle appelé uniquement
    depuis son `if __name__ == "__main__":`, pas de la logique métier), et
    quelques branches défensives de `nodes_rag.py` (197-200, 818, 928-935,
    953).

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

- [x] Templates d'issue GitHub — ajoutés le 4 septembre 2026 sous
  [.github/ISSUE_TEMPLATE/](.github/ISSUE_TEMPLATE) : `anomalie.yml`
  (étapes de reproduction, attendu, observé et commit obligatoires),
  `tache.yml` (besoin et critères de fin obligatoires) et `config.yml` qui
  désactive les issues en texte libre. Les deux formulaires reprennent
  l'échelle de priorité 🔴/🟠/🟡 de ce fichier et la liste des composants du
  dépôt, pour que le tri d'une issue et celui du TODO se lisent pareil.
  - Reste à faire côté GitHub, hors dépôt : ni les libellés ni la vue projet ne
    sont versionnables. `bug` et `enhancement` sont créés par défaut avec tout
    dépôt, donc utilisables tels quels ; un libellé absent est ignoré en
    silence par GitHub, sans erreur visible.

## Dette déjà connue (hors scope Partie 3, cf. CLAUDE.md)

- [x] **Déjà corrigé, entrée obsolète.** `SUPABASE_PASSWORD` dans
  [database/connection.py](database/connection.py) refuse déjà le démarrage
  (`if "<MOT_DE_PASSE>" in DATABASE_URL: raise ValueError(...)`) — vérifié via
  `git log` (correctif déjà en place, commit `4f948ad`). Le `CLAUDE.md` reste à
  corriger séparément (sa section « Dette existante » décrit encore l'ancien
  comportement).

---

# Relecture du dossier complet — 3 septembre 2026

Observations issues d'une relecture de **l'intégralité du répertoire de
travail**, fichiers non suivis par git compris (`.env` locaux, `.dockerignore`,
Dockerfiles, configuration du hook, artefacts sur disque) — donc de choses
qu'une lecture du seul contenu commité ne montre pas.

## 🔴 Sécurité — critique, non listé jusqu'ici

- [x] **Clé de signature JWT en dur dans le dépôt, et effectivement utilisée.**
  Corrigé le 3 septembre 2026 — voir l'entrée en tête de la section
  « 🔴 Sécurité (Épilogue MLOps) » plus haut pour le détail du correctif.
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

- [x] **Les `uv.lock` sont copiés dans les images puis jamais utilisés.**
  Les trois Dockerfiles installent désormais depuis le lock
  (`uv sync --frozen --no-dev --no-install-project`,
  [Dockerfile.api:33](Dockerfile.api:33),
  [Dockerfile.database:29](Dockerfile.database:29),
  [Dockerfile.frontend:18](Dockerfile.frontend:18)), la liste manuelle
  `uv pip install --system` a disparu.
  - La dérive était réelle : `database/pyproject.toml` ne déclarait ni
    `fastapi` ni `uvicorn` alors que `database/main.py` les importe — masqué
    jusqu'ici par la liste manuelle qui les incluait à la main. Corrigé par
    `uv add "fastapi>=0.136.3" "uvicorn[standard]>=0.49.0"` dans `database/`.
  - Autre dérive : `database/pyproject.toml` déclare `psycopg2` (compilation
    depuis les sources) alors que la liste manuelle installait
    `psycopg2-binary` (précompilé), masquant le besoin de `build-essential` +
    `libpq-dev`. Ajoutés à [Dockerfile.database](Dockerfile.database).
  - Vérifié : les trois images buildent et démarrent en `(healthy)`
    (`docker compose ps`), `/health` et `/db/health` répondent, import direct
    de `agents.graph`/`api.main` confirmé dans le conteneur `api`.

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

- [x] `sqlalchemy` installé deux fois dans [Dockerfile.database:27](Dockerfile.database:27)
  et [Dockerfile.database:33](Dockerfile.database:33) (`sqlalchemy` puis
  `SQLAlchemy`) — sans effet mais signe que la liste manuelle n'est pas relue.
  Résolu de fait avec la liste manuelle disparue : `sqlalchemy` n'apparaît
  plus qu'une fois, dans [database/pyproject.toml](database/pyproject.toml).

- [x] Incohérence de lancement entre images : `api` et `database` démarrent via
  `uv run uvicorn ...` alors que les dépendances ont été installées avec
  `uv pip install --system` (aucun projet uv à `/app`), tandis que `frontend`
  appelle `streamlit` directement. Un seul mécanisme suffirait.
  Unifié : les trois images installent leurs dépendances via `uv sync` dans un
  vrai `.venv` d'image, et démarrent via `uv run` — `--project api`/
  `--project database` pour ces deux-là (le code source vit à `/app`, un cran
  au-dessus du projet uv), directement pour `frontend` (`pyproject.toml`/
  `uv.lock` copiés à la racine `/app` du conteneur).

## 🟠 Trois sources de vérité pour les secrets

- [ ] `.env` (racine), `database/.env` et `agents/tools/.env` déclarent **les
  mêmes** identifiants Supabase/Postgres, dupliqués à l'identique. Trois copies
  divergent, et c'est la mauvaise qui reste (socle § DRY). Les sous-projets
  appellent tous `load_dotenv()` sans chemin explicite, donc la copie prise
  dépend du répertoire courant au lancement — comportement différent entre
  `docker compose` (racine) et un `uv run` depuis `database/`.
  → Un seul `.env` à la racine, chargé par chemin explicite.

- [ ] **Partiellement résolu (par Hanna, sur `dev`), reste ouvert pour le
  reste.** `.env.example` désynchronisé du code, dans les deux sens :
  - **Corrigé** : `JWT_SECRET_KEY` (+ `JWT_ALGORITHM`, durées d'expiration)
    est désormais présent et documenté comme obligatoire dans `.env.example`,
    **et** effectivement défini dans le `.env` réel de ce poste (vérifié) —
    le cas « présent dans le modèle, absent du `.env` réel » signalé en § 🔴
    Sécurité est clos.
  - **Toujours absentes du modèle**, utilisées par le code : `API_URL`,
    `DATABASE_API_URL`, `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`,
    `LANGFUSE_SECRET_KEY`, `LANGGRAPH_STRICT_MSGPACK`.
  - **Toujours dans le modèle, lues nulle part** : `POSTGRES_USER/PASSWORD/DB/HOST/PORT`
    (aucun service Postgres local dans `docker-compose.yml` — le bloc est
    commenté), `SUPABASE_PROJECT`, `SUPABASE_PUBLISHABLE_KEY`,
    `OLLAMA_MODELS_PATH`.
  - Revérifié le 3 septembre 2026.

## 🟠 Outillage déclaré mais inexistant

- [x] **`ruff` n'est une dépendance d'aucun des quatre sous-projets.**
  Ajouté en dépendance de dev (`uv add --dev ruff`) dans les quatre
  `pyproject.toml`, avec une configuration minimale identique
  (`[tool.ruff]` : `line-length = 88`, `target-version = "py311"` ;
  `[tool.ruff.lint]` : `select = ["E", "W", "F", "I"]`). `D` (docstrings)
  volontairement omis pour l'instant, en commentaire dans chaque fichier :
  l'activer sur le code existant ferait échouer le hook sur la quasi-totalité
  des fichiers (mesuré : 118+305+81+387 = 891 violations rien qu'avec
  `E,W,F,I`) — à revoir après une passe de mise en conformité des docstrings
  dédiée.

- [x] **Le hook pre-commit est actif mais sa configuration est le modèle
  d'exemple, non adaptée au projet.** [.githooks/standards.conf](.githooks/standards.conf)
  mis à jour :
  - `INTERDIRE_LOGGING=1`, `MODULE_LOGGER="logger.py"`, `RUFF=1`.
  - `INTERDIRE_PRINT` laissé à `0`, avec la raison en commentaire dans le
    fichier : 165 `print()` préexistants dans une douzaine de fichiers
    (`start.py`, `test_auth.py`, `database/faiss_service.py`, etc.) —
    l'activer bloquerait tout commit futur qui les touche ; à revoir après
    une passe de nettoyage dédiée.
  - `CHEMINS_EXCLUS=""` et `MOTIFS_INTERDITS="*.env"` : les valeurs d'exemple
    (`Reference/*`, `donnees/*`, `sources/*`, `.xlsx`...) ne correspondent à
    rien dans ce dépôt ; `*.env` (avec joker) couvre le `.env` racine et ceux
    des sous-dossiers, contrairement au motif littéral précédent.
  - Le dépôt n'ayant pas de `pyproject.toml` à la racine, [.githooks/pre-commit](.githooks/pre-commit)
    a été adapté pour lancer `uv run --project <sous-projet> ruff check`/
    `ruff format --check` séparément sur `api/`, `agents/`, `database/`,
    `frontend/` selon le sous-projet de chaque fichier staged, plutôt qu'un
    unique appel `uv run ruff` depuis la racine (qui n'aurait trouvé aucune
    configuration).
  - Vérifié en conditions réelles : `bash .githooks/pre-commit` sur un commit
    réel touchant les quatre sous-projets passe (`EXIT=0`) après correction
    des violations ruff préexistantes dans les fichiers concernés
    (`agents/graph.py`, `database/faiss_service.py`,
    `database/tests/test_faiss_service.py`).

## 🟠 Duplication de code — `api/schemas.py` est un fork périmé de `shared/schemas.py`

- [x] **Corrigé.** [api/schemas.py](api/schemas.py) réduit aux six schémas
  d'authentification (`UserRegister`, `UserLogin`, `Token`, `TokenRefresh`,
  `UserResponse`, `AuthResponse`), les 15 doublons supprimés. En-tête réécrit
  pour expliquer la répartition avec `shared/schemas.py`.
  [api/auth_routes.py](api/auth_routes.py) importe désormais `ErrorResponse`
  depuis `shared.schemas`. Docstring corrigée dans le même lot :
  [agents/router.py:110](agents/router.py:110) référence maintenant
  `shared.schemas (AgentState)`.

## 🟠 Code mort et en-têtes périmés (suite de la section « Dette de lisibilité »)

- [x] **Corrigé.** [agents/nodes_rag.py](agents/nodes_rag.py) : `BASE_DIR` et
  `FAISS_INDEX_PATH` supprimés (inutilisés, confirmé par recherche de
  référence). En-tête réécrit — supprime la description des « nœuds
  principaux à implémenter » sous des noms abandonnés, décrit les nœuds
  réellement présents et corrige les dépendances listées.
- [x] `agents/state.py` : confirmé supprimé du disque et de l'index git — la
  réserve « à faire manuellement » de la section précédente est levée.
- [x] **Corrigé.** [api/README.md](api/README.md) était vide (0 octet) ;
  rédigé (objet du module, arborescence, renvoi vers `shared/schemas.py`,
  démarrage, tests), sur le modèle de `database/README.md`.

## 🟡 Scripts et tests orphelins à la racine

- [x] **Rangés dans [scripts/](scripts/)** (choix validé avec l'utilisateur).
  [start.py](scripts/start.py), [start_with_auth.sh](scripts/start_with_auth.sh),
  [start_with_auth.bat](scripts/start_with_auth.bat) déplacés par `git mv`,
  chemins internes corrigés pour le nouvel emplacement (racine du dépôt un
  cran au-dessus). `test_auth.py` → [scripts/verifier_auth.py](scripts/verifier_auth.py)
  et `test_synopsis_enrichment.py` →
  [scripts/verifier_synopsis_enrichment.py](scripts/verifier_synopsis_enrichment.py) :
  renommés hors du motif `test_*.py` (plus de collecte accidentelle par
  pytest), lanceurs mis à jour pour référencer le nouveau chemin.
  `frontend/start.py` non touché : lanceur propre à ce sous-projet, hors
  scope de ce doublon-là.
- [x] **Supprimé.** [frontend/test_app.py](frontend/test_app.py) confirmé
  superflu : ses classes (`TestApiClient`, `TestComponents`, `TestIntegration`)
  sont une ébauche antérieure, moins complète, de ce qui vit désormais
  proprement dans `frontend/tests/test_api_client.py`, `test_components.py`,
  `test_integration.py`.
- [x] **Corrigé.** `api/tests/test_chat_servise.py` renommé
  `test_chat_service.py` (`git mv`, pas de changement de contenu).
- [x] **Renommé, pas fusionné.** Lecture complète des deux fichiers : ce ne
  sont **pas** de vrais doublons — `api/tests/test_wiki.py` teste la route
  FastAPI (`TestClient`), `agents/tests/test_wiki.py` teste l'outil brut. Les
  fusionner aurait perdu une couche de couverture. Renommé en
  [api/tests/test_wikipedia_route.py](api/tests/test_wikipedia_route.py) pour
  lever l'ambiguïté du nom.
- [x] **Corrigé.** `frontend/pytest.ini` supprimé, son contenu fusionné dans
  `frontend/pyproject.toml` (`[tool.pytest.ini_options]`), aligné sur les
  trois autres sous-projets. Vérifié : `uv run pytest -q` depuis `frontend/`
  charge bien `pyproject.toml` (`configfile: pyproject.toml`) et les tests
  passent.

## 🟡 Déclarations de dépendances incohérentes entre sous-projets

- [x] **Supprimé.** `frontend/requirements.txt` retiré : `uv.lock` est la
  seule source de vérité, conforme à `.claude/rules/python.md`.
- [x] **Corrigé.** `pytest-asyncio` déplacé en dépendance de dev
  (`uv remove pytest-asyncio && uv add --dev pytest-asyncio`) dans
  `api/pyproject.toml` et `agents/pyproject.toml`.
- [x] **Corrigé.** `supabase` retiré d'`api/pyproject.toml`
  (`uv remove supabase`, 24 paquets transitifs en moins) — confirmé inutilisé
  par recherche de référence dans tout le dépôt.
- [x] **Unifié sur `psycopg2` (source).** `api/pyproject.toml` déclarait
  `psycopg2-binary` ; remplacé par `psycopg2` pour s'aligner sur `agents/` et
  `database/` — c'est le choix recommandé par le projet en production
  (`psycopg2-binary` n'est officiellement conseillé que pour le
  développement/test). `Dockerfile.api` installait déjà `build-essential`
  pour faiss : `libpq-dev` ajouté pour compléter la compilation, sans nouveau
  besoin de toolchain. `uv sync` et `uv run pytest` vérifiés dans `api/`
  après le changement.
- [x] **Corrigé.** `dotenv` remplacé par `python-dotenv` dans `agents/` et
  `database/` (`uv remove dotenv && uv add python-dotenv`) — les deux
  exposent la même API (`from dotenv import load_dotenv`), aucun code
  appelant à modifier.
- [x] **Corrigé.** Les périmètres `[tool.setuptools]`/`packages.find`
  réalignés sur les imports réels (vérifiés par recherche de référence) :
  `agents/pyproject.toml` empaquette désormais `["agents", "database", "api",
  "shared"]` (retiré `frontend`, jamais importé nulle part ; ajouté `shared`,
  omis alors qu'`agents` l'importe) ; `database/pyproject.toml` empaquette
  `["database", "shared"]` (retiré `agents`, que `database` n'importe pas) ;
  `api/pyproject.toml` inclut désormais aussi `shared*`. `shared/` était
  omis des trois déclarations bien qu'importé par les trois sous-projets —
  bug réel au-delà du simple chevauchement signalé initialement.
- [x] **Corrigé.** `frontend/.python-version` créé (`3.11`), aligné sur les
  trois autres sous-projets.
- [x] **Corrigé.** `api/monitoring/__init__.py` créé, sur le modèle de
  `api/modules/__init__.py`.

## 🟡 Monitoring — couplages fragiles

- [x] **Corrigé (par Hanna, commit sur `dev`).** Le [docker-compose.yml](docker-compose.yml)
  racine déclare désormais `name: horragor_2` en tête de fichier (commentaire
  explicite sur cette correction), ce qui fixe le nom du projet Compose
  indépendamment du nom du répertoire de clone. `monitoring/docker-compose.yml:233`
  continue de nommer en dur le réseau externe `horragor_2_horragor_net`, mais
  ce nom est désormais garanti correct par le `name:` fixé côté stack
  principale, plutôt que dépendant accidentellement du nom du dossier.
  Revérifié le 3 septembre 2026 après les commits d'Hanna sur `dev`.
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
- [x] `uid: afwve5oglmvwgb` ajouté en dur dans
  [monitoring/grafana/provisioning/datasources/prometheus.yml](monitoring/grafana/provisioning/datasources/prometheus.yml) :
  confirmé référencé 6 fois par
  [monitoring/grafana/dashboards/horragor.json](monitoring/grafana/dashboards/horragor.json) —
  sans lui, le provisioning en génère un aléatoire à chaque démarrage et
  casse ces références. Commité (`fix : fixe l'UID du datasource Prometheus
  dans Grafana`).

## 🟡 `.gitignore` — motifs trop larges

- [x] **Corrigé.** `bin/`, `lib/`, `include/`, `env/` restreints à la racine
  (`/bin/`, `/lib/`, `/include/`, `/env/`), même convention que `/build/` et
  `/dist/`. `.pytest_cache/` ajouté au passage (traînait, non ignoré).
  **Bug supplémentaire trouvé et corrigé, hors périmètre initial de cet
  item** (socle § priorité 1 : un risque de perte de données/incohérence se
  corrige même hors scope) : un bloc de marqueurs de conflit Git non résolu
  (`<<<<<<< HEAD` / `=======` / `>>>>>>> 83ad3f4...`) était committé dans le
  fichier, neutralisant silencieusement les règles `coverage*.xml`/
  `htmlcov*/` qu'il encadrait. Marqueurs retirés, les deux jeux de règles
  conservés (ce n'était pas un vrai conflit de contenu, juste une fusion non
  terminée).
- [x] `*.env` : confirmé volontaire, rien à corriger — laissé tel quel comme
  demandé par l'entrée d'origine.
- [x] **Entrée obsolète.** `HorRAGor BOT Partie 3.pdf` est en réalité déjà
  suivi (`git ls-files "*.pdf"` le confirme, commité dans `83ad3f4`) : le
  `??` décrit dans cet item ne reflète plus l'état du dépôt. Aucune action
  `.gitignore` nécessaire.

## 🟡 Artefacts régénérables commités

- [x] **Corrigé.** Quatre copies du diagramme du graphe étaient suivies :
  `HorRAGor_graph.png` (racine), `api/HorRAGor_graph.png`,
  `docs/HorRAGor_graph.png` (les trois **identiques**, 168 Ko chacune) et
  `agents/HorRAGor_graph.png` (32 Ko, version périmée) — idem pour
  `graph.mmd`. Générés au démarrage par
  [agents/graph.py:313-317](agents/graph.py:313) dans le répertoire courant
  du processus, donc régénérables. `api/graph.mmd`/`HorRAGor_graph.png`,
  `agents/graph.mmd`/`HorRAGor_graph.png` (périmés) et
  `docs/graph.mmd`/`HorRAGor_graph.png` (doublon inutilisé —
  [docs/source/langgraph.rst:9](docs/source/langgraph.rst:9) référence en
  réalité la copie racine, `../../HorRAGor_graph.png`) retirés du dépôt
  (`git rm`). Seule la copie racine reste versionnée : c'est celle que la CI
  embarque dans la doc Sphinx sans étape de régénération. Les trois autres
  emplacements ajoutés au `.gitignore` pour qu'une régénération locale
  n'y recrée pas de doublon suivi.
- [x] **Corrigé.** `agents/Capture d’écran 2026-06-06 000734.png` (capture de
  travail, apostrophe typographique dans le nom) retirée du dépôt.
- [x] **Corrigé.** `MERISE HORRAGOR.pptx` (4,5 Mo) et
  `HorRAGor_presentation.pptx` retirés du dépôt (`git rm`) : binaires de
  présentation non diffables, non référencés par aucun fichier du dépôt,
  alourdissant chaque clone et chaque contexte de build.
- [x] **Corrigé.** `slide4_corrections.png` / `slide6_corrections.png`
  supprimés du répertoire de travail (n'étaient pas suivis, déjà ignorés
  depuis [.gitignore:73](.gitignore:73)).

## 🟡 Documentation — dérive constatée

- [x] **Corrigé.** L'arborescence de [README.md](README.md:52) listait encore
  `agents/state.py` (fichier supprimé) et omettait des modules existants —
  ajoutés : `agents/config.py`, `agents/chat_terminal.py`,
  `api/auth_config.py`, `api/auth_crypto.py`, `api/auth_routes.py`,
  `api/auth_utils.py`, `api/schemas.py`, `database/create_auth_tables.py`,
  `shared/embeddings.py`, ainsi que `scripts/` (lanceurs déplacés hors
  racine, cf. section « Scripts et tests orphelins »).
- [x] **Corrigé.** Deux QUICKSTART concurrents :
  [QUICKSTART.md](QUICKSTART.md) (chemin Docker, à jour) et
  `frontend/QUICKSTART.md` (chemin local, obsolète — référençait
  `requirements.txt` déjà supprimé, un contrat d'API périmé (`POST /chat`
  au lieu de `/chat/response_stream`), une structure de fichiers non
  auth-aware, mise en forme markdown cassée). `frontend/QUICKSTART.md`
  supprimé (`git rm`) : `QUICKSTART.md` fait foi pour le lancement,
  [frontend/README.md](frontend/README.md) reste la référence pour un
  lancement local hors Docker du seul frontend.
- [ ] **Conservé, sur demande explicite.** `CHANGELOG_FLAVIE.md` — journal de
  travail nominatif redondant avec l'historique git pour sa partie diff, et
  référençant un `EPIC_FLAVIE_RESUME.md` inexistant. Une première
  suppression a fait perdre une information réelle non documentée ailleurs
  (§ Points de vigilance : pas de persistance des synopsis Wikipedia en base
  pour raison de droits d'auteur, pas de cache) — recapturée dans l'en-tête
  de [agents/nodes_wikipedia.py](agents/nodes_wikipedia.py:9) avant que le
  fichier ne soit restauré. Le fichier reste donc en l'état, sans
  suppression ni fusion dans un changelog non nominatif tant que ce n'est
  pas redemandé.
- [x] **Corrigé.** Sphinx ne documentait ni `frontend/` ni `shared/` :
  [docs/source/frontend.rst](docs/source/frontend.rst) (clients API,
  authentification, chiffrement du mot de passe, composants d'affichage) et
  [docs/source/shared.rst](docs/source/shared.rst) (schémas Pydantic,
  embeddings) ajoutés, référencés dans
  [docs/source/index.rst](docs/source/index.rst). `frontend/` important ses
  propres modules en chemin relatif à lui-même (`from utils.x import y`,
  comme le fait Streamlit au lancement) plutôt qu'en `frontend.utils.x`,
  [docs/source/conf.py](docs/source/conf.py) ajoute `frontend/` à `sys.path`
  pour que l'autodoc résolve ces imports, sur le même principe que l'ajout
  déjà en place pour la racine du dépôt. `streamlit` n'étant pas installé
  dans l'environnement qui construit la doc en CI (`uv run --project ../api`
  ne sync que les dépendances d'`api/`), il est simulé via
  `autodoc_mock_imports = ["streamlit"]` plutôt que d'ajouter une dépendance
  supplémentaire à l'environnement de build. `app.py` volontairement exclu
  de l'autodoc (effets de bord Streamlit au niveau module — configuration de
  page, appels `st.*` hors fonction) : seuls les modules réutilisables sont
  documentés (clients, composants). Vérifié par un build Sphinx complet en
  local (`uv run --project api sphinx-build -E -b html docs/source <sortie>`)
  : `build succeeded`, symboles `frontend.utils.auth_client.login_user`,
  `frontend.utils.auth_crypto_client.encrypt_password`,
  `shared.schemas.AgentState` bien présents dans le HTML généré.

## 🟡 CI — angles morts confirmés en relisant le workflow

- [x] **Corrigé le 4 septembre 2026.** Un job `lint` a été ajouté à
  [.github/workflows/docker.yml](.github/workflows/docker.yml), en parallèle du
  job `test` (`docker` dépend désormais des deux). Il rejoue par sous-projet les
  commandes déclarées dans le [CLAUDE.md](CLAUDE.md), à `--check` près : une CI
  vérifie, elle ne reformate pas (`rules/cicd.md`). Structure choisie en job
  séparé plutôt qu'en étapes du job `test` : un échec de lint sur `agents`
  aurait sinon arrêté le job et masqué les tests des trois autres sous-projets.

  Le lint était vert le jour où il a été branché : les quatre sous-projets ont
  été mis en conformité au préalable (77 + 247 + 72 + 361 = 757 violations, plus
  41 fichiers non formatés). Le détail des choix de suppression figure dans les
  `[tool.ruff.lint.per-file-ignores]` de chaque `pyproject.toml`, chacun avec sa
  justification.

- [x] **Le lint a effectivement cassé le jour suivant (4 septembre 2026,
  run `33853899120`), confirmant que le job sert à quelque chose.** `ruff
  check` passait mais `ruff format --check` échouait sur
  [components/components.py](frontend/components/components.py) et
  [tests/test_components.py](frontend/tests/test_components.py) — deux
  fichiers non reformatés, entrés via un merge (`a4b30b6 merge: mettre la
  branche à jour avec dev`, Roxiina). Corrigé par un simple
  `uv run ruff format .` dans `frontend/` (aucun changement de logique).
  **Cause probable, non confirmée :** un merge automatique (fast-forward ou
  sans conflit) n'invoque pas le hook `pre-commit` — seul un commit le
  déclenche. Si `core.hooksPath` n'a pas non plus été activé sur le poste
  d'origine (`git config core.hooksPath .githooks`, à faire une fois par
  machine selon le `CLAUDE.md`), un fichier non formaté peut atteindre `dev`
  sans qu'aucun garde-fou local ne le voie — seule la CI l'attrape, après
  coup. Pas d'action corrective ouverte : la CI a joué son rôle de dernier
  filet ; à surveiller si le cas se répète.

- [x] **Trou de périmètre trouvé et comblé au passage.** Huit fichiers Python
  n'étaient vérifiés par personne : ni par le hook `pre-commit` (qui ne boucle
  que sur `SOUS_PROJETS_RUFF="api agents database frontend"`), ni par une
  configuration ruff (il n'y en avait aucune à la racine, et ruff résout sa
  configuration par ancêtre le plus proche). Il s'agissait de
  [logger.py](logger.py), [shared/](shared/) (3 fichiers, importés par les
  quatre sous-projets), [scripts/](scripts/) (3) et
  [docs/source/conf.py](docs/source/conf.py) — 84 violations. Un
  [ruff.toml](ruff.toml) racine les couvre désormais, avec une étape CI dédiée.
  Ce n'est volontairement pas un `pyproject.toml` : le `CLAUDE.md` interdit d'en
  créer un à la racine.

- [ ] **Le hook `pre-commit` reste aveugle sur ces huit fichiers.** Le
  `ruff.toml` racine et la CI les couvrent, mais `SOUS_PROJETS_RUFF` est codé en
  dur dans [.githooks/pre-commit](.githooks/pre-commit), qui est une copie du
  fichier partagé `.claude/standards/hooks/pre-commit` : l'étendre suppose de
  remonter la modification dans `standards-code`, sinon elle sera écrasée à la
  prochaine mise à jour du sous-module. Conséquence en attendant : une
  modification de `logger.py` ou de `shared/` passe le commit et n'est
  rattrapée qu'en CI.
## 🟡 Suppressions ruff assumées — à lever dans une tâche dédiée

Trois catégories de violations n'ont pas été corrigées lors de la mise en
conformité du 4 septembre 2026, mais neutralisées par `per-file-ignores`
documentés. Chacune est un vrai écart, pas un faux positif.

- [ ] **E501 sur le texte des prompts** (`agents/prompts.py`, `router.py`,
  `nodes_rag.py`, `nodes_narrateur.py`, `nodes_wikipedia.py`,
  `tools/vector_tools.py`, `tools/wiki_tools.py` et trois fichiers de test) —
  160 lignes, toutes situées **à l'intérieur de chaînes** envoyées au LLM (la
  plus longue fait 257 caractères). Les replier insérerait des retours à la
  ligne dans la charge utile du modèle : aucun test ne couvre le comportement
  des prompts, donc le repli est une tâche à part, avec sa propre validation.
- [ ] **E501 sur le CSS/HTML** (`frontend/app.py`,
  `frontend/components/components.py`, `frontend/components/auth_components.py`)
  — 83 lignes, toutes dans des blocs injectés via
  `st.markdown(unsafe_allow_html=True)`. Les replier reviendrait à réécrire la
  feuille de style au détour d'une passe de lint.
- [ ] **F403 sur [shared/__init__.py](shared/__init__.py)** (`from .schemas
  import *`). Vérifié : **personne n'utilise ce ré-export** — les 20 imports du
  dépôt passent tous par `from shared.schemas import ...`. La ligne est donc du
  code mort, mais la supprimer change le contrat public du paquet : à faire
  dans une tâche dédiée plutôt qu'au détour du lint.

## 🟡 CI — angles morts confirmés en relisant le workflow (suite)

- [x] **Corrigé.** [.github/workflows/docker.yml](.github/workflows/docker.yml)
  calcule désormais un tag de canal (`CHANNEL_TAG`) selon `github.ref_name` :
  `latest` uniquement depuis `main`, `dev` depuis `dev`. Les trois images
  (api, database-api, frontend) taguent `:${{ github.sha }}` **et**
  `:${{ env.CHANNEL_TAG }}` au lieu de `:latest` inconditionnel — un `:latest`
  ne peut plus provenir de `dev`.
- [x] **Résolu indirectement (par Hanna, commits « fix tests agents » sur
  `dev`).** Le job `test` du workflow ne testait à l'origine que `agents` ;
  il exécute désormais `uv sync` + `uv run pytest --cov=... --cov-fail-under=40`
  séparément pour **agents, api, database et frontend**, chacun avec son
  upload de couverture. La structure de dépendance n'a pas changé (`docker`
  dépend toujours d'un seul job `test`), mais comme ce job couvre maintenant
  les quatre sous-projets, un échec de tests `api`/`database`/`frontend`
  bloque désormais bien la publication d'image — l'écart signalé n'existe
  plus. Revérifié le 3 septembre 2026.
