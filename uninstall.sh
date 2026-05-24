#!/usr/bin/env bash

set -e

echo -e "\033[1;36m==> Видалення Anime TUI...\033[0m"

# 1. Видалення обгортки (wrapper)
WRAPPER="$HOME/.local/bin/anime-tui"
if [ -f "$WRAPPER" ]; then
    echo -e "Видалення $WRAPPER..."
    rm "$WRAPPER"
fi

# 2. Видалення файлів програми
VENV_DIR="$HOME/.local/share/anime-tui"
if [ -d "$VENV_DIR" ]; then
    echo -e "Видалення $VENV_DIR..."
    rm -rf "$VENV_DIR"
fi

echo -e "\033[1;32m[Готово!]\033[0m Anime TUI успішно видалено з вашої системи."
