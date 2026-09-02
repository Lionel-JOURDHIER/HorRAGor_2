Schéma relationnel de la base de données
=========================================

La base de données relationnelle de HorRAGor est organisée autour de la table
``films``. Les informations complémentaires sont réparties dans les tables
des réalisateurs, collections, genres et scores provenant de différentes
sources externes.

Table ``films``
---------------

Table centrale contenant les informations principales sur les films.

**Clé primaire :**

- ``tmdb_id`` : identifiant TMDB.

**Clés étrangères :**

- ``director_id`` → ``realisateurs.director_id``
- ``id_collection`` → ``collections.tmdb_collection_id``

**Identifiants alternatifs :**

- ``imdb_id`` : identifiant IMDb, unique.
- ``id_tertiaire`` : identifiant tertiaire, unique.

**Métadonnées principales :**

- ``title``
- ``original_title``
- ``original_language``
- ``release_date``
- ``status``
- ``runtime``
- ``overview``
- ``tagline``
- ``poster_path``
- ``budget``
- ``revenue``


Table ``realisateurs``
----------------------

Table contenant les réalisateurs.

**Clé primaire :**

- ``director_id`` : identifiant natif TMDB, sans auto-incrémentation.

**Attributs :**

- ``name`` : nom du réalisateur.

**Relation :**

- Un réalisateur peut être associé à plusieurs films.
- ``realisateurs`` 1 → N ``films``.


Table ``collections``
---------------------

Table contenant les collections de films.

**Clé primaire :**

- ``tmdb_collection_id`` : identifiant natif TMDB, sans auto-incrémentation.

**Attributs :**

- ``collection_name``

**Relation :**

- Une collection peut contenir plusieurs films.
- ``collections`` 1 → N ``films``.


Table ``genres``
----------------

Table de référence contenant les genres cinématographiques.

**Clé primaire :**

- ``id_genre`` : entier auto-incrémenté.

**Attributs :**

- ``genre_name`` : nom du genre, unique.

**Relation :**

- Un genre peut être associé à plusieurs films.
- Relation N-N avec ``films`` via ``film_genres``.


Table ``film_genres``
---------------------

Table d'association entre les films et les genres.

**Clé primaire :**

- ``id_film_genre`` : entier auto-incrémenté.

**Clés étrangères :**

- ``tmdb_id`` → ``films.tmdb_id``
- ``id_genre`` → ``genres.id_genre``

Les clés étrangères utilisent ``ON DELETE CASCADE``.

**Relation :**

- ``films`` N ↔ N ``genres``.


Table ``score_tmdb``
--------------------

Table contenant les statistiques provenant de TMDB.

**Clé primaire :**

- ``id_score_tmdb`` : entier auto-incrémenté.

**Clé étrangère :**

- ``tmdb_id`` → ``films.tmdb_id``

La colonne ``tmdb_id`` est unique, ce qui garantit une relation 1-1 avec
un film.

**Attributs :**

- ``vote_average``
- ``vote_count``
- ``popularity``


Table ``score_imdb``
--------------------

Table contenant les évaluations provenant d'IMDb.

**Clé primaire :**

- ``id_score_imdb`` : entier auto-incrémenté.

**Clé étrangère :**

- ``tconst`` → ``films.imdb_id``

La colonne ``tconst`` est unique, garantissant une relation 1-1.

**Attributs :**

- ``title``
- ``average_rating``
- ``num_votes``


Table ``score_rt``
------------------

Table contenant les évaluations provenant de Rotten Tomatoes.

**Clé primaire :**

- ``id_score_rt`` : entier auto-incrémenté.

**Clé étrangère :**

- ``id_tertiaire`` → ``films.id_tertiaire``

La colonne ``id_tertiaire`` est unique, garantissant une relation 1-1.

**Attributs :**

- ``url_rotten`` : URL unique de la page Rotten Tomatoes.
- ``rt_tomatometer``
- ``rt_audience_score``
- ``rt_critics_consensus``


Relations entre les tables
--------------------------

Les relations principales du schéma sont les suivantes :

.. list-table::
   :header-rows: 1

   * - Relation
     - Cardinalité
     - Clé étrangère
   * - Réalisateur → Films
     - 1-N
     - ``films.director_id``
   * - Collection → Films
     - 1-N
     - ``films.id_collection``
   * - Films ↔ Genres
     - N-N
     - ``film_genres.tmdb_id`` / ``film_genres.id_genre``
   * - Film → Score TMDB
     - 1-1
     - ``score_tmdb.tmdb_id``
   * - Film → Score IMDb
     - 1-1
     - ``score_imdb.tconst``
   * - Film → Score Rotten Tomatoes
     - 1-1
     - ``score_rt.id_tertiaire``


Schéma conceptuel simplifié
----------------------------

.. code-block:: text

   REALISATEURS
        │
        │ 1-N
        ▼
      FILMS ◄──────── 1-N ──────── COLLECTIONS
        │
        │
        ├──────── 1-1 ──────── SCORE_TMDB
        │
        ├──────── 1-1 ──────── SCORE_IMDB
        │
        ├──────── 1-1 ──────── SCORE_RT
        │
        │
        │ N-N
        ▼
   FILM_GENRES
        │
        │ N-1
        ▼
      GENRES


## Intégrité référentielle

La structure utilise les contraintes de clés étrangères SQLAlchemy afin
d'assurer l'intégrité référentielle.

Pour la relation entre les films et les réalisateurs ainsi que pour la
relation entre les films et les collections, la suppression d'une référence
utilise `ON DELETE SET NULL` afin de conserver le film.

Pour la table d'association `film_genres`, la suppression d'un film ou
d'un genre entraîne la suppression des enregistrements associés grâce à
`ON DELETE CASCADE`.

Les tables de scores utilisent des clés étrangères uniques afin de garantir
une relation de type 1-1 avec la table `films`.


