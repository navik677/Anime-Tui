import json
import os
from pathlib import Path

HISTORY_FILE = Path(os.path.expanduser("~/.config/anime-tui/history.json"))

def load_history() -> dict:
    if not HISTORY_FILE.exists():
        return {}
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_history(history: dict):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def mark_watched(provider: str, anime_id: str, episode_identifier: str):
    history = load_history()
    key = f"{provider}:{anime_id}"
    if key not in history:
        history[key] = []
    if episode_identifier not in history[key]:
        history[key].append(episode_identifier)
        save_history(history)

def is_watched(provider: str, anime_id: str, episode_identifier: str) -> bool:
    history = load_history()
    key = f"{provider}:{anime_id}"
    return episode_identifier in history.get(key, [])

def get_watched_episodes(provider: str, anime_id: str) -> set:
    history = load_history()
    key = f"{provider}:{anime_id}"
    return set(history.get(key, []))
