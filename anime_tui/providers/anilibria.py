"""
Anilibria provider — uses the official public REST API v3.
API docs: https://github.com/anilibria/docs/blob/master/api_v3.md

Stream host: https://cache.libria.fun
HLS paths are relative; prepend the host to get the full URL.
"""
from __future__ import annotations
import requests
from ..models import Anime, Episode, Quality, Stream
from .base import BaseProvider
from ..config import get as get_config
from ..proxy import ProxyManager

DEFAULT_TIMEOUT = 15

HEADERS = {
    "User-Agent": "anime-tui/1.0 (github.com/user/anime-tui)",
    "Accept": "application/json",
}


class AnilibriaProvider(BaseProvider):
    name = "anilibria"

    def __init__(self):
        self.session = ProxyManager.get_session()
        self.api_base = get_config("anilibria.api_base", "https://anilibria.top/api/v1")
        self.stream_host = get_config("anilibria.stream_host", "https://cache.libria.fun")

    def search(self, query: str, limit: int = 20) -> list[Anime]:
        if not query:
            url = f"{self.api_base}/anime/releases/latest"
            params = {}
        else:
            url = f"{self.api_base}/app/search/releases"
            params = {"query": query}

        resp = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        resp.raise_for_status()
        items = resp.json()
        return [self._parse_anime(item) for item in items[:limit]]

    def get_episodes(self, anime: Anime) -> list[Episode]:
        # Fetch detailed release info to get episodes list
        release_id = anime.id
        resp = self.session.get(
            f"{self.api_base}/anime/releases/{release_id}",
            timeout=DEFAULT_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        
        episode_list = data.get("episodes", [])
        
        episodes = []
        for ep in episode_list:
            ep_num = ep.get("ordinal", "?")
            ep_name = ep.get("name")
            
            # Format skips for player.py (which expects lists like [start, end])
            skips = {}
            opening = ep.get("opening", {})
            if opening and opening.get("start") is not None and opening.get("stop") is not None:
                skips["opening"] = [opening["start"], opening["stop"]]
            ending = ep.get("ending", {})
            if ending and ending.get("start") is not None and ending.get("stop") is not None:
                skips["ending"] = [ending["start"], ending["stop"]]
                
            episodes.append(Episode(
                number=ep_num,
                title=ep_name,
                _meta={
                    "hls_480": ep.get("hls_480"),
                    "hls_720": ep.get("hls_720"),
                    "hls_1080": ep.get("hls_1080"),
                    "skips": skips,
                },
            ))
        return sorted(episodes, key=lambda e: float(str(e.number).replace(",", ".")))

    def get_stream(self, anime: Anime, episode: Episode) -> Stream:
        qualities = []
        quality_map = [
            ("1080p", "hls_1080"),
            ("720p",  "hls_720"),
            ("480p",  "hls_480"),
        ]
        for label, key in quality_map:
            url = episode._meta.get(key)
            if url:
                if url.startswith("/"):
                    url = self.stream_host + url
                qualities.append(Quality(label=label, url=url))

        return Stream(qualities=qualities)

    # ──────────────────────────────────────────────────────────
    def _parse_anime(self, item: dict) -> Anime:
        name = item.get("name", {})
        type_obj = item.get("type", {})
        
        # Parse genres
        genres = []
        for g in item.get("genres", []):
            if isinstance(g, dict) and g.get("name"):
                genres.append(g["name"])
                
        # Parse age rating and score (favorites)
        age_rating = ""
        ar_obj = item.get("age_rating")
        if isinstance(ar_obj, dict) and ar_obj.get("label"):
            age_rating = ar_obj["label"]
            
        score = ""
        favs = item.get("added_in_users_favorites")
        if favs:
            score = f"★ {favs}"

        return Anime(
            id=str(item.get("id", "")),
            title_ru=name.get("main") or name.get("english") or "Без назви",
            title_en=name.get("english"),
            year=item.get("year"),
            genres=genres,
            status=type_obj.get("description"),
            provider=self.name,
            _meta={
                "alias": item.get("alias"),
                "poster_url": "https://anilibria.top" + item["poster"]["src"] if item.get("poster") and isinstance(item["poster"], dict) and item["poster"].get("src") else None,
                "description": item.get("description"),
                "age_rating": age_rating,
                "rating": score,
                "comments": [],
            },
        )
