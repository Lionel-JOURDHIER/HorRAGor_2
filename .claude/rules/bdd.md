---
paths:
  - "**/db/**/*.py"
  - "**/models.py"
  - "**/database.py"
  - "**/repositories/**/*.py"
  - "**/migrations/**"
  - "alembic/**"
---

# Base de données — SQLAlchemy

<!-- Portée à ajuster à l'arborescence réelle du dépôt. Si l'ORM vit dans un
     répertoire `models/`, ajouter "**/models/**/*.py" dans la copie locale —
     mais jamais dans un projet qui a un src/ml/models/, où le mot désigne des
     architectures de réseau et où cette règle n'aurait aucun sens.

     Cette règle complète le tableau « Choix par défaut » de rules/python.md,
     elle ne le remplace pas : SQLAlchemy, Alembic, SQLite en local et en
     test, PostgreSQL en serveur. -->

## Deux styles, ne pas les mélanger

La bibliothèque installée est la 2.0. Elle accepte encore la syntaxe héritée de
la 1.x, ce qui fait cohabiter deux écritures de la même chose.

| Hérité (1.x) | Style 2.0 |
|---|---|
| `Base = declarative_base()` | `class Base(DeclarativeBase): ...` |
| `nom = Column(String, nullable=False)` | `nom: Mapped[str] = mapped_column()` |
| `session.query(Modele).filter_by(...)` | `select(Modele).where(...)` + `session.execute(...)` |

- **Projet neuf : style 2.0.** `session.query()` est marqué hérité par
  SQLAlchemy et finira par disparaître ; `Mapped[str]` implique `NOT NULL` et
  `Mapped[str | None]` implique `NULL`, donc la nullabilité se lit dans
  l'annotation au lieu d'être répétée en argument.
- **Projet existant écrit en 1.x : il reste en 1.x.** Une modification suit le
  style du fichier qu'elle touche, conformément à la priorité 3 du socle. Une
  migration de style est une tâche à part, décidée et faite d'un bloc, pas au
  détour d'un correctif.
- **Jamais les deux dans le même dépôt.** Un modèle en `Column` et un autre en
  `Mapped` produisent des erreurs de typage incompréhensibles, et personne ne
  sait plus quelle forme écrire. Le style retenu est écrit dans le `CLAUDE.md`
  du dépôt.

## Session

**Une session par unité de travail.** Jamais de session globale de module,
jamais une session partagée entre deux requêtes HTTP : les objets restent
attachés, l'état fuit d'une opération à l'autre et les erreurs sont
irreproductibles.

Ouverture par gestionnaire de contexte, qui ferme et libère la connexion même
en cas d'exception :

```python
with Session() as session:          # synchrone
    with session.begin():
        session.add(logement)
```

`session.begin()` valide en sortie de bloc et annule sur exception. Écrire un
`rollback()` à la main n'est utile que hors de ce schéma.

- Anti-schéma courant, présent tel quel dans les supports de formation : un
  `try` qui englobe le `with`, et un `except` qui appelle `session.rollback()`
  — la variable n'existe plus ou la session est déjà fermée. Le rattrapage se
  met **à l'intérieur** du bloc, ou nulle part.
- Une session ne se « ferme » pas par `session.dispose()` : cette méthode
  n'existe pas sur une session. C'est le **moteur** qui se dispose, une fois,
  à l'arrêt du programme.

### Synchrone ou asynchrone

Le critère est le contexte d'exécution, pas la préférence :

| Contexte | Attendu |
|---|---|
| Script, notebook, outil en ligne de commande, tâche planifiée | **synchrone** — `create_engine`, `sessionmaker` |
| Route FastAPI, service qui tient des connexions concurrentes | **asynchrone** — `create_async_engine`, `async_sessionmaker` |

Un seul des deux par projet : mélanger fait apparaître des appels bloquants au
milieu d'une boucle d'événements, ce qui sérialise silencieusement tout le
service.

- Sur FastAPI, la session est une dépendance (`Depends(get_session)`), une par
  requête. Elle n'est pas créée dans la fonction de route.
- En asynchrone, tout accès à un attribut peut déclencher une requête : le
  chargement paresseux hors session lève `MissingGreenlet`. Charger
  explicitement ce qui sera lu (`selectinload`) plutôt que de compter dessus.
- Un appel synchrone dans une route asynchrone est le défaut le plus fréquent
  de cette pile, et il ne se voit pas : le service fonctionne, il ne tient
  simplement plus la charge.

## Conception : Merise avant le code

Une table ne s'improvise pas dans l'éditeur. Trois étapes, dans l'ordre, avant
d'écrire une classe :

1. **MCD** — entités, associations, cardinalités des deux côtés (`0,1`, `1,1`,
   `0,n`, `1,n`). C'est là qu'on décide ce qui est obligatoire.
2. **MLD** — clés primaires et étrangères déduites des cardinalités.
3. **MPD** — types SQL concrets, longueurs, contraintes.

- Une information répétée à l'identique sur plusieurs lignes est une table à
  part, référencée par une clé étrangère : moins d'espace, et surtout une seule
  orthographe possible. Une faute de frappe dans un libellé recopié crée une
  catégorie fantôme.
- Une relation *n-m* se résout **toujours** par une table d'association, qui
  porte au passage ses propres attributs (quantité, date, rôle).
- Dénormaliser est une optimisation, pas un point de départ : on ne le fait
  qu'avec une mesure qui le justifie, et on l'écrit.

## Modèles

- `__tablename__` en `snake_case` pluriel.
- Clé primaire `id` entière autoincrémentée par défaut. UUID seulement si les
  identifiants doivent être générés hors base ou ne rien révéler.
- Relations bidirectionnelles avec `back_populates=` des deux côtés — jamais
  `backref`, qui crée un attribut invisible à la lecture du modèle enfant.
- `cascade="all, delete-orphan"` côté parent quand l'enfant n'a pas d'existence
  autonome. Y réfléchir explicitement : c'est une suppression en chaîne.
- Contraintes en base, pas seulement dans le code Python : `unique=True`,
  `nullable`, clés étrangères, `CheckConstraint`. Une règle qui ne vit que dans
  l'application est contournée par le premier script d'import.
- Index sur toute colonne servant à filtrer ou à joindre régulièrement. Les clés
  étrangères ne sont **pas** indexées automatiquement par PostgreSQL.
- Horodatages `timestamptz` avec valeur par défaut serveur
  (`server_default=func.now()`), pas une valeur calculée en Python : c'est
  l'heure de la base qui fait foi.

## Recherche vectorielle — pgvector

Extension PostgreSQL pour la recherche par similarité sémantique (RAG,
recommandation) : le type `vector` reste dans PostgreSQL, interrogeable par les
mêmes `WHERE`/`JOIN`/`GROUP BY` que le reste du schéma. Ne s'active qu'à la
demande — ce n'est pas une entrée du tableau « Choix par défaut » de
`rules/python.md`.

- Extension activée une fois par base, **dans une migration Alembic**
  (`op.execute("CREATE EXTENSION IF NOT EXISTS vector")`) — pas à la main sur
  le serveur, sinon l'environnement suivant (test, autre poste, CI) ne l'a pas.
- Colonne déclarée avec `pgvector.sqlalchemy.Vector(N)` et `mapped_column`,
  cohérent avec le style 2.0 de ce fichier. Un accès `psycopg2` brut avec
  `register_vector(conn)` reste possible pour un script d'exploration ponctuel,
  pas pour le code applicatif.
- `N` est la dimension du modèle d'embedding (384/768/1536 selon le modèle) et
  ne varie pas dans la colonne : changer de modèle d'embedding recalcule toutes
  les lignes, ce qui se traite comme une migration de données, pas un
  ajustement de type.

### Opérateur de distance

Le choix dépend de la nature des vecteurs, pas d'une préférence :

| Opérateur | Distance | Cas d'usage |
|---|---|---|
| `<=>` | Cosinus | Embeddings texte / NLP — presque toujours le bon choix par défaut |
| `<->` | L2 (euclidienne) | Images, vision |
| `<#>` | Produit scalaire (négatif) | Retrieval dense, bi-encodeurs |
| `<+>` | L1 (Manhattan) | Features éparses, recommandation |

L'opérateur utilisé en requête doit correspondre à l'`ops` de l'index
(`vector_cosine_ops` pour `<=>`, `vector_l2_ops` pour `<->`, etc.) : un index
construit avec le mauvais `ops` n'est simplement pas utilisé, sans erreur.

### Index ANN

Sans index, une recherche compare tous les vecteurs un par un (balayage
séquentiel). Au-delà d'environ 10 000 lignes, un index ANN (Approximate
Nearest Neighbors) est obligatoire.

| | HNSW | IVFFlat |
|---|---|---|
| Par défaut | oui, sauf contrainte mémoire | non |
| Mémoire | plus gourmand | plus léger |
| Paramètres | `m`, `ef_construction`, `ef_search` | `lists`, `probes` |

```sql
CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

Vérifier que l'index est réellement utilisé avec `EXPLAIN (ANALYZE, BUFFERS)`,
pas en le supposant : un `ops` erroné ou un filtre `WHERE` additionnel peut
faire retomber sur un balayage complet. Ce type n'est testable que sur une
vraie base PostgreSQL — voir § Tests.

## Requêtes

- Toujours passer par les paramètres liés. `text("… WHERE nom = :nom")` avec
  paramètres est acceptable ; une f-string dans une requête SQL ne l'est jamais,
  y compris pour un script interne.
- Les jointures explicites, les tables aliasées dès qu'il y en a plus d'une.
- `N+1` : une boucle Python qui accède à une relation fait une requête par
  itération. Charger en une fois (`selectinload`, `joinedload`) et vérifier en
  activant `echo=True` en développement quand le doute existe.
- L'agrégation et le filtrage se font en base, pas en Python après un `SELECT *`.
- `WHERE` filtre les lignes **avant** l'agrégation, `HAVING` filtre le résultat
  **après**. Mettre une condition sur une colonne brute dans un `HAVING`
  fonctionne parfois et coûte un balayage complet de la table.
- Une sous-requête est entre parenthèses, et rend soit une valeur unique
  (comparaison), soit une colonne (`IN (...)`). Une sous-requête corrélée
  s'exécute une fois par ligne : vérifier avec `EXPLAIN` avant de s'en
  satisfaire.
- Ne sélectionner que les colonnes utilisées. `SELECT *` transporte des données
  inutiles et casse silencieusement le jour où une colonne est ajoutée.

## Migrations

- Tout changement de modèle passe par une migration Alembic, y compris en
  développement. Pas de `Base.metadata.create_all()` ailleurs que dans les tests.
- La migration générée par `--autogenerate` est **relue et corrigée** avant
  commit : elle rate les renommages (qu'elle traduit en `DROP` + `ADD`, donc en
  perte de données), les changements de type et les contraintes nommées.
- Chaque migration a un `downgrade` qui fonctionne, ou un commentaire disant
  pourquoi le retour arrière est impossible.
- Migration de structure et migration de données dans des révisions distinctes :
  elles n'échouent pas pour les mêmes raisons et ne se rejouent pas pareil.
- SQLite ne sait pas modifier une colonne en place. Une migration validée sur
  SQLite peut échouer sur PostgreSQL, et l'inverse : la cible de production est
  celle qui compte.

## Tests

- SQLite en mémoire, base recréée par test, transaction annulée en fin de test.
- Ce qui touche à un type spécifique à PostgreSQL (`JSONB`, `ARRAY`, `tsvector`,
  `vector` — § Recherche vectorielle) ne peut pas être testé sur SQLite : ces
  tests-là visent une vraie base PostgreSQL, sinon ils ne prouvent rien.

## Connexion

- URL en variable d'environnement, jamais en dur — cohérent avec la section
  Configuration de `rules/python.md`. Un mot de passe de base n'apparaît ni dans
  le code, ni dans un log, ni dans une trace d'erreur renvoyée à un client.
- Un seul moteur par processus, créé au démarrage : c'est lui qui porte le pool
  de connexions. Un moteur créé par appel épuise les connexions du serveur.
- Le moteur se libère à l'arrêt du programme : `engine.dispose()`, ou
  `await engine.dispose()` en asynchrone (événement d'arrêt FastAPI).
- `echo=True` est un outil de mise au point : il journalise chaque requête, y
  compris les valeurs liées. Il ne reste pas dans le code livré.
