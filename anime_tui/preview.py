import sys
import os
import json
import urllib.request
import textwrap
from pathlib import Path

# ANSI colors
CYAN = "\033[38;5;87m"
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

    title = item.get("title_ru", "")
    meta = item.get("_meta", {})
    poster_url = meta.get("poster_url")
    description = meta.get("description", "")

    print(f"{CYAN}{BOLD}{title}{RESET}\n")

    if poster_url:
        import hashlib
        try:
            import climage
            
            # Create cache dir for covers
            cache_dir = Path(os.path.expanduser("~/.cache/anime-tui/covers"))
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Simple hash for filename
            url_hash = hashlib.md5(poster_url.encode()).hexdigest()
            img_path = cache_dir / f"{url_hash}.jpg"
            
            # Download if not exists
            if not img_path.exists():
                req = urllib.request.Request(
                    poster_url, 
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    img_data = resp.read()
                    with open(img_path, "wb") as f:
                        f.write(img_data)
            
            # Convert and print
            # 40 columns width is usually good for fzf preview pane
            out = climage.convert(str(img_path), is_unicode=True, width=40)
            print(out)
        except ImportError:
            print(f"{DIM}[постер недоступний - встановіть climage]{RESET}\n")
        except Exception:
            print(f"{DIM}[помилка завантаження постера]{RESET}\n")
    
    if description:
        # Wrap description to 50 chars for better readability
        wrapped = textwrap.fill(description, width=50)
        print(f"\n{DIM}{wrapped}{RESET}")

if __name__ == "__main__":
    main()
