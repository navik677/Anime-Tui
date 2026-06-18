"""
AnimeVost provider.
Site: https://animevost.org
API: https://api.animevost.org/v1
"""
from __future__ import annotations
import requests
import sys
import re

from ..models import Anime, Episode, Quality, Stream
from .base import BaseProvider
from ..proxy import ProxyManager
from ..config import get as get_config

DEFAULT_TIMEOUT = 10

class AnimeVostProvider(BaseProvider):
    name = "animevost"

    def __init__(self):
        self.session = ProxyManager.get_session()
        self.api_url = get_config("animevost.api_base")

    def search(self, query: str, limit: int = 20) -> list[Anime]:
        try:
            if not query:
                # Latest releases
                r = self.session.get(f"{self.api_url}/last", timeout=DEFAULT_TIMEOUT, verify=False)
                r.raise_for_status()
                data = r.json().get("data", [])
            else:
                r = self.session.post(f"{self.api_url}/search", data={"name": query}, timeout=DEFAULT_TIMEOUT, verify=False)
                r.raise_for_status()
                data = r.json().get("data", [])
                
            results = []
            for item in data[:limit]:
                title = item.get("title", "Без назви")
                anime_id = str(item.get("id"))
                desc = item.get("description", "").replace("<br>", "\n").strip()
                
                # Try to extract year and title_ru
                title_parts = title.split("/")
                title_ru = title_parts[0].strip()
                year = None
                if item.get("year"):
                    try:
                        year = int(re.search(r"\d{4}", str(item["year"])).group())
                    except:
                        pass
                
                results.append(Anime(
                    id=anime_id,
                    title_ru=title_ru,
                    year=year,
                    description=desc,
                    _meta={"item": item}
                ))
            return results
        except Exception as e:
            print(f"[animevost] Помилка пошуку: {e}", file=sys.stderr)
            return []

    def get_episodes(self, anime: Anime) -> list[Episode]:
        try:
            r = self.session.post(f"{self.api_url}/playlist", data={"id": anime.id}, timeout=DEFAULT_TIMEOUT, verify=False)
            r.raise_for_status()
            data = r.json()
            
            if isinstance(data, dict) and "error" in data:
                return []
                
            episodes = []
            for ep in data:
                ep_name = ep.get("name", "Епізод")
                # Try to extract number
                m = re.search(r"(\d+)", ep_name)
                num = int(m.group(1)) if m else len(episodes) + 1
                
                episodes.append(Episode(
                    number=num,
                    title=ep_name,
                    _meta={"hd": ep.get("hd"), "std": ep.get("std")}
                ))
            return sorted(episodes, key=lambda x: x.number)
        except Exception as e:
            print(f"[animevost] Помилка отримання серій: {e}", file=sys.stderr)
            return []

    def get_stream(self, anime: Anime, episode: Episode) -> Stream:
        qualities = []
        hd_url = episode._meta.get("hd")
        std_url = episode._meta.get("std")
        
        if hd_url:
            qualities.append(Quality("720p", hd_url))
        if std_url:
            qualities.append(Quality("480p", std_url))
            
        if not qualities:
            raise ValueError("No video urls found in episode metadata")
            
        return Stream(qualities=qualities)
