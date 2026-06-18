"""
Downloader module for anime-tui.
Handles downloading streams via yt-dlp.
"""
from __future__ import annotations
import os
import subprocess
import sys
from pathlib import Path

from .models import Quality
from . import config as cfg
from .i18n import t
from .theme import CYAN, GREEN, RED, RESET

def download_stream(quality: Quality, anime_title: str, episode_title: str):
    """
    Downloads a stream using yt-dlp, blocking the UI so progress is visible.
    """
    download_dir = Path(cfg.get("download_dir", "~/Downloads/Anime")).expanduser()
    
    # Clean up names for filesystem
    safe_anime_title = "".join(c if c.isalnum() or c in " -_[]()" else "_" for c in anime_title).strip()
    safe_episode_title = "".join(c if c.isalnum() or c in " -_[]()" else "_" for c in episode_title).strip()
    
    out_dir = download_dir / safe_anime_title
    out_dir.mkdir(parents=True, exist_ok=True)
    
    out_path = out_dir / f"{safe_episode_title}.mp4"
    
    print(f"\n{CYAN}[info]{RESET} {t('info_downloading')}: {safe_anime_title} - {safe_episode_title}")
    print(f"       -> {out_path}\n")

    args = ["yt-dlp"]
    
    # HTTP headers
    if quality.headers.get("Referer"):
        args += ["--add-header", f"Referer:{quality.headers['Referer']}"]
    if quality.headers.get("User-Agent"):
        args += ["--user-agent", quality.headers['User-Agent']]

    args += ["-o", str(out_path)]
    args += [quality.url]

    try:
        subprocess.run(args)
        print(f"\n{GREEN}[info]{RESET} {t('info_download_success')} {out_path}\n")
    except KeyboardInterrupt:
        print(f"\n{RED}[скасовано]{RESET}\n")
    except FileNotFoundError:
        print(f"\n{RED}[помилка]{RESET} yt-dlp не знайдено.\nВстановіть: pip install yt-dlp", file=sys.stderr)
