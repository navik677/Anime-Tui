import json
import os
from pathlib import Path
from .models import Anime

def get_favorites_file() -> Path:
    p = Path(os.path.expanduser("~/.config/anime-tui/favorites.json"))
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def get_favorites() -> list[Anime]:
    file = get_favorites_file()
    if not file.exists():
        return []
    
    try:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        animes = []
        for item in data:
            animes.append(Anime(
                id=item["id"],
                title_ru=item["title_ru"],
                title_en=item.get("title_en"),
                year=item.get("year"),
                genres=item.get("genres", []),
                status=item.get("status"),
                provider=item["provider"],
                _meta=item.get("_meta", {}),
            ))
        return animes
    except Exception:
        return []

def _save_favorites(animes: list[Anime]):
    file = get_favorites_file()
    data = []
    for anime in animes:
        data.append({
            "id": anime.id,
            "title_ru": anime.title_ru,
            "title_en": anime.title_en,
            "year": anime.year,
            "genres": anime.genres,
            "status": anime.status,
            "provider": anime.provider,
            "_meta": anime._meta,
        })
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_favorite(provider: str, anime_id: str) -> bool:
    animes = get_favorites()
    for anime in animes:
        if anime.provider == provider and str(anime.id) == str(anime_id):
            return True
    return False

def toggle_favorite(anime: Anime) -> bool:
    """Returns True if added, False if removed."""
    animes = get_favorites()
    for i, a in enumerate(animes):
        if a.provider == anime.provider and str(a.id) == str(anime.id):
            animes.pop(i)
            _save_favorites(animes)
            return False
            
    animes.insert(0, anime)
    _save_favorites(animes)
    return True
