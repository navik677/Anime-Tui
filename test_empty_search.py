import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from anime_tui.providers.anilibria import AnilibriaProvider
from anime_tui.providers.rezka import RezkaProvider
from anime_tui.providers.yummyanime import YummyAnimeProvider

def test_empty_query():
    for Prov in [AnilibriaProvider, RezkaProvider, YummyAnimeProvider]:
        print(f"\n--- {Prov.name} ---")
        try:
            p = Prov()
            results = p.search("")
            for r in results[:3]:
                print(f"  {r.title_ru}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_empty_query()
