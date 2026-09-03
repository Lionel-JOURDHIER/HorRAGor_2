---
paths:
  - "tests/**/*.py"
  - "**/test_*.py"
  - "**/conftest.py"
---

# Tests — pytest

<!-- Nommé tests-python.md et non test_python.md : le tiret suit la casse des
     autres règles (securite-api, workflow-session), et le préfixe test_ est
     réservé aux modules que pytest collecte.

     Les tests propres à un domaine sont ailleurs : rules/ml.md pour ce qui se
     teste sur un modèle, rules/bdd.md pour la base, rules/http.md pour les
     appels sortants. Ce fichier porte ce qui vaut pour tous. -->

Un test existe pour qu'une régression se voie. Il n'est utile que s'il échoue
pour la bonne raison et que son message dit laquelle.

## Organisation

- `tests/` à la racine, modules `test_*.py`, fonctions `test_*`. Pas de classe
  sauf pour partager une fixture coûteuse entre plusieurs cas.
- Le nom dit le cas et l'attendu :
  `test_charger_parc_colonne_manquante_leve_valueerror`. Un `test_parc_2` oblige
  à lire le corps pour savoir ce qui est cassé.
- `conftest.py` au niveau qui correspond à la portée réelle d'une fixture. Une
  fixture à la racine est chargée pour tout le monde ; c'est rarement voulu.
- Configuration dans `[tool.pytest.ini_options]` du `pyproject.toml`, pas dans
  un `pytest.ini` séparé — même raison que pour ruff, un seul fichier de
  configuration par projet :

  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  addopts = "-q --strict-markers"
  markers = ["slow: exclu du lancement par défaut"]
  ```

  `--strict-markers` fait échouer un marqueur non déclaré, ce qui évite qu'un
  `@pytest.mark.slwo` mal orthographié passe pour un test ordinaire.
- La couverture **ne fait pas partie** des options par défaut : elle ralentit
  chaque lancement et brouille les traces. Elle se demande quand on la veut,
  `uv run pytest --cov=src --cov-report=term-missing`, et en intégration
  continue.
- Un test vérifie **un** comportement. Trois assertions sur la même sortie sont
  un test, trois scénarios en sont trois.
- **Jamais de `sys.path.insert` ni de bricolage de chemin** dans un test ou dans
  un `__init__.py` pour retrouver le code. Le symptôme dit que le projet n'est
  pas installé : disposition `src/`, `uv sync`, et l'import fonctionne
  identiquement en local et en CI. Un chemin calculé à partir de `__file__`
  dépend du répertoire depuis lequel on lance pytest.

## Fixtures

- `@pytest.fixture` avec `yield` dès qu'il y a quelque chose à refermer :
  connexion, fichier, répertoire temporaire, serveur simulé. Le code après le
  `yield` s'exécute même quand le test échoue.
- Fichiers et répertoires : `tmp_path`, jamais un chemin en dur ni un dossier du
  dépôt. Un test qui écrit à côté du code finit par être lancé deux fois en
  parallèle.
- Pas d'état partagé mutable entre tests. Chaque test doit passer seul, et la
  suite doit passer dans n'importe quel ordre — un test qui ne passe qu'après un
  autre ne teste plus ce qu'on croit.

## Plusieurs cas

`@pytest.mark.parametrize` plutôt qu'une boucle dans le test : la boucle
s'arrête au premier échec et masque les suivants, alors que chaque jeu de
paramètres est un test à part, nommé, qui échoue seul.

```python
@pytest.mark.parametrize(
    "saisie, attendu",
    [("1234", 1234), ("0012", 12)],
)
def test_code_marche_normalise(saisie, attendu):
    assert normaliser_marche(saisie) == attendu
```

## Assertions

- `pytest.raises(ValueError, match="Colonne")` — sans `match`, le test passe
  pour n'importe quelle `ValueError`, y compris celle d'un bug arrivé plus tôt.
- Flottants : `pytest.approx`. Une égalité stricte sur un flottant échoue un
  jour, sur une machine, sans que rien n'ait changé.
- Comparer la structure entière (`assert resultat == attendu`) plutôt qu'une
  dizaine de champs un par un : le message d'échec montre alors le diff complet.

## Ce qu'on teste, et ce qu'on ne teste pas

- La logique métier d'abord. Pas les widgets, pas la mise en page, pas ce que
  fait déjà la bibliothèque tierce ou le framework.
- Un scénario de bout en bout sur le chemin critique, en plus des tests
  unitaires — pour une API, le flux d'authentification complet.
- Une route FastAPI se teste par `TestClient`, qui appelle l'application en
  mémoire sans ouvrir de port : assertions sur `response.status_code` **et** sur
  `response.json()`. Vérifier le seul code de retour laisse passer une réponse
  200 au corps vide.
- Correction d'un défaut : **écrire d'abord le test qui échoue**, puis corriger.
  Sans lui, rien ne garantit que le défaut ne revienne pas, ni même qu'on ait
  compris lequel c'était.
- Le taux de couverture n'est pas un objectif. Un chemin critique non couvert
  compte plus que dix points de pourcentage.

## Isolation

- Aucun appel réseau réel, aucune base réelle, aucune horloge réelle. Le temps
  se passe en paramètre ou par une fixture, jamais par un `sleep` qui rend la
  suite lente et aléatoire.
- `monkeypatch` et les doubles se posent **là où l'objet est utilisé**, pas là
  où il est défini : `monkeypatch.setattr("mon_module.httpx.get", ...)`. C'est
  l'erreur la plus fréquente, et elle se manifeste par un test qui passe alors
  que rien n'est simulé.
- Simuler la frontière du système (le client HTTP, l'accès disque), pas les
  fonctions internes du code testé — sinon le test décrit l'implémentation et
  casse à la première réécriture.
- Ce qui est lent ou dépend d'une ressource externe est marqué
  (`@pytest.mark.slow`) et exclu du lancement par défaut.

## Les tests sont du code, sauf pour DRY

La règle de la troisième occurrence du socle ne s'applique pas ici : un test
doit se lire sans suivre d'indirection. Mieux vaut trois fois la même
préparation de trois lignes qu'une fabrique paramétrée qui oblige à ouvrir un
autre fichier pour savoir ce qui est testé.

Un test qui échoue ne se modifie jamais pour le faire passer avant d'avoir
compris pourquoi il échoue.
