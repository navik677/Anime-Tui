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


# ── Placeholder messages (shown in fzf list when not searching) ────────
MSG_EMPTY   = "  ·  Введіть назву аніме…"
MSG_SHORT   = "  ·  Введіть ще кілька символів…"
MSG_LOADING = "  ·  Завантаження…"
MSG_NONE    = "  ✗  Нічого не знайдено"
MSG_ERR     = "  ✗  Помилка: "


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
        print(MSG_EMPTY)
        return

    provider_file = args[0]
    query = " ".join(args[1:]).strip()
    provider_name = _load_provider(provider_file)

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
            print(f"{MSG_NONE} (Улюблені порожні)")
            return
    else:
        # ── Short / empty query (for network providers) ───────────────
        if not query:
            print(MSG_EMPTY)
            return
        if len(query) < 2:
            print(MSG_SHORT)
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
            print(f"{MSG_ERR}{exc}")
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
            results = provider.search(query, limit=25)
        except Exception as exc:
            msg = str(exc)
            if "Connection" in msg or "Network" in msg or "Errno" in msg:
                print(f"{MSG_ERR}Мережева помилка. Перевірте інтернет або VPN.")
            else:
                if len(msg) > 90:
                    msg = msg[:90] + "…"
                print(f"{MSG_ERR}{msg}")
            return

        if not results:
            print(f"{MSG_NONE} для «{query}»")
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
            "provider": provider_name,
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
