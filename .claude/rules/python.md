---
paths:
  - "**/*.py"
---

# Python

## Outillage

- **uv** exclusivement : `uv sync`, `uv run <script>`, `uv add <paquet>`. Jamais
  `pip install`, jamais poetry, jamais d'activation manuelle du venv — `uv run`
  s'en charge et fonctionne à l'identique sous Windows et Linux.
- `uv.lock` est la source de vérité des versions et est committé. Ne pas
  maintenir en plus un `requirements.txt` : deux verrous divergent toujours.
- Derrière le proxy de l'entreprise : `uv sync --native-tls`.
- **ruff** pour le lint et le format. Avant de committer :
  `uv run ruff check --fix . && uv run ruff format .`
- Ce que ruff vérifie n'a pas à être répété ici : longueur de ligne, ordre des
  imports, guillemets, présence des docstrings.

### Configuration de ruff

Toute la configuration de l'outillage vit dans `pyproject.toml`. Pas de
`.ruff.toml`, pas de `setup.cfg`, pas de `pytest.ini` : un seul fichier, sinon
personne ne sait lequel gagne.

```toml
[tool.ruff]
line-length = 88
target-version = "py311"        # la version réellement visée par le projet

[tool.ruff.lint]
select = ["E", "W", "F", "I", "D"]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

| Code | Ce qu'il apporte |
|---|---|
| `E`, `W` | style PEP 8 — espaces, indentation, lignes |
| `F` | erreurs logiques : variable non définie, import inutilisé |
| `I` | tri et regroupement des imports |
| `D` | présence et forme des docstrings |

- `convention = "google"` est **obligatoire** avec `D` : sans elle, ruff
  applique les règles PEP 257 par défaut et signale nos sections `Args:` /
  `Returns:` comme des erreurs de format.
- Ce qu'on **ne** met **pas** dans `ignore` : `D101`, `D102`, `D103`,
  `D104` — ce sont exactement les docstrings que le standard exige. Les
  désactiver « parce que la fonction est courte » revient à supprimer la règle.
  `D100` (docstring de module) est le seul écart courant admis.
- Un `ignore` se justifie dans le fichier, en commentaire, avec sa raison. Une
  liste d'exclusions héritée d'un autre projet et recopiée sans la lire ne veut
  plus rien dire.
- Une exception ponctuelle se marque à la ligne concernée
  (`# noqa: E501`, avec le code), jamais par une exclusion globale.

## Structure d'un projet

- Le code vit sous `src/<nom_du_package>/`, jamais à la racine. **Le nom du
  package suit le nom du dépôt.** La racine ne porte que ce qui décrit le
  projet : `pyproject.toml`, `README.md`, `CLAUDE.md`, la CI, le Dockerfile.
- `__init__.py` déclare l'API publique du package avec `__all__`. Ce qui n'y
  figure pas est un détail d'implémentation : on peut le renommer sans prévenir.
  C'est ce qui rend l'interdiction de `import *` tenable au lieu d'arbitraire.
- Les tests vivent dans `tests/` à la racine, hors du package livré.
- Un module exécutable protège son point d'entrée par
  `if __name__ == "__main__":`, et cette clause ne contient qu'un appel. La
  logique est dans une fonction importable, donc testable — sans quoi elle
  s'exécute au moindre import et ne peut être appelée par rien d'autre.

## Classes

- `@property` / `@x.setter` avec validation qui lève `ValueError` dès qu'un
  attribut doit respecter une règle (bornes, format, cohérence avec un autre
  champ). Un attribut public non contrôlé délègue la vérification à chaque
  appelant, donc à aucun.
- Pas de `get_x()` / `set_x()` sans logique : en Python c'est un attribut, et on
  ajoute la `property` le jour où une règle apparaît, sans changer les appelants.
- Un objet qui ne fait que porter des champs est une `dataclass`, pas une classe
  écrite à la main.

## Docstrings

Style Google, en français. Contrôlé par la règle `D` de ruff quand le projet
l'active.

```python
def charger_parc(chemin: Path, marche: str) -> dict[str, Logement]:
    """Construit le parc à partir d'un export bailleur.

    Args:
        chemin: Fichier xlsx exporté depuis l'outil bailleur.
        marche: Code marché à quatre chiffres, non padé.

    Returns:
        Logements indexés par code, y compris les duplicables.

    Raises:
        FileNotFoundError: Si l'export est absent.
        ValueError: Si une colonne attendue manque.
    """
```

- Ce qui est déjà dit par le nom, les annotations de type et la signature n'est
  pas répété. Une fonction évidente prend un résumé d'une ligne, pas un
  `Args:`/`Returns:` complet.
- `Raises:` est obligatoire dès qu'une exception est levée volontairement :
  c'est le seul endroit où l'appelant peut l'apprendre.
- Fonctions privées (`_nom`) : docstring seulement si la logique n'est pas
  triviale.
- Une classe documente ses attributs publics dans sa propre docstring, section
  `Attributes:`, et pas dans celle de `__init__` : c'est la classe qu'on
  consulte, pas son constructeur.
- Pas d'exemple d'utilisation dans une docstring. Rien ne l'exécute, donc il
  ment tôt ou tard sans que personne ne s'en aperçoive. Un exemple qui doit
  rester juste est un test — voir `rules/tests-python.md`.

## Typage

- Annotations sur toute signature publique. Le type de retour aussi, y compris
  `-> None`.
- Syntaxe moderne : `list[str]`, `dict[str, int]`, `str | None`. Pas de
  `typing.List` ni de `Optional`.
- `Path` plutôt que des chemins en chaîne, `pathlib` plutôt que `os.path`.

## Erreurs

- Lever une exception standard au message utilisable plutôt qu'un type maison :
  `FileNotFoundError`, `ValueError`, `KeyError`. Une exception dédiée seulement
  si l'appelant doit la distinguer pour agir différemment.
- Le message dit quoi et où : `f"Colonne '{nom}' absente de {chemin.name}"`.
- Jamais de `except:` ni de `except Exception:` sans re-levée. Rattraper le type
  précis attendu.
- Les exceptions remontent jusqu'au point d'entrée (CLI, fenêtre, route) qui
  décide de l'affichage. Pas de rattrapage intermédiaire qui transforme une
  erreur en valeur par défaut silencieuse.

## Journalisation

- **Le logger est loguru.** Ni `logging`, ni `print()`, ni un logger maison. Le
  `CLAUDE.md` d'un dépôt ne peut y déroger que pour un programme qui n'a pas de
  journal du tout (CLI courte, GUI), et en le disant. Ne jamais introduire un
  second mécanisme, ni remplacer celui en place au détour d'un correctif.
- La configuration des sinks est centralisée dans un module unique, qui commence
  par `logger.remove()` — sinon le handler par défaut de loguru continue
  d'écrire sur `stderr` en plus des sinks déclarés. Un point d'entrée fait
  `from logger import logger`, un module seulement importé fait
  `from loguru import logger` — loguru est global, les sinks sont hérités.
  `logger.add()` et `logger.remove()` nulle part ailleurs : une double
  configuration duplique chaque ligne de log.
- Ce module lit le contexte de déploiement dans une variable d'environnement :
  développement (niveau bas, rétention courte) et production (`INFO`, rétention
  longue) sont deux jeux de `logger.add()`, pas un bloc commenté qu'on
  décommente à la main.
- Arguments passés en style loguru, pas en f-string :
  `logger.error("lecture {} : {}", chemin, err)`. La chaîne n'est formatée que
  si le niveau est actif.
- Niveaux : `trace` pour le pas-à-pas qu'on n'active qu'en mise au point,
  `debug` pour le détail technique, `info` pour le suivi normal d'une étape,
  `warning` pour un cas dégradé mais géré, `error` pour un échec, `critical`
  pour ce qui arrête le service. Un sink retient son niveau **et tous ceux
  au-dessus** : `level="WARNING"` capte aussi les `error` et les `critical`.
- Dans un `except`, `logger.exception("…")` et pas `logger.error(str(err))` :
  seul le premier joint la trace. Sans elle, il reste le message d'une erreur
  dont on ne sait plus d'où elle vient.
- **Ne jamais journaliser un mot de passe, un jeton, une clé, ni une donnée
  personnelle** — un journal est lu, copié et conservé plus longtemps que le
  reste. Vaut partout, pas seulement sur une API (voir
  `rules/securite-api.md`).
- Un sink fichier a une rotation et une rétention
  (`rotation="10 MB"`, `retention="7 days"`, `compression="zip"`), sinon le
  fichier grossit jusqu'à remplir le disque de la machine qui héberge le
  service. `enqueue=True` dès que plusieurs processus ou threads écrivent.
- Rien dans une boucle serrée ni sur un chemin appelé à chaque itération : un
  journal saturé ne se lit plus, et le coût d'écriture devient celui du
  traitement. Ce qui est répétitif se journalise agrégé, une fois à la fin.

## Configuration

- Aucune URL, aucun chemin réseau, aucun identifiant en dur dans le code.
  Variables d'environnement lues au même endroit (`config.py`), valeurs par
  défaut pour le développement local.
- Le basculement entre contextes de déploiement se fait par une variable, pas
  par du code conditionnel dispersé.
- Envoi d'email (`redmail` par exemple, `from redmail import gmail`) : un
  **mot de passe d'application dédié** (généré depuis le compte Google,
  jamais le mot de passe réel du compte — une fuite se révoque alors sans
  toucher au compte), et `gmail.username`/`gmail.password` chargés depuis
  l'environnement comme n'importe quel identifiant, jamais écrits en dur
  dans le script.

## Mots de passe et saisie sensible

Vaut partout, y compris dans un script ou un outil en ligne de commande —
`rules/securite-api.md` ne se charge que sur le code d'API, mais la règle ne
s'y limite pas.

- Un mot de passe ne se stocke **jamais** en clair, et jamais sous un hash
  rapide (`hashlib.sha256`, `md5`), même salé à la main. **bcrypt via
  `pwdlib`**, dont l'algorithme est lent par conception et sale
  automatiquement. Détail dans `rules/securite-api.md`.
- Saisie interactive : `getpass.getpass()`, jamais `input()`, qui affiche le
  mot de passe à l'écran et le laisse dans le terminal derrière soi.
- Un hash ne s'affiche pas plus qu'un mot de passe : il se casse hors ligne. Ni
  à l'écran, ni dans un tableau exporté, ni dans une trace d'erreur.
- Comparer par la fonction de vérification de la bibliothèque, jamais par `==`
  sur les empreintes recalculées à la main.

## Choix par défaut

Valables sauf décision contraire écrite dans le `CLAUDE.md` du dépôt, avec sa
raison :

| | |
|---|---|
| Persistance | SQLAlchemy 2.0 en asynchrone, migrations Alembic |
| Base locale ou `.exe` | SQLite (`aiosqlite`) |
| Base serveur | PostgreSQL (`asyncpg`) |
| Tests | SQLite en mémoire |
| Paquetage Windows | PyInstaller |
| Déploiement serveur | `docker-compose.yml`, images sur le registre interne |

Le code SQLAlchemy reste identique d'un contexte à l'autre : seule l'URL change.

## Style

- Nommage en français pour les concepts métier (`affaire`, `logement`,
  `escalier`), `snake_case`, explicite plutôt que court.
- Pas d'import avec `*`.
- Une fonction qui dépasse l'écran ou qui atteint trois niveaux d'indentation
  demande une extraction, pas un commentaire.
