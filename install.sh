#!/usr/bin/env bash
# ============================================================
#  anime-tui — Скрипт встановлення для Arch Linux
# ============================================================
set -euo pipefail

CYAN='\033[38;5;87m'
GREEN='\033[38;5;82m'
YELLOW='\033[38;5;220m'
RED='\033[38;5;196m'
BOLD='\033[1m'
RESET='\033[0m'

info()    { echo -e "${CYAN}[info]${RESET} $*"; }
success() { echo -e "${GREEN}[ok]${RESET} $*"; }
warn()    { echo -e "${YELLOW}[warn]${RESET} $*"; }
error()   { echo -e "${RED}[error]${RESET} $*" >&2; exit 1; }

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
  ╔═══════════════════════════════════════╗
  ║     anime-tui — Встановлення          ║
  ║     Arch Linux TUI Anime Player       ║
  ╚═══════════════════════════════════════╝
EOF
echo -e "${RESET}"

# ── Check OS ──────────────────────────────────────────────────────────
if ! command -v pacman &>/dev/null; then
    warn "pacman не знайдено. Цей скрипт розрахований на Arch Linux."
    warn "На інших дистрибутивах встановіть залежності вручну."
fi

# ── System dependencies ───────────────────────────────────────────────
info "Перевірка системних залежностей…"

MISSING_PKGS=()
for pkg in python fzf mpv; do
    if ! command -v "$pkg" &>/dev/null; then
        MISSING_PKGS+=("$pkg")
    fi
done

# yt-dlp — check separately (may be installed via pip or pacman)
if ! command -v yt-dlp &>/dev/null; then
    MISSING_PKGS+=("yt-dlp")
fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    info "Встановлення системних пакетів: ${MISSING_PKGS[*]}"
    sudo pacman -S --needed --noconfirm "${MISSING_PKGS[@]}" || \
        error "Не вдалося встановити пакети. Спробуйте вручну: sudo pacman -S ${MISSING_PKGS[*]}"
    success "Системні залежності встановлено"
else
    success "Всі системні залежності вже встановлені"
fi

# ── Python check ───────────────────────────────────────────────────────
PYTHON_VERSION=$(python --version 2>&1 | cut -d' ' -f2)
info "Python версія: ${PYTHON_VERSION}"

PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]; }; then
    error "Потрібен Python 3.10+. Поточна версія: ${PYTHON_VERSION}"
fi

# ── Install anime-tui ─────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

info "Встановлення anime-tui…"

# Prefer pipx for isolated install, fall back to pip --user
if command -v pipx &>/dev/null; then
    info "Встановлення через pipx (ізольоване середовище)…"
    pipx install --force "$SCRIPT_DIR"
    success "anime-tui встановлено через pipx"
elif python -m pip install --user --quiet "$SCRIPT_DIR"; then
    success "anime-tui встановлено через pip (--user)"
    # Ensure ~/.local/bin is in PATH
    LOCAL_BIN="$HOME/.local/bin"
    if [[ ":$PATH:" != *":$LOCAL_BIN:"* ]]; then
        warn "Додайте до ~/.bashrc або ~/.zshrc:"
        echo "  export PATH=\"\$PATH:$HOME/.local/bin\""
    fi
else
    error "Не вдалося встановити anime-tui. Спробуйте вручну: pip install --user $SCRIPT_DIR"
fi

# ── HdRezkaApi ────────────────────────────────────────────────────────
info "Встановлення Python залежностей…"
python -m pip install --user --quiet HdRezkaApi beautifulsoup4 lxml requests || \
    warn "Деякі Python залежності не вдалося встановити. Спробуйте: pip install -r requirements.txt"

# ── Generate default config ────────────────────────────────────────────
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/anime-tui"
if [ ! -f "$CONFIG_DIR/config.toml" ]; then
    info "Створення конфігураційного файлу…"
    anime-tui --init-config 2>/dev/null || true
fi

# ── Done ──────────────────────────────────────────────────────────────
echo
echo -e "${GREEN}${BOLD}✓ Встановлення завершено!${RESET}"
echo
echo -e "  Запуск:       ${BOLD}anime-tui${RESET}"
echo -e "  З провайдером: ${BOLD}anime-tui -p anilibria${RESET}"
echo -e "  Пошук:        ${BOLD}anime-tui -q \"Атака Титанів\"${RESET}"
echo -e "  Конфіг:       ${BOLD}$CONFIG_DIR/config.toml${RESET}"
echo -e "  Допомога:     ${BOLD}anime-tui --help${RESET}"
echo
