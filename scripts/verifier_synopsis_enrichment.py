"""
Script de vérification manuelle de l'enrichissement automatique du synopsis
via Wikipedia — à lancer depuis la racine du dépôt.

Usage:
    python scripts/verifier_synopsis_enrichment.py [tmdb_id]

Exemple:
    python scripts/verifier_synopsis_enrichment.py 539
"""

import sys
from pathlib import Path

# Ajoute la racine du dépôt au path (ce script vit dans scripts/)
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

from agents.tools.wiki_tools import wikipedia_search
from database.connection import db_session
from database.queries import get_film_details_by_id


def test_synopsis_enrichment(tmdb_id: int):
    """
    Teste l'enrichissement du synopsis pour un film donné.

    Args:
        tmdb_id: ID TMDB du film à tester
    """
    print(f"\n🎬 Test d'enrichissement du synopsis pour le film {tmdb_id}\n")
    print("=" * 70)

    # 1. Récupérer le film depuis la BDD
    with db_session() as session:
        film = get_film_details_by_id(session, tmdb_id)

        if not film:
            print(f"❌ Film {tmdb_id} introuvable dans la base de données")
            return

        print("\n📝 Informations du film :")
        print(f"   Titre : {film.title}")
        print(f"   Année : {film.release_date.year if film.release_date else 'N/A'}")
        print(f"   Réalisateur : {film.director or 'N/A'}")
        print(f"   Genres : {', '.join(film.genres) if film.genres else 'N/A'}")

        # 2. Vérifier si le synopsis existe
        has_synopsis = bool(film.synopsis and film.synopsis.strip())
        print("\n📖 Synopsis actuel :")

        if has_synopsis:
            print(f"   ✅ Synopsis présent en BDD ({len(film.synopsis)} caractères)")
            print(f"   Extrait : {film.synopsis[:200]}...")
        else:
            print("   ⚠️  Synopsis manquant ou vide en BDD")

        # 3. Tenter l'enrichissement via Wikipedia
        print("\n🌐 Tentative d'enrichissement via Wikipedia :")

        year = film.release_date.year if film.release_date else None
        wiki_result = wikipedia_search.invoke({"title": film.title, "year": year})

        print(f"   Statut : {wiki_result.get('source', 'UNKNOWN')}")

        if wiki_result.get("source") == "wikipedia":
            wiki_synopsis = wiki_result.get("synopsis", "")
            print(
                f"   ✅ Synopsis Wikipedia récupéré ({len(wiki_synopsis)} caractères)"
            )
            print(f"   URL : {wiki_result.get('source_url', 'N/A')}")
            print(f"   Extrait : {wiki_synopsis[:200]}...")

            if not has_synopsis:
                print("\n✨ Le synopsis serait enrichi automatiquement par l'API")
        else:
            print("   ❌ Impossible de récupérer le synopsis depuis Wikipedia")
            if "error" in wiki_result:
                print(f"   Erreur : {wiki_result['error']}")

    print("\n" + "=" * 70)
    print("✅ Test terminé\n")


def main():
    """Point d'entrée du script."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/verifier_synopsis_enrichment.py [tmdb_id]")
        print("\nExemples de films à tester :")
        print("  - 539 : Psycho (1960)")
        print("  - 694 : The Shining (1980)")
        print("  - 745 : The Sixth Sense (1999)")
        sys.exit(1)

    try:
        tmdb_id = int(sys.argv[1])
        test_synopsis_enrichment(tmdb_id)
    except ValueError:
        print("❌ Erreur : L'argument doit être un nombre entier (TMDB ID)")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur lors du test : {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
