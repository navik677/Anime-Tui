"""
search_cli — subprocess helper called by fzf's reload binding.

Usage (called by fzf internally):
    python3 -m anime_tui.search_cli <provider_state_file> <query...>

Outputs tab-separated lines:  <index>\t<display_text>
Results are cached to $ANIME_TUI_CACHE (JSON) so the parent process
can reconstruct Anime objects after fzf returns the selected index.
"""
from __future__ import annotations
import sys
import os
import json
from pathlib import Path

from anime_tui.i18n import t


def _load_provider(provider_file: str) -> str:
    try:
        return Path(provider_file).read_text().strip() or "anilibria"
    except Exception:
        return "anilibria"


def _make_serializable(meta: dict) -> dict:
    """Remove non-JSON-serializable objects (e.g. HdRezkaApi instance)."""
    return {k: v for k, v in meta.items() if isinstance(v, (str, int, float, bool, list, dict, type(None)))}


def main():
    args = sys.argv[1:]

    if not args:
        print(t("msg_empty"))
        return

    provider_file = args[0]
    query = " ".join(args[1:]).strip()
    provider_name = _load_provider(provider_file)
    
    import re
    
    GENRE_MAP = {
        "екшен": "экшен", "экшон": "экшен", "action": "экшен",
        "фентезі": "фэнтези", "фентези": "фэнтези", "fantasy": "фэнтези",
        "сьонен": "сёнен", "сенен": "сёнен", "shounen": "сёнен",
        "повсякденність": "повседневность", "slice": "повседневность",
        "ісекай": "исекай", "isekai": "исекай",
        "пригоди": "приключения", "adventure": "приключения",
        "жахи": "ужасы", "хоррор": "ужасы", "horror": "ужасы",
        "романтика": "романтика", "romance": "романтика",
        "комедія": "комедия", "comedy": "комедия",
        "надприродне": "сверхъестественное",
        "школа": "школа",
        "драма": "драма",
        "детектив": "детектив",
        "трилер": "триллер",
        "етті": "этти", "этти": "этти", "ecchi": "этти",
        "меха": "меха", "mecha": "меха",
        "махо-сьодзьо": "махо-сёдзё", "махо-сёдзё": "махо-сёдзё",
        "спорт": "спорт", "sports": "спорт",
        "музика": "музыка", "музыка": "музыка",
        "ігри": "игры", "игры": "игры",
        "кіберпанк": "киберпанк", "киберпанк": "киберпанк",
    }
    
    RATING_MAP = {
        "R+": ["16+", "18+", "R16", "R18"],
        "18+": ["18+", "R18"],
        "16+": ["16+", "R16"],
        "PG": ["12+", "13+", "PG"],
    }

    # Parse query for tags
    genre_filters = []
    rating_filters = []
    
    clean_query = query
    for m in re.finditer(r'(?i)(?:genre|жанр):([^\s]+)', clean_query):
        g = m.group(1).lower()
        genre_filters.append(GENRE_MAP.get(g, g))
    clean_query = re.sub(r'(?i)(?:genre|жанр):([^\s]+)', '', clean_query)
    
    for m in re.finditer(r'(?i)(?:^|\s)(R\+|18\+|16\+|PG|PG-13)(?=\s|$)', clean_query):
        r = m.group(1).upper()
        rating_filters.extend(RATING_MAP.get(r, [r]))
    clean_query = re.sub(r'(?i)(?:^|\s)(R\+|18\+|16\+|PG|PG-13)(?=\s|$)', ' ', clean_query)
    
    clean_query = clean_query.strip()

    # ── Handle Favorites Provider ──────────────────────────────────────
    if provider_name == "favorites":
        try:
            from anime_tui.favorites import get_favorites
            results = get_favorites()
        except ImportError:
            results = []
            
        if query:
            q = query.lower()
            results = [a for a in results if (a.title_ru and q in a.title_ru.lower()) or (a.title_en and q in a.title_en.lower())]
            
        if not results:
            print(f"{t('msg_none')} {t('msg_favorites_empty')}")
            return
    else:
        if len(query) == 1:
            print(t("msg_short"))
            return

        # ── Import network provider ────────────────────────────────────
        try:
            # Ensure the package is importable (when run from source dir)
            src_root = str(Path(__file__).parent.parent)
            if src_root not in sys.path:
                sys.path.insert(0, src_root)

            from anime_tui.providers.anilibria import AnilibriaProvider
            from anime_tui.providers.yummyanime import YummyAnimeProvider
            from anime_tui.providers.rezka import RezkaProvider
        except ImportError as exc:
            print(f"{t('msg_err')}{exc}")
            return

        _providers = {
            "anilibria":  AnilibriaProvider,
            "yummyanime": YummyAnimeProvider,
            "rezka":      RezkaProvider,
        }
        provider_cls = _providers.get(provider_name, AnilibriaProvider)

        # ── Search ─────────────────────────────────────────────────────
        try:
            provider = provider_cls()
            # If we have filters but no clean_query, fetch more items to filter locally
            limit = 50 if (genre_filters or rating_filters) else 25
            results = provider.search(clean_query, limit=limit)
        except Exception as exc:
            msg = str(exc)
            if "Connection" in msg or "Network" in msg or "Errno" in msg:
                print(f"{t('msg_err')}{t('err_network')}")
            else:
                if len(msg) > 90:
                    msg = msg[:90] + "…"
                print(f"{t('msg_err')}{msg}")
            return

        if genre_filters or rating_filters:
            filtered = []
            for a in results:
                # Filter by genre
                if genre_filters:
                    a_genres = [g.lower() for g in (a.genres or [])]
                    # Since some providers don't return genres in search, skip filter if a_genres is totally empty 
                    # OR we can strictly require genres to match (which drops YummyAnime/HDRezka search results).
                    # Let's be strict: if user asks for genre, only show items that match.
                    if a_genres:
                        if not all(any(req in g for g in a_genres) for req in genre_filters):
                            continue
                    else:
                        # If provider doesn't give genres, we can't filter. We drop it to be accurate.
                        # However, for HDRezka we might want to allow it? No, drop it.
                        continue
                
                # Filter by rating
                if rating_filters:
                    # check age_rating
                    ar = (a._meta.get("age_rating") or "").upper()
                    if ar:
                        if not any(req in ar for req in rating_filters):
                            continue
                    else:
                        continue
                
                filtered.append(a)
            results = filtered

        if not results:
            print(f"{t('msg_none')} для «{query}»")
            return

    # ── Cache results to JSON for parent process ───────────────────────
    cache_file = os.environ.get("ANIME_TUI_CACHE", "/tmp/anime_tui_cache.json")
    data = []
    for i, anime in enumerate(results):
        safe_meta = _make_serializable(anime._meta or {})
        data.append({
            "id":       anime.id,
            "title_ru": anime.title_ru,
            "title_en": anime.title_en,
            "year":     anime.year,
            "genres":   anime.genres or [],
            "status":   anime.status,
            "provider": anime.provider if anime.provider else provider_name,
            "_meta":    safe_meta,
        })
        # fzf sees: "index\tDisplay Text"  (--with-nth 2 hides index column)
        print(f"{i}\t{anime.display()}")

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass  # Non-fatal — parent will handle missing cache gracefully


if __name__ == "__main__":
    main()
