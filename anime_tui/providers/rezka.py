"""
HDRezka provider — uses the HdRezkaApi library for stream extraction.

Installation: pip install HdRezkaApi
Mirror URL can be configured via REZKA_URL environment variable.

Flow:
  1. Search: scrape https://hdrezka.ag/search/?do=search&subaction=search&q=<query>
  2. Episodes: use HdRezkaApi to get season/episode structure
  3. Stream: HdRezkaApi.getStream(season, episode) → decode encrypted URLs
"""
from __future__ import annotations
import os
import re
import sys
from urllib.parse import urljoin

import requests

from ..models import Anime, Episode, Quality, Stream
from .base import BaseProvider

# Allow overriding the mirror via env variable (useful if rezka.ag is blocked)
REZKA_BASE = os.environ.get("REZKA_URL", "https://hdrezka.ag")
DEFAULT_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
}

QUALITY_ORDER = ["1080p Ultra", "1080p", "720p", "480p", "360p"]


def _get_soup(html: str):
    """Parse HTML with BeautifulSoup, preferring lxml."""
    try:
        from bs4 import BeautifulSoup
        try:
            return BeautifulSoup(html, "lxml")
        except Exception:
            return BeautifulSoup(html, "html.parser")
    except ImportError:
        raise ImportError(
            "beautifulsoup4 не встановлено.\n"
            "  Встановіть: pip install --user beautifulsoup4 lxml"
        )


class RezkaProvider(BaseProvider):
    name = "rezka"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._check_library()

    def _check_library(self):
        try:
            import HdRezkaApi  # noqa: F401
        except ImportError:
            print(
                "[rezka] Бібліотека HdRezkaApi не встановлена.\n"
                "  Встановіть: pip install --user HdRezkaApi",
                file=sys.stderr,
            )

    # ── Search ──────────────────────────────────────────────────────────
    def search(self, query: str, limit: int = 20) -> list[Anime]:
        url = f"{REZKA_BASE}/search/"
        try:
            resp = self.session.get(
                url,
                params={"do": "search", "subaction": "search", "q": query},
                timeout=DEFAULT_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[rezka] Помилка пошуку: {exc}", file=sys.stderr)
            return []

        try:
            soup = _get_soup(resp.text)
        except ImportError as exc:
            print(f"[rezka] {exc}", file=sys.stderr)
            return []

        results: list[Anime] = []

        # HDRezka search results are in .b-content__inline_item blocks
        for item in soup.select(".b-content__inline_item")[:limit]:
            title_a = item.select_one(".b-content__inline_item-link a")
            if not title_a:
                continue
            
            href = title_a.get("href")
            if not href.startswith("http"):
                href = urljoin(REZKA_BASE, href)
                
            title = title_a.get_text(strip=True)
            if not title:
                continue

            # Year
            year = None
            info_div = item.select_one(".b-content__inline_item-link div")
            if info_div:
                m = re.search(r"\d{4}", info_div.get_text())
                if m:
                    year = int(m.group())

            # Category tag (Фільм / Серіал)
            cat = item.select_one(".b-content__inline_item-cover span")
            category = cat.get_text(strip=True) if cat else None

            # Poster and Description
            poster_url = None
            description = None
            img_tag = item.find("img")
            if img_tag and img_tag.get("src"):
                poster_url = img_tag.get("src")
            if info_div:
                description = info_div.get_text(strip=True)

            results.append(Anime(
                id=href,
                title_ru=title,
                year=year,
                status=category,
                provider=self.name,
                _meta={"url": href, "poster_url": poster_url, "description": description},
            ))

        return results

    # ── Translators ──────────────────────────────────────────────────────
    def get_translators(self, anime: Anime) -> list[dict]:
        try:
            from HdRezkaApi import HdRezkaApi
        except ImportError:
            return []

        page_url = anime._meta.get("url") or anime.id
        try:
            api = anime._meta.get("_api")
            if not api:
                api = HdRezkaApi(page_url)
                anime._meta["_api"] = api

            translators = []
            for tr_id, tr_data in api.translators.items():
                translators.append({
                    "id": str(tr_id),
                    "name": tr_data["name"]
                })
            return translators
        except Exception:
            return []

    # ── Episodes ─────────────────────────────────────────────────────────
    def get_episodes(self, anime: Anime) -> list[Episode]:
        try:
            from HdRezkaApi import HdRezkaApi
        except ImportError:
            print("[rezka] HdRezkaApi не встановлено. pip install --user HdRezkaApi",
                  file=sys.stderr)
            return []

        page_url = anime._meta.get("url") or anime.id
        try:
            api = HdRezkaApi(page_url)
            anime._meta["_api"] = api

            try:
                # For movies, seriesInfo throws ValueError
                seasons = api.seriesInfo
            except ValueError:
                return [Episode(number=1, title="Фільм", _meta={"type": "movie"})]

            episodes: list[Episode] = []
            season_episodes = {}
            
            selected_tr = anime._meta.get("translator_id")
            if not selected_tr:
                selected_tr = list(seasons.keys())[0]
            else:
                selected_tr = int(selected_tr)
                
            tr_data = seasons.get(selected_tr, {})
            
            for s_num, eps_dict in tr_data.get("episodes", {}).items():
                s_int = int(s_num)
                if s_int not in season_episodes:
                    season_episodes[s_int] = set()
                for ep_num in eps_dict.keys():
                    season_episodes[s_int].add(int(ep_num))
                    
            for s_int in sorted(season_episodes.keys()):
                for ep_int in sorted(season_episodes[s_int]):
                    episodes.append(Episode(
                        number=ep_int,
                        title=f"Сезон {s_int}, Серія {ep_int}",
                        _meta={"season": str(s_int), "episode": str(ep_int), "type": "series"},
                    ))
            
            if not episodes:
                return [Episode(number=1, title="Фільм", _meta={"type": "movie"})]
                
            return episodes

        except Exception as exc:
            print(f"[rezka] Помилка отримання серій: {exc}", file=sys.stderr)
            return []

    # ── Stream ───────────────────────────────────────────────────────────
    def get_stream(self, anime: Anime, episode: Episode) -> Stream:
        try:
            from HdRezkaApi import HdRezkaApi
        except ImportError:
            return Stream()

        page_url = anime._meta.get("url") or anime.id
        ep_type = episode._meta.get("type", "movie")
        qualities: list[Quality] = []

        try:
            api = anime._meta.get("_api") or HdRezkaApi(page_url)

            if ep_type == "movie":
                if anime._meta.get("translator_id"):
                    stream = api.getStream(translation=int(anime._meta["translator_id"]))
                else:
                    stream = api.getStream()
            else:
                season = str(episode._meta.get("season", "1"))
                ep_num = str(episode._meta.get("episode", "1"))
                if anime._meta.get("translator_id"):
                    stream = api.getStream(season, ep_num, translation=int(anime._meta["translator_id"]))
                else:
                    stream = api.getStream(season, ep_num)

            for label in QUALITY_ORDER:
                try:
                    result = stream(label)
                    if result:
                        # HdRezkaStream returns a list of URLs (e.g., primary and fallback)
                        url = result[0] if isinstance(result, list) else result
                        qualities.append(Quality(label=label, url=url))
                except Exception:
                    pass

        except Exception as exc:
            print(f"[rezka] Помилка отримання потоку: {exc}", file=sys.stderr)

        return Stream(qualities=qualities)
