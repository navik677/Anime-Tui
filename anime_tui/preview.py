import sys
import os
import json
import urllib.request
import textwrap
from pathlib import Path

# ANSI colors
CYAN = "\033[38;5;87m"
MAGENTA = "\033[38;5;213m"
YELLOW = "\033[38;5;220m"
RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"

def main():
    if len(sys.argv) < 2:
        return

    idx_str = sys.argv[1].split("\t")[0].strip()
    if not idx_str.isdigit():
        return
    idx = int(idx_str)

    cache_file = os.environ.get("ANIME_TUI_CACHE")
    if not cache_file:
        return
    
    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            item = data[idx]
    except Exception:
        return

    # To get details, we should import the provider and fetch it
    provider_name = item.get("provider", "anilibria")
    
    # Construct Anime object
    # Add project root to sys.path
    src_root = str(Path(__file__).parent.parent)
    if src_root not in sys.path:
        sys.path.insert(0, src_root)
        
    try:
        from anime_tui.models import Anime
        anime = Anime(
            id=item["id"],
            title_ru=item.get("title_ru", ""),
            title_en=item.get("title_en"),
            year=item.get("year"),
            genres=item.get("genres", []),
            status=item.get("status"),
            provider=provider_name,
            _meta=item.get("_meta", {})
        )
        
        # Fetch details dynamically
        if provider_name == "anilibria":
            from anime_tui.providers.anilibria import AnilibriaProvider
            provider = AnilibriaProvider()
        elif provider_name == "yummyanime":
            from anime_tui.providers.yummyanime import YummyAnimeProvider
            provider = YummyAnimeProvider()
        elif provider_name == "rezka":
            from anime_tui.providers.rezka import RezkaProvider
            provider = RezkaProvider()
        else:
            provider = None
            
        if provider:
            anime = provider.get_details(anime)
            
    except Exception as e:
        # Fallback if something fails
        pass

    title = item.get("title_ru", "")
    meta = anime._meta if 'anime' in locals() else item.get("_meta", {})
    poster_url = meta.get("poster_url")
    description = meta.get("description", "")
    rating = meta.get("rating", "")
    age_rating = meta.get("age_rating", "")
    genres = anime.genres if 'anime' in locals() else item.get("genres", [])
    comments = meta.get("comments", [])

    print(f"{CYAN}{BOLD}{title}{RESET}\n")

    text_lines = []
    if rating:
        text_lines.append(f"{YELLOW}{rating}{RESET}")
    if age_rating:
        text_lines.append(f"{MAGENTA}Вік: {age_rating}{RESET}")
    if genres:
        text_lines.append(f"{CYAN}Жанри: {', '.join(genres)}{RESET}")
    
    if description:
        if text_lines: text_lines.append("")
        wrapped = textwrap.wrap(description, width=50)
        text_lines.extend([f"{DIM}{line}{RESET}" for line in wrapped])
        
    if comments:
        text_lines.append("")
        text_lines.append(f"{BOLD}Відгуки:{RESET}")
        for c in comments:
            text_lines.extend([f"{DIM}> {line}{RESET}" for line in textwrap.wrap(c, width=50)])
            text_lines.append("")

    img_lines = []
    has_image = False

    if poster_url:
        import hashlib
        try:
            import climage
            cache_dir = Path(os.path.expanduser("~/.cache/anime-tui/covers"))
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            url_hash = hashlib.md5(poster_url.encode()).hexdigest()
            img_path = cache_dir / f"{url_hash}.jpg"
            
            if not img_path.exists():
                req = urllib.request.Request(
                    poster_url, 
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    img_data = resp.read()
                    with open(img_path, "wb") as f:
                        f.write(img_data)
            
            # Width 40 means 40 characters wide.
            out = climage.convert(str(img_path), is_unicode=True, width=35)
            img_lines = out.strip().split('\n')
            has_image = True
        except Exception:
            pass

    if has_image:
        max_lines = max(len(img_lines), len(text_lines))
        for i in range(max_lines):
            img_part = img_lines[i] if i < len(img_lines) else " " * 35
            txt_part = text_lines[i] if i < len(text_lines) else ""
            print(f"{img_part}    {txt_part}")
    else:
        for line in text_lines:
            print(line)

if __name__ == "__main__":
    main()
