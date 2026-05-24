#!/usr/bin/env bash

set -e

echo -e "\033[1;36m==> Встановлення Anime TUI...\033[0m"

# 1. Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo -e "\033[1;31m[Помилка]\033[0m Python 3 не знайдено. Встановіть Python 3."
    exit 1
fi

# 2. Check for system dependencies (fzf, mpv)
echo -e "\033[1;34m==> Перевірка системних залежностей (fzf, mpv, yt-dlp)...\033[0m"
MISSING_PKGS=""
if ! command -v fzf &> /dev/null; then MISSING_PKGS="fzf $MISSING_PKGS"; fi
if ! command -v mpv &> /dev/null; then MISSING_PKGS="mpv $MISSING_PKGS"; fi
if ! command -v yt-dlp &> /dev/null; then MISSING_PKGS="yt-dlp $MISSING_PKGS"; fi

if [ -n "$MISSING_PKGS" ]; then
    echo -e "\033[1;33m[Попередження]\033[0m Відсутні системні пакети: $MISSING_PKGS"
    echo -e "Спроба автоматичного встановлення..."
    
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y $MISSING_PKGS
    elif command -v pacman &> /dev/null; then
        sudo pacman -S --noconfirm $MISSING_PKGS
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y $MISSING_PKGS
    elif command -v brew &> /dev/null; then
        brew install $MISSING_PKGS
    else
        echo -e "\033[1;31m[Помилка]\033[0m Не вдалося визначити пакетний менеджер. Будь ласка, встановіть '$MISSING_PKGS' вручну."
        exit 1
    fi
fi

# 3. Create virtualenv and install python dependencies
VENV_DIR="$HOME/.local/share/anime-tui/venv"
echo -e "\033[1;34m==> Налаштування віртуального середовища Python...\033[0m"
mkdir -p "$HOME/.local/share/anime-tui"
python3 -m venv "$VENV_DIR"

echo -e "\033[1;34m==> Встановлення Python пакетів...\033[0m"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install requests climage HdRezkaApi

# 4. Copy source code
echo -e "\033[1;34m==> Копіювання файлів...\033[0m"
cp -r anime_tui "$HOME/.local/share/anime-tui/"

# 5. Create executable wrapper
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
WRAPPER="$BIN_DIR/anime-tui"

cat > "$WRAPPER" << 'EOF'
#!/usr/bin/env bash
export PYTHONPATH="$HOME/.local/share/anime-tui:$PYTHONPATH"
exec "$HOME/.local/share/anime-tui/venv/bin/python" -m anime_tui.main "$@"
EOF

chmod +x "$WRAPPER"

echo -e "\033[1;32m[Готово!]\033[0m Anime TUI успішно встановлено!"
echo -e "Увага: переконайтеся, що \033[1m$BIN_DIR\033[0m додано до вашого \$PATH."
echo -e "Якщо ви використовуєте ZSH або Bash і команда 'anime-tui' не працює, виконайте:"
echo -e "  \033[36mecho 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc && source ~/.zshrc\033[0m"
echo -e "\nЗапустити програму можна командою: \033[1;36manime-tui\033[0m"
