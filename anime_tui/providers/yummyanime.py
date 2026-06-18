"""
YummyAnime provider — web scraping + yt-dlp for stream extraction.
Site: https://yummyanime.club

Because YummyAnime uses embedded players (Kodik, Alloha, etc.) that require
JavaScript to resolve stream URLs, we rely on yt-dlp as a universal extractor.

Flow:
  1. Search: GET /search/?q=<query> → parse anime list from HTML
  2. Episodes: scrape the anime page for episode links
  3. Stream: pass embed URL to yt-dlp to extract direct stream URL
"""
from __future__ import annotations
import subprocess
import json
import re
import sys
from urllib.parse import urljoin

import requests

from ..models import Anime, Episode, Quality, Stream
from .base import BaseProvider

BASE_URL = "https://yummyanime.tv"
DEFAULT_TIMEOUT = 20

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "uk-UA,uk;q=0.9,ru;q=0.8,en;q=0.7",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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


class YummyAnimeProvider(BaseProvider):
    name = "yummyanime"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    # ── Search ──────────────────────────────────────────────────────────
    def search(self, query: str, limit: int = 20) -> list[Anime]:
        if not query:
            url = BASE_URL
            try:
                resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"[yummyanime] Помилка: {exc}", file=sys.stderr)
                return []
        else:
            url = f"{BASE_URL}/index.php?do=search"
            data = {
                "do": "search",
                "subaction": "search",
                "story": query,
            }
            try:
                resp = self.session.post(url, data=data, timeout=DEFAULT_TIMEOUT)
                resp.raise_for_status()
            except requests.RequestException as exc:
                print(f"[yummyanime] Помилка пошуку: {exc}", file=sys.stderr)
                return []

        try:
            soup = _get_soup(resp.text)
        except ImportError as exc:
            print(f"[yummyanime] {exc}", file=sys.stderr)
            return []

        results: list[Anime] = []
        items = soup.select(".movie-item")

        for item in items[:limit]:
            link = item.select_one("a.movie-item__link")
            if not link:
                continue

            href = urljoin(BASE_URL, link.get("href", ""))
            
            title_el = item.select_one(".movie-item__title")
            title = title_el.get_text(strip=True) if title_el else ""

            year = None
            meta_div = item.select_one(".movie-item__meta")
            if meta_div:
                m = re.search(r"\d{4}", meta_div.get_text())
                if m:
                    year = int(m.group())

            # Poster and Description
            poster_url = None
            description = None
            img_tag = item.select_one("img")
            if img_tag and img_tag.get("src"):
                poster_url = urljoin(BASE_URL, img_tag.get("src"))
            
            desc_div = item.select_one(".movie-item__text")
            if desc_div:
                description = desc_div.get_text(strip=True)

            if title and href:
                results.append(Anime(
                    id=href,
                    title_ru=title,
                    year=year,
                    provider=self.name,
                    _meta={"url": href, "poster_url": poster_url, "description": description},
                ))

        return results

    # ── Details ──────────────────────────────────────────────────────────
    def get_details(self, anime: Anime) -> Anime:
        page_url = anime._meta.get("url") or anime.id
        try:
            resp = self.session.get(page_url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
            soup = _get_soup(resp.text)
            
            # Scrape description
            desc_div = soup.select_one("#text-hide")
            if desc_div:
                anime._meta["description"] = desc_div.get_text(strip=True)
                
            # Scrape rating
            rating_span = soup.select_one(".rating-value")
            if rating_span:
                anime._meta["rating"] = f"★ {rating_span.get_text(strip=True)}"
                
            # Scrape genres
            genres = []
            for a_tag in soup.select("ul.content-main-info li a[href*='genre']"):
                genres.append(a_tag.get_text(strip=True))
            if genres:
                anime.genres = genres
                
            # Age rating (often in li items)
            for li in soup.select("ul.content-main-info li"):
                text = li.get_text(strip=True)
                if "Возрастное ограничение:" in text:
                    anime._meta["age_rating"] = text.replace("Возрастное ограничение:", "").strip()
                    
            # Comments
            comments = []
            for comment_div in soup.select(".comments-item")[:3]:
                text_div = comment_div.select_one(".comments-item__text")
                if text_div:
                    comments.append(text_div.get_text(strip=True))
            anime._meta["comments"] = comments
            
        except Exception as exc:
            print(f"[yummyanime] get_details помилка: {exc}", file=sys.stderr)
            
        return anime

    # ── Episodes ─────────────────────────────────────────────────────────
    def get_episodes(self, anime: Anime) -> list[Episode]:
        page_url = anime._meta.get("url") or anime.id
        try:
            resp = self.session.get(page_url, timeout=DEFAULT_TIMEOUT)
            resp.raise_for_status()
        except requests.RequestException as exc:
            print(f"[yummyanime] Помилка отримання серій: {exc}", file=sys.stderr)
            return []

        try:
            soup = _get_soup(resp.text)
        except ImportError as exc:
            print(f"[yummyanime] {exc}", file=sys.stderr)
            return []

        episodes: list[Episode] = []

        # Try multiple episode list selectors
        ep_selectors = [
            ".episode-item",
            ".episodes-list li",
            ".serial-series-item",
            ".watch-series-link",
            ".episode-link",
            "[data-episode]",
            ".ep-item",
            ".series-item",
        ]
        items = []
        for sel in ep_selectors:
            items = soup.select(sel)
            if items:
                break

        if not items:
            # Fallback: look for Kodik AJAX player (xfplayer)
            xfplayer = soup.find("div", class_="xfplayer")
            if xfplayer and xfplayer.get("data-params"):
                params = xfplayer["data-params"]
                ajax_url = f"{BASE_URL}/engine/ajax/controller.php?{params}"
                try:
                    r = self.session.get(ajax_url, timeout=DEFAULT_TIMEOUT)
                    data = r.json()
                    if data.get("success") and data.get("data"):
                        url = data["data"]
                        if not url.startswith("http"):
                            url = "https:" + url.replace("\\/", "/")
                        episodes.append(Episode(
                            number=1,
                            title="Фільм / Повний епізод",
                            _meta={"embed_url": url},
                        ))
                        return episodes
                except Exception as e:
                    pass

            # Fallback 2: look for a player iframe (movie)
            iframe = soup.find("iframe", src=True)
            if iframe:
                episodes.append(Episode(
                    number=1,
                    title="Фільм / Повний епізод",
                    _meta={"embed_url": iframe["src"]},
                ))
            else:
                # Last resort: the page URL itself for yt-dlp
                episodes.append(Episode(
                    number=1,
                    title="Епізод",
                    _meta={"embed_url": page_url},
                ))
            return episodes

        for i, item in enumerate(items, 1):
            link = item.find("a", href=True)
            ep_num = i
            embed_url = page_url

            # Try to extract episode number
            for attr in ["data-episode", "data-num", "data-ep"]:
                val = item.get(attr, "")
                if val:
                    try:
                        ep_num = int(val)
                        break
                    except ValueError:
                        pass
            else:
                text = item.get_text()
                m = re.search(r"(\d+)", text)
                if m:
                    ep_num = int(m.group(1))

            ep_title = item.get_text(strip=True)
            if link:
                embed_url = urljoin(BASE_URL, link["href"])

            episodes.append(Episode(
                number=ep_num,
                title=ep_title if ep_title and ep_title != str(ep_num) else None,
                _meta={"embed_url": embed_url},
            ))

        try:
            episodes.sort(key=lambda e: int(str(e.number)))
        except Exception:
            pass
        return episodes

    # ── Stream via yt-dlp ────────────────────────────────────────────────
    def get_stream(self, anime: Anime, episode: Episode) -> Stream:
        embed_url = episode._meta.get("embed_url") or anime._meta.get("url") or anime.id

        qualities: list[Quality] = []
        try:
            result = subprocess.run(
                [
                    "yt-dlp", "--dump-json",
                    "--no-playlist",
                    "--user-agent", HEADERS["User-Agent"],
                    "--add-headers", f"Referer:{BASE_URL}",
                    embed_url,
                ],
                capture_output=True, text=True, timeout=45,
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                formats = info.get("formats", [])
                seen_heights: set[int] = set()
                for fmt in reversed(formats):
                    height = fmt.get("height") or 0
                    url = fmt.get("url", "")
                    if not url or height in seen_heights:
                        continue
                    seen_heights.add(height)
                    label = f"{height}p" if height else "auto"
                    qualities.append(Quality(
                        label=label,
                        url=url,
                        headers={"Referer": BASE_URL},
                    ))
                qualities.sort(
                    key=lambda q: int(q.label.replace("p", "").replace("auto", "0")),
                    reverse=True,
                )
            else:
                err = result.stderr[:300].strip()
                print(f"[yummyanime] yt-dlp помилка:\n  {err}", file=sys.stderr)
        except FileNotFoundError:
            print("[yummyanime] yt-dlp не знайдено. Встановіть: sudo pacman -S yt-dlp",
                  file=sys.stderr)
        except subprocess.TimeoutExpired:
            print("[yummyanime] yt-dlp перевищив час очікування.", file=sys.stderr)
        except json.JSONDecodeError:
            print("[yummyanime] Не вдалося розпарсити вивід yt-dlp.", file=sys.stderr)

        return Stream(qualities=qualities)
