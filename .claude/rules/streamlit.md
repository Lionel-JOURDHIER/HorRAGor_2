---
paths:
  - "app.py"
  - "**/app.py"
  - "Home.py"
  - "**/Home.py"
  - "pages/**/*.py"
  - "**/pages/**/*.py"
  - ".streamlit/**"
---

# Application Streamlit

<!-- Source : projet de découverte Streamlit (catalogue de widgets, page
     fonction affine, page data analyst) et le CLAUDE.md racine du dossier de
     formation § Applications. Le fichier couvre ce que le catalogue de
     widgets ne dit pas : gestion d'état, cache, secrets, déploiement — pas
     un rappel de l'API (`st.button()` fait un bouton n'est pas une
     convention à écrire ici). -->

Une page Streamlit se réexécute entièrement à chaque interaction. Ce qui suit
sert surtout à contenir les conséquences de ce modèle d'exécution : un état
qui ne doit pas se perdre au prochain rerun, un widget qui ne doit pas
recréer sa clé au prochain passage, une connexion qui ne doit pas se rouvrir
à chaque clic.

## Structure

- Multipage via un dossier `pages/`, un fichier par page, **préfixe
  numérique** pour fixer l'ordre du menu (`0_fonction_affine.py`,
  `1_data_analyst.py`) — c'est le mécanisme natif de Streamlit, pas une
  convention à réinventer avec des routes ou un fichier de config à part.
- La logique métier (calcul, filtrage, chargement de données) reste dans des
  fonctions testables, importées par la page — pas écrite en ligne dans le
  script de la page. `rules/tests-python.md` § Ce qu'on teste, et ce qu'on ne
  teste pas s'applique tel quel : la fonction se teste, le widget ne se teste
  pas.

## État et connexions

- **`@st.cache_resource`** sur toute connexion externe (base de données,
  API, client Supabase) : sans lui, une connexion se rouvre à chaque rerun,
  donc à chaque clic sur un widget.
- **`st.session_state`** pour ce qui doit survivre au rerun suivant (un
  DataFrame chargé une fois, une sélection utilisateur cumulée) — une
  variable locale au script est réinitialisée à chaque exécution, elle ne
  persiste jamais entre deux interactions.
- **`st.rerun()`** après une mutation qui doit se refléter immédiatement
  (état modifié en dehors du flux normal des widgets) — sans lui, l'affichage
  reste en retard d'une interaction.
- **`key=` unique** pour chaque widget créé en boucle (une case à cocher par
  ligne d'un tableau, par exemple) : sans clé explicite et distincte,
  Streamlit lève une erreur de clé dupliquée ou, pire, mélange l'état de deux
  widgets qui se ressemblent.

## Fichiers envoyés par l'utilisateur

- `st.file_uploader()` : vérifier le type et la taille avant de traiter le
  fichier, pas seulement l'extension déclarée par le navigateur — un fichier
  renommé passe l'extension mais pas un `pd.read_csv()` qui échoue en plein
  traitement si le contenu ne correspond pas.
- `st.download_button()` génère le fichier à chaque rerun où il est présent à
  l'écran, pas seulement au clic : un calcul coûteux derrière un bouton de
  téléchargement doit être mis en cache (`@st.cache_data`), pas relancé à
  chaque interaction ailleurs sur la page.

## Journalisation

Même règle que partout ailleurs (`rules/python.md` § Journalisation) :
loguru, pas de `print()` ni de `st.write()` de debug qui traîne dans une
version livrée — un `st.write(df)` de contrôle oublié reste affiché à
l'utilisateur final, contrairement à un `print()` oublié qui reste au moins
invisible côté navigateur.

## Secrets

`.streamlit/secrets.toml` pour les identifiants (base de données, clé d'API),
jamais commité — même règle que `.env`/`.env.example` dans `rules/python.md`
§ Configuration, appliquée au fichier que Streamlit lit nativement via
`st.secrets`.

## Déploiement

Pas de service cloud tiers par défaut (Streamlit Cloud ou équivalent) :
cohérent avec `rules/python.md` § Choix par défaut (« Déploiement serveur :
`docker-compose.yml`, images sur le registre interne »), une application
Streamlit se conteneurise et se déploie comme le reste — `rules/deploiement.md`
s'applique telle quelle. Un déploiement sur un service tiers reste possible,
mais c'est une dérogation à écrire dans le `CLAUDE.md` du dépôt, pas un choix
par défaut.
