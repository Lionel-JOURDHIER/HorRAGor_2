---
paths:
  - "Dockerfile*"
  - "docker-compose*.yml"
  - "docker-compose*.yaml"
  - "compose.yml"
  - "compose.yaml"
  - "**/k8s/**"
  - "prefect.yaml"
---

# Conteneurs et orchestration — Docker, Compose, Kubernetes

<!-- Fait suite à rules/python.md § Structure d'un projet (Dockerfile à la
     racine, uv comme outillage) et rules/cicd.md (CI Gitea). Ce fichier
     couvre ce qui se passe une fois l'image construite : composition locale
     (Compose), orchestration de pipeline (Prefect), traitement asynchrone
     (Celery), passage à l'échelle (Kubernetes). Le cycle de vie du modèle
     lui-même reste dans rules/ml.md — ce fichier ne fait que le servir.

     Portée : un motif sans barre oblique s'applique déjà à tous les niveaux du
     dépôt, donc "Dockerfile*" couvre Dockerfile.dev comme docker/Dockerfile et
     un "**/" en plus serait redondant. "compose.yaml" est le nom par défaut de
     Compose v2, "**/k8s/**" attrape les manifestes en .yaml comme en .yml, y
     compris sous deploy/k8s/. -->

Un conteneur garantit qu'un service tourne à l'identique partout. Ce qui suit
ne porte pas sur cette garantie mais sur ce qui l'entoure : combien
d'instances, quelles données survivent à un arrêt, qui peut parler à qui.

## Dockerfile

- Image basée sur `python:<version>-slim`, `uv` copié depuis l'image officielle
  (`COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/`) plutôt
  qu'installé par un script téléchargé en `RUN`.
- `pyproject.toml` et `uv.lock` copiés et installés **avant** le reste du code
  (`COPY pyproject.toml uv.lock ./` puis l'installation, seulement ensuite
  `COPY . .`). Docker met en cache chaque étape : changer une ligne de code
  ne doit pas redéclencher une réinstallation complète des dépendances, seul
  un changement du lock le doit.
- `.dockerignore` exclut ce qui n'a aucune raison d'être dans l'image :
  `.git`, `.venv`, `tests/`, `docs/`, `htmlcov/`, `.pytest_cache/`,
  `.ruff_cache/`. Une image qui embarque `.venv` ou `.git` est plus lourde et
  peut exposer l'historique.
- Aucun secret, aucune variable d'environnement de déploiement figée dans le
  Dockerfile (`ENV DATABASE_URL=...`). Elle est injectée à l'exécution, par
  Compose ou Kubernetes — un `ENV` en dur devient vrai pour toutes les
  images construites depuis, y compris en local.
- **Un modèle entraîné ou un jeu de données ne se copie pas dans l'image**
  (`COPY modele.pkl .`) : il est monté en volume. Une image qui embarque un
  modèle doit être reconstruite à chaque nouvelle version du modèle, ce qui
  mélange deux cycles de vie qui n'ont rien à voir (le code change rarement,
  le modèle peut changer chaque semaine).

## Docker Compose — configuration et secrets

- `.env` versionné en `.env.example` (clés sans valeurs), `.env` réel dans
  `.gitignore` — même règle que `rules/python.md` § Configuration, appliquée
  ici au fichier que Compose lit.
- Une variable du `.env` n'atteint un service que si son bloc `environment:`
  la référence explicitement (`DATABASE_URL: ${DATABASE_URL}`). Il n'y a pas
  de variable globale partagée entre conteneurs : chaque service ne voit que
  ce qu'on lui a donné, et un service qui n'a pas besoin d'un identifiant ne
  le reçoit pas.
- Volume nommé pour tout ce qui doit survivre à `docker-compose down` :
  données de base, artefacts MLflow non externalisés vers un vrai stockage
  objet, modèles montés. Sans volume déclaré, l'état d'un conteneur disparaît
  à son arrêt — c'est le comportement par défaut, le volume est l'exception
  qui dit « ceci doit survivre ».
- `deploy.resources.limits.memory` sur tout service qui fait un vrai travail
  (API, worker, base) : sans limite, un conteneur qui fuit de la mémoire peut
  affamer les autres sur le même hôte.
- Réseau dédié pour isoler ce qui doit se parler de ce qui n'en a pas besoin
  (`networks:` avec seulement les services concernés) : par défaut, tous les
  services d'un même `docker-compose.yml` peuvent joindre n'importe quel
  autre, y compris une base de données qui ne devrait être visible que de
  l'API. Un réseau restreint coûte trois lignes de YAML et retire une classe
  entière d'accès non prévus, dans le même esprit que le CORS restreint et
  les rôles d'API décrits dans `rules/securite-api.md`.

## Reverse proxy — Traefik

<!-- Source : tuto-traefik.html (proxy vs reverse proxy, vocabulaire
     EntryPoint/Router/Service/Middleware, docker-compose + labels, socket
     Docker, dashboard, ACME, priorité des routers, réseaux multiples,
     cycle de vie des labels, compatibilité Docker 29, provider file,
     forwardauth, métriques). Le module 8 du même support — répliques,
     affinité de session, streaming — est en § séparé plus bas : il ne se
     manifeste qu'au-delà d'un conteneur unique. -->

- Aucun service applicatif ne publie de port (`ports:`) : un seul port
  publié dans tout le projet, celui du reverse proxy. Les services se
  joignent entre eux par nom sur le réseau Compose partagé — un conteneur
  qui n'a pas besoin d'être atteint depuis l'extérieur ne doit jamais
  l'être, dans le même esprit que le réseau restreint du § Docker
  Compose ci-dessus.
- Vocabulaire minimal : **EntryPoint** (où ça entre, `:80`), **Router**
  (règle de correspondance — `Host(...)`, `PathPrefix(...)`, combinables
  par `&&`), **Service** (le port interne du conteneur, jamais le port
  publié — s'y tromper donne un 502), **Middleware** (ce qui se passe entre
  les deux — `stripprefix`, `basicauth`, `ratelimit`).
- La priorité par défaut d'un router est la **longueur de sa règle** : la
  plus spécifique gagne, sans rien à déclarer. Et `PathPrefix` compare une
  **chaîne**, pas des segments de chemin : `/apidocs` correspond à
  `PathPrefix(/api)`. Quand la distinction compte, un `Path(...)` exact.
- Labels Docker = configuration dynamique relue à chaud, sans redémarrer le
  proxy. `traefik.enable=true` obligatoire sur chaque service à exposer —
  ignoré par défaut sinon.
- Les labels sont lus à la **création** du conteneur : `docker compose
  restart` redémarre sans recréer, donc sans relire. Une modification de
  label se prend par `docker compose up -d` (`--force-recreate` en cas de
  doute) — un label resté sans effet est presque toujours ça, pas une
  faute de syntaxe.
- Version du proxy épinglée, jamais `latest`, et **v3.6 au minimum** : les
  versions antérieures réclament une version de l'API Docker que Docker 29
  ne sert plus. Le proxy démarre normalement, ne découvre aucun conteneur,
  et tout répond 404 — dashboard compris.
- Un conteneur présent sur deux réseaux a deux adresses, et le proxy peut
  retenir celle qu'il n'atteint pas : 504 sur une configuration pourtant
  juste. Déclarer `--providers.docker.network` dès qu'un service est sur
  plus d'un réseau, ce qui est le cas courant quand la donnée a le sien en
  `internal: true`.
- Les noms de routers/services sont globaux au provider Docker, pas
  cloisonnés par projet Compose : deux projets qui nomment un router `api`
  se collisionnent (404 ou timeout). Contraindre par
  `--providers.docker.constraints` sur le label `com.docker.compose.project`
  pour rattacher chaque instance de Traefik à son seul projet.
- Le socket Docker monté dans le proxy (`/var/run/docker.sock`) équivaut en
  pratique à un accès administrateur de l'hôte — la découverte automatique
  en dépend, mais c'est la partie la plus sensible de l'architecture. Monter
  en lecture seule (`:ro`) réduit sans éliminer le risque ; en production,
  préférer un proxy de socket (type `docker-socket-proxy`) ou le provider
  `file` (configuration statique, sans accès au socket).
- Dashboard **jamais** en `--api.insecure=true` (topologie complète exposée
  sans authentification) : le router comme n'importe quel service, protégé
  par un middleware `basicauth`.
- `basicauth` protège un dashboard, pas une application : dès que le projet
  a son propre système d'authentification (`rules/securite-api.md`), c'est
  `forwardauth` qui interroge ce service avant de transmettre — 2xx laisse
  passer, avec les en-têtes d'identité renvoyés par le service d'auth, et
  toute autre réponse est renvoyée telle quelle sans que le service protégé
  soit atteint. Réimplémenter la vérification dans chaque service ne passe
  pas à l'échelle ; en contrepartie le service d'auth devient un point de
  passage obligé, sa latence et sa disponibilité comptent pour tout ce
  qu'il protège.
- Exposer une API sous `app.localhost/api` élimine le CORS par construction
  (même origine) plutôt que de le corriger — préférer ce routage au
  middleware `headers` (CORS), qui reste un repli pour les cas où les deux
  origines ne sont pas maîtrisables (app mobile, intégration tierce) ; la
  politique CORS elle-même reste celle de `rules/securite-api.md` §
  Durcissement.
- Le `ratelimit` du proxy est un niveau différent, complémentaire, du
  `slowapi` applicatif de `rules/securite-api.md` : à poser devant toute
  route d'inférence, avant même l'authentification.
- HTTPS géré par le proxy (certificats ACME/Let's Encrypt), applications en
  HTTP en interne — à poser dès qu'un domaine public existe, pas seulement
  en environnement de démonstration.
- Un certificat n'appartient à aucun conteneur : aucun label ne peut le
  déclarer. C'est le provider `file` qui porte la configuration TLS, en
  parallèle du provider Docker — les deux tournent ensemble et leurs
  configurations fusionnent.
- Traefik ne sert pas de fichiers statiques : un front statique reste
  derrière un nginx, que le proxy route comme n'importe quel autre service.
- Point d'entrée unique = point de défaillance unique, assumé : en
  production, plusieurs exemplaires du proxy derrière un répartiteur.
- Diagnostic, dans cet ordre : le proxy ne plante presque jamais, il ignore
  en silence ce qu'il ne comprend pas. D'abord ses **logs**, puis les
  **routes qu'il connaît réellement** — une route absente de cette liste ne
  sera jamais trouvée côté navigateur, inutile de chercher ailleurs —, puis
  les **logs d'accès** (`--accesslog=true`), les seuls à dire ce qui est
  réellement arrivé à chaque requête.
- Codes de retour : 404 = route inconnue du proxy (`traefik.enable`
  manquant, service hors du réseau du proxy, règle mal écrite, ou noms de
  router qui ne concordent pas d'une ligne de label à l'autre) ; 502 =
  route connue, application injoignable (port de service faux, ou
  application qui écoute sur `127.0.0.1` au lieu de `0.0.0.0` dans le
  conteneur) ; 504 = le plus souvent le conteneur à deux réseaux ci-dessus.
- Les métriques du proxy (latence perçue, requêtes par router, codes de
  retour, retries) ne remplacent pas celles de l'application et ne sont pas
  remplacées par elles : l'application sait ce qu'elle a fait, le proxy sait
  ce que le client a vécu.

## Reverse proxy devant une IA — répliques, sessions, streaming

<!-- Source : tuto-traefik.html module 8, mesures relevées sur traefik
     v3.6.25. Ces points ne se manifestent qu'à partir de la deuxième
     réplique ou du premier flux : jamais en développement local à un
     conteneur, donc jamais avant la mise en production. -->

- **Sonde de santé côté proxy dès la deuxième réplique.** Le proxy ne
  vérifie rien par défaut : tant que le conteneur tourne, il reste dans la
  répartition, même s'il ne rend plus aucun service (base injoignable,
  thread bloqué, mémoire saturée). `restart: unless-stopped` ne le relève
  pas, puisqu'il n'est pas tombé. À ne pas confondre avec le `healthcheck:`
  de Compose : celui de Docker décide si le conteneur est sain, celui du
  proxy s'il reste dans le pool — seul le second change le routage.
- **Une session ne se répartit pas.** Un serveur MCP en `streamable-http`
  (`rules/agents-ia.md` § Connecteur MCP), comme toute session portant des
  flux SSE ouverts, vit dans un seul processus : elle ne se sérialise pas et
  ne se déplace pas. Derrière plusieurs répliques sans affinité, l'appel
  d'outil tombe sur une autre réplique que celle qui a ouvert la session, et
  l'erreur (404, JSON-RPC `-32001`) ne dit rien du répartiteur. Le symptôme
  se résume à « ça marche à une réplique, ça casse à deux ».
- Le **cookie collant** ne suffit pas pour un agent : il suppose un client
  qui gère les cookies. Un `httpx.post()` sans session persistante l'ignore
  et reste cassé. Pour un client programmatique, l'affinité qui tient est le
  hachage consistant sur l'adresse du client (`strategy=hrw`), avec sa
  limite symétrique : deux agents derrière un même NAT partagent une
  adresse, donc une réplique.
- **Le streaming ne se configure pas, il se préserve.** Un middleware
  `buffering` accumule la réponse et rend inutilisable le streaming exigé
  par `rules/agents-ia.md` § Streaming — le piège est de l'ajouter pour
  plafonner la taille des requêtes entrantes (`maxRequestBodyBytes`) sans
  voir qu'on met les réponses en tampon du même coup. Deux réflexes venus de
  nginx à ne pas recopier : le `compress` de Traefik transmet au fil de
  l'eau (compatible SSE), et `flushInterval` n'a aucun effet sur une vraie
  réponse `chunked` — un flux saccadé ne vient presque jamais de là.
- S'il ne fallait ajouter que trois choses à un projet réel, dans cet
  ordre : le TLS par ACME dès qu'un domaine public existe, le `ratelimit`
  sur toute route qui déclenche une inférence, la sonde de santé dès la
  deuxième réplique.

## Stockage objet compatible S3 — MinIO

- MinIO sert à la fois DVC (jeux de données versionnés, `rules/ml.md`) et le
  stockage d'artefacts MLflow (`rules/ml.md` § MLflow) : une seule instance
  peut porter les deux usages, mais dans des buckets séparés — un bucket
  `datasets` et un bucket `mlflow`, pas un fourre-tout commun.
- La création de bucket est un geste de code idempotent (vérifier son
  existence avant de le créer), pas une étape manuelle faite une fois à la
  console et jamais reproduite ailleurs.
- Identifiants (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`,
  `MLFLOW_S3_ENDPOINT_URL`) en variable d'environnement, jamais en dur dans le
  script qui prépare le bucket ou dans le `docker-compose.yml` — même règle
  que partout ailleurs (`rules/python.md` § Configuration).

## Orchestration de pipeline — Prefect

- `@flow` marque le point d'entrée (nom explicite), `@task` marque une étape
  unitaire.
- `log_prints=True` sur le `@flow` **ne lève pas l'interdiction de `print()`**
  de `rules/python.md` § Journalisation : notre code journalise par loguru,
  l'option ne sert qu'à récupérer ce qu'écrit sur la sortie standard le code
  qu'on n'a pas écrit (bibliothèque tierce, script appelé), qui se perdrait
  sinon. Elle n'autorise pas à écrire un `print()` de suivi dans une `@task`.
- `retries` et `retry_delay_seconds` sur toute tâche qui dépend d'un réseau ou
  d'un service externe (appel API, scraping) — pas sur un calcul pur, qui
  échouera de la même façon à chaque tentative. `cache_key_fn` évite de
  recalculer une étape dont les entrées n'ont pas changé.
- `flow.serve(...)` est un confort de développement : le déploiement vit dans
  le processus qui l'a lancé, et s'arrête avec lui. En production,
  `prefect deploy` piloté par un `prefect.yaml` (étapes `build`/`push`/`pull`)
  contre un `work_pool` et un worker persistant — pas `.serve()` laissé
  tourner dans un terminal ou un `screen`.
- Un flow qui scrape, entraîne ou réentraîne un modèle reste soumis aux mêmes
  règles que le reste de `rules/ml.md` à l'intérieur de chaque tâche
  (reproductibilité, fuite de données, critères de promotion) : l'orchestration
  planifie et relance, elle ne remplace aucune des vérifications déjà décrites.
- Un contrôle qualité (Evidently `TestSuite`, `rules/ml.md` § Portail qualité)
  est une `@task` comme une autre : son échec bloque le flow — l'orchestrateur
  vérifie quotidiennement la qualité des données entrantes et arrête
  l'entraînement ou l'inférence en aval plutôt que de laisser une anomalie se
  propager. Pas de traitement spécial pour ce type de tâche.

## Traitement asynchrone — Celery

- Un traitement plus long qu'une requête HTTP ne bloque pas la requête :
  `tache.delay(...)` l'ajoute à la file et rend immédiatement un identifiant de
  tâche ; l'appelant interroge ou se fait notifier du résultat plus tard.
  Retenir une connexion ouverte le temps d'une inférence lourde ou d'un
  entraînement est le signe qu'il fallait une file, pas un appel synchrone.
- Le choix du courtier est un arbitrage, pas un défaut : **Redis** est rapide,
  entièrement en mémoire, sans garantie de livraison — une file perdue au
  redémarrage est acceptable si retenter suffit. **RabbitMQ** est plus lourd
  mais confirme chaque livraison — à choisir dès qu'une tâche perdue est un
  problème réel (facturation, action irréversible).
- **Flower** est le seul point de visibilité sur ce que fait Celery : connecté
  au courtier, pas interrogé via l'API applicative. Une file sans moyen de
  voir les tâches en attente, en échec ou bloquées n'est pas opérable en
  production.
- Le nombre de workers se change en une commande
  (`docker compose up --scale worker=3 -d`) seulement si le service worker
  n'a pas de `container_name` fixe dans le Compose — un nom figé entre en
  collision avec lui-même dès qu'on dépasse une instance.

## Kubernetes

- Kubernetes ne construit aucune image : elle est construite et poussée sur un
  registre au préalable (localement ou en CI), Kubernetes ne fait que la
  tirer. Docker Compose n'est pas jeté à ce stade : il reste l'étape de
  validation locale de ce même jeu d'images avant de les décrire en
  manifestes.
- Chaque service déployé est **deux objets**, pas un : un `Deployment` (image,
  ressources, nombre de réplicas — ce qui tourne) et un `Service` (nom et
  adresse stables devant des pods qui meurent et changent d'IP). Ils se
  trouvent par étiquette : `spec.selector.matchLabels` du Deployment et
  `spec.selector` du Service pointent la même valeur que
  `metadata.labels` du pod. Une étiquette qui diverge d'un caractère fait
  échouer le `Service` silencieusement — pas d'erreur, juste aucun trafic
  routé.
- Le HPA (Horizontal Pod Autoscaler) scale par défaut sur CPU/RAM. Scaler sur
  la profondeur d'une file Celery demande une extension (KEDA), pas le HPA
  seul.
- En cas de pod en échec : `kubectl logs <pod>` puis `kubectl describe pod
  <pod>` — les logs ne montrent que ce que le conteneur a eu le temps
  d'écrire ; `describe` montre pourquoi un pod ne démarre pas du tout
  (image introuvable, ressources indisponibles, échec de montage).

## Publication d'image en CI

- Une CD qui construit puis pousse une image cible le **registre interne**,
  pas Docker Hub — cohérent avec `rules/python.md` § Choix par défaut
  (« Déploiement serveur : … images sur le registre interne »).
- L'authentification au registre suit la même règle que tout jeton
  d'automatisation Gitea (`rules/cicd.md` § Jetons et secrets) : pas d'OIDC
  disponible, donc un secret de dépôt avec une rotation prévue — jamais un
  identifiant en dur dans le workflow.

## Monitoring d'infrastructure

Prometheus/Grafana ou un outil de disponibilité (Uptime Kuma) répondent à
« le conteneur tourne-t-il, avec quelle charge ? ». C'est un niveau différent
de la surveillance décrite dans `rules/ml.md` § Surveillance en production,
qui répond à « le modèle est-il encore juste ? ». Les deux sont nécessaires,
et l'un ne dispense pas de l'autre : un service peut répondre en 50 ms avec un
modèle dont les prédictions ont dérivé, et un modèle stable derrière un
conteneur qui redémarre en boucle.
