"""
Theming module for anime-tui.
Provides ANSI color codes based on the selected theme (accent color).
"""
from __future__ import annotations
from . import config as cfg

THEMES = {
    "блакитна (стандартна)": "87",
    "зелена": "82",
    "оранжева": "208",
    "синя": "39",
    "фіолетова": "213",
    "червона": "196",
    "жовта": "226",
    "рожева": "205",
}

theme_name = cfg.get("theme", "блакитна (стандартна)")
if theme_name not in THEMES:
    theme_name = "блакитна (стандартна)"

fzf_acc = THEMES[theme_name]

# The primary accent color replaces CYAN everywhere
CYAN = f"\033[38;5;{fzf_acc}m"

FZF_COLORS = f"dark,fg:252,fg+:255,bg+:236,hl:{fzf_acc},hl+:{fzf_acc},pointer:{fzf_acc},marker:{fzf_acc},header:244,info:244,prompt:{fzf_acc},spinner:{fzf_acc},border:{fzf_acc}"

MAGENTA = "\033[38;5;213m"
YELLOW = "\033[38;5;220m"
GREEN = "\033[38;5;82m"
RED = "\033[38;5;196m"

RESET = "\033[0m"
DIM = "\033[2m"
BOLD = "\033[1m"
