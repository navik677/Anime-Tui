"""
Configuration management for anime-tui.
Config file: ~/.config/anime-tui/config.toml (XDG-compliant)
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
from typing import Any

# Default configuration values
DEFAULTS: dict[str, Any] = {
    "default_provider": "anilibria",
    "default_quality": "best",
    "language": "auto",
    "theme": "default",
    "mpv_path": "mpv",
    "hide_mpv_logs": True,
    "download_dir": "~/Downloads/Anime",
    "fzf_height": "60%",
    "anilibria": {
        "api_base": "https://anilibria.top/api/v1",
        "stream_host": "https://cache.libria.fun",
    },
    "yummyanime": {
        "base_url": "https://yummyanime.club",
    },
    "rezka": {
        "base_url": "https://hdrezka.ag",
    },
    "animevost": {
        "api_base": "https://api.animevost.org/v1",
    },
}

_CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "anime-tui"
_CONFIG_FILE = _CONFIG_DIR / "config.toml"

_config: dict[str, Any] = {}


def _deep_merge(base: dict, override: dict) -> dict:
    result = base.copy()
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load() -> dict[str, Any]:
    global _config
    _config = dict(DEFAULTS)

    if _CONFIG_FILE.exists():
        try:
            # Python 3.11+ has tomllib built-in
            if sys.version_info >= (3, 11):
                import tomllib
                with open(_CONFIG_FILE, "rb") as f:
                    user_cfg = tomllib.load(f)
            else:
                try:
                    import tomli as tomllib  # type: ignore
                    with open(_CONFIG_FILE, "rb") as f:
                        user_cfg = tomllib.load(f)
                except ImportError:
                    user_cfg = {}
            _config = _deep_merge(_config, user_cfg)
        except Exception as exc:
            print(f"[config] Не вдалося завантажити конфіг: {exc}", file=sys.stderr)

    # Environment variable overrides
    if url := os.environ.get("REZKA_URL"):
        _config.setdefault("rezka", {})["base_url"] = url

    return _config


def get(key: str, default: Any = None) -> Any:
    if not _config:
        load()
    keys = key.split(".")
    val = _config
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return default
    return val if val is not None else default


def write_default_config():
    """Write default config.toml to XDG config dir."""
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if _CONFIG_FILE.exists():
        return

    content = """\
# anime-tui configuration file
# Location: ~/.config/anime-tui/config.toml

# Default provider: "anilibria", "yummyanime", or "rezka"
default_provider = "anilibria"

# Default quality preference: "best", "1080p", "720p", "480p"
default_quality = "best"

# Interface language: "auto", "uk", "ru", "en"
language = "auto"

# Visual theme: "default", "dracula", "catppuccin_mocha", "nord"
theme = "default"

# Path to mpv binary (or just "mpv" if it's in PATH)
mpv_path = "mpv"

# Hide mpv connection/ffmpeg error logs but keep status line
hide_mpv_logs = true

# Directory to save downloaded episodes
download_dir = "~/Downloads/Anime"

[anilibria]
# Override API base URL if needed (e.g., https://api.anilibria.tv/v3)
# api_base = "https://anilibria.top/api/v1"
# stream_host = "https://cache.libria.fun"

[yummyanime]
# base_url = "https://yummyanime.club"

[rezka]
# Use REZKA_URL env variable or set here for mirror
# base_url = "https://hdrezka.ag"

[animevost]
# api_base = "https://api.animevost.org/v1"
"""
    _CONFIG_FILE.write_text(content)
    print(f"[config] Конфіг збережено: {_CONFIG_FILE}")
