"""
Background downloader worker.
Runs independently of the TUI to download episodes/seasons in the background.
"""
from __future__ import annotations
import sys
import os
import json
import subprocess
import time
from pathlib import Path

from anime_tui.models import Anime, Episode, Quality
from anime_tui.models import Anime, Episode, Quality
from anime_tui import config as cfg
from anime_tui import downloader

def send_notification(title: str, message: str):
    try:
        subprocess.run(["notify-send", "-a", "Anime TUI", title, message], check=False)
    except FileNotFoundError:
        pass  # notify-send not installed

def log_msg(msg: str):
    log_file = Path(os.path.expanduser("~/.cache/anime-tui/downloads.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")

def main():
    if len(sys.argv) < 2:
        sys.exit(1)
        
    job_file = Path(sys.argv[1])
    if not job_file.exists():
        sys.exit(1)
        
    try:
        data = json.loads(job_file.read_text(encoding="utf-8"))
    except Exception as e:
        log_msg(f"Failed to read job file: {e}")
        sys.exit(1)
        
    provider_name = data.get("provider")
    quality_label = data.get("quality")
    anime_data = data.get("anime", {})
    episodes_data = data.get("episodes", [])
    
    
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
        log_msg(f"Invalid provider: {provider_name}")
        sys.exit(1)
    
    anime = Anime(
        id=anime_data.get("id"),
        title_ru=anime_data.get("title_ru"),
        _meta=anime_data.get("_meta", {})
    )
    
    total = len(episodes_data)
    anime_title = anime.title_ru or "Unknown Anime"
    
    send_notification("Початок завантаження", f"{anime_title} ({total} серій)")
    log_msg(f"Started background download job for {anime_title} ({total} episodes)")
    
    success_count = 0
    
    for i, ep_data in enumerate(episodes_data, 1):
        ep = Episode(
            number=ep_data.get("number"),
            title=ep_data.get("title"),
            _meta=ep_data.get("_meta", {})
        )
        
        ep_display = ep.display()
        log_msg(f"Fetching stream for {ep_display}...")
        
        try:
            stream = provider.get_stream(anime, ep)
            if not stream or not stream.qualities:
                raise Exception("No streams found")
                
            if quality_label == "best" and stream.qualities:
                chosen = stream.qualities[0]
            else:
                chosen = next((q for q in stream.qualities if q.label == quality_label), None)
            if not chosen:
                chosen = stream.qualities[0] # Fallback
                
            log_msg(f"Starting yt-dlp for {ep_display} ({chosen.label})...")
            
            # Use downloader module but capture output to log file
            download_dir = Path(cfg.get("download_dir", "~/Downloads/Anime")).expanduser()
            safe_anime_title = "".join(c if c.isalnum() or c in " -_[]()" else "_" for c in anime_title).strip()
            safe_episode_title = "".join(c if c.isalnum() or c in " -_[]()" else "_" for c in ep_display).strip()
            out_dir = download_dir / safe_anime_title
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{safe_episode_title}.mp4"
            
            args = ["yt-dlp"]
            if chosen.headers.get("Referer"):
                args += ["--add-header", f"Referer:{chosen.headers['Referer']}"]
            if chosen.headers.get("User-Agent"):
                args += ["--user-agent", chosen.headers['User-Agent']]
            args += ["-o", str(out_path), chosen.url]
            args += ["--newline"]
            
            status_file = Path(os.path.expanduser("~/.cache/anime-tui/status.json"))
            
            def update_status(percent="0%", speed="", eta=""):
                status_data = {
                    "active": True,
                    "pid": os.getpid(),
                    "anime": anime_title,
                    "episode": ep_display,
                    "percent": percent,
                    "speed": speed,
                    "eta": eta,
                    "current": i,
                    "total": total
                }
                try:
                    status_file.write_text(json.dumps(status_data, ensure_ascii=False), encoding="utf-8")
                except:
                    pass
            
            update_status()
            
            process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            for line in process.stdout:
                line = line.strip()
                if "[download]" in line and "%" in line:
                    parts = line.split()
                    try:
                        percent_str = next((p for p in parts if "%" in p), "0%")
                        speed_str = next((p for p in parts if "iB/s" in p or "B/s" in p), "")
                        eta_str = next((p for p in parts if ":" in p and "ETA" not in p), "")
                        update_status(percent_str, speed_str, eta_str)
                    except:
                        pass
            
            process.wait()
            r_returncode = process.returncode
                
            if r_returncode == 0:
                success_count += 1
                send_notification("Завантажено серію", f"{anime_title} - {ep_display}")
                log_msg(f"Success: {ep_display}")
            else:
                send_notification("Помилка завантаження", f"{anime_title} - {ep_display}")
                log_msg(f"Error: yt-dlp failed for {ep_display}")
                
        except Exception as e:
            log_msg(f"Error getting stream for {ep_display}: {e}")
            send_notification("Помилка завантаження", f"Не вдалося отримати потік для {ep_display}")
            
    # Cleanup
    try:
        job_file.unlink()
    except:
        pass
        
    log_msg(f"Job completed. Successfully downloaded {success_count}/{total} episodes.")
    if total > 1:
        if success_count == total:
            send_notification("Завершено!", f"Усі {total} серій '{anime_title}' успішно завантажено.")
        else:
            send_notification("Завершено з помилками", f"Завантажено {success_count}/{total} серій '{anime_title}'.")
    try:
        status_file = Path(os.path.expanduser("~/.cache/anime-tui/status.json"))
        if status_file.exists():
            status_data = json.loads(status_file.read_text(encoding="utf-8"))
            status_data["active"] = False
            status_file.write_text(json.dumps(status_data, ensure_ascii=False), encoding="utf-8")
    except:
        pass

if __name__ == "__main__":
    main()
