"""
Main CLI entrypoint for anime-tui.

Usage:
  anime-tui                          # interactive mode (provider picker in UI)
  anime-tui -p anilibria             # start with Anilibria
  anime-tui -q "Атака Титанів"       # start with pre-filled search (not yet supported in live mode)
  anime-tui --quality 1080p          # prefer specific quality
  anime-tui --list-providers         # show available providers
  anime-tui --init-config            # create default config file
"""
from __future__ import annotations
import argparse
import sys
import os

import requests.exceptions
import time
import shutil

from . import config as cfg
from . import ui, player, history, favorites
from .models import Anime, Episode, Quality, Stream
from .providers.base import BaseProvider


# ── Provider registry ──────────────────────────────────────────────────
def _get_provider(name: str) -> BaseProvider:
    from .providers.anilibria import AnilibriaProvider
    from .providers.yummyanime import YummyAnimeProvider
    from .providers.rezka import RezkaProvider
    mapping = {
        "anilibria":  AnilibriaProvider,
        "yummyanime": YummyAnimeProvider,
        "rezka":      RezkaProvider,
    }
    cls = mapping.get(name)
    if cls is None:
        _err(f"Невідомий провайдер: '{name}'. Доступні: {', '.join(mapping)}")
        sys.exit(1)
    return cls()


PROVIDER_DESCRIPTIONS = {
    "anilibria":  "АніЛібрія  — офіційне API, аніме з озвучкою",
    "yummyanime": "YummyAnime — скрейпінг + yt-dlp",
    "rezka":      "HDRezka    — фільми та серіали з кількома озвучками",
}

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[38;5;87m"
GREEN  = "\033[38;5;82m"
YELLOW = "\033[38;5;220m"
RED    = "\033[38;5;196m"
DIM    = "\033[2m"


def _err(msg: str):
    print(f"{RED}[помилка]{RESET} {msg}", file=sys.stderr)


def _err_network(exc: Exception, provider: str):
    msg = str(exc)
    if len(msg) > 100:
        msg = msg[:100] + "…"
    print(f"{RED}[помилка]{RESET} Мережева помилка [{provider}]: {msg}", file=sys.stderr)
    print(f"{YELLOW}  Підказка:{RESET} Перевірте підключення або VPN.", file=sys.stderr)


def _info(msg: str):
    print(f"{CYAN}[info]{RESET} {msg}")


# ─────────────────────────────────────────────────────────────────────
# EPISODE PLAYBACK LOOP
# ─────────────────────────────────────────────────────────────────────

def episode_loop(provider: BaseProvider, anime: Anime, preferred_quality: str):
    """
    Show episode list → pick episode → pick quality → play → loop back.
    Returns when user presses Esc on episode selection.
    """
    while True:
        has_translator_menu = False
        
        if hasattr(provider, "get_translators"):
            _info("Отримання списку озвучок…")
            try:
                translators = provider.get_translators(anime)
                if len(translators) > 1:
                    has_translator_menu = True
                    tr = ui.select(
                        translators,
                        display_fn=lambda t: t["name"],
                        prompt="Озвучка > ",
                        header=f"{BOLD}{anime.display()}{RESET}\n Оберіть озвучку  •  Esc → назад",
                    )
                    if tr is None:
                        return # Back to search
                    anime._meta["translator_id"] = tr["id"]
                elif len(translators) == 1:
                    anime._meta["translator_id"] = translators[0]["id"]
            except Exception as exc:
                _err(f"Помилка отримання озвучок: {exc}")

        _info("Завантаження списку серій…")
        try:
            episodes = provider.get_episodes(anime)
        except requests.exceptions.ConnectionError as exc:
            _err_network(exc, provider.name)
            if has_translator_menu: continue
            else: return
        except Exception as exc:
            _err(f"Помилка отримання серій: {exc}")
            if has_translator_menu: continue
            else: return

        if not episodes:
            _err("Список серій порожній або недоступний.")
            if has_translator_menu: continue
            else: return

        back_to_translators = False
        while True:
            watched_eps = history.get_watched_episodes(provider.name, str(anime.id))
            is_fav = favorites.is_favorite(provider.name, anime.id)

            def ep_display(ep):
                if ep.number == -1:
                    return f"{YELLOW}{'★' if is_fav else '☆'}{RESET} {ep.title}"
                ep_id = str(ep.number)
                mark = f"{ui.MAGENTA}✓{ui.RESET} " if ep_id in watched_eps else "  "
                return f"{mark}{ep.display()}"

            fav_title = "Видалити з улюблених" if is_fav else "Додати в улюблені"
            fav_ep = Episode(number=-1, title=fav_title)
            display_episodes = [fav_ep] + episodes

            episode = ui.select(
                display_episodes,
                display_fn=ep_display,
                prompt="Серія > ",
                header=(
                    f"{BOLD}{anime.display()}{RESET}\n"
                    f" {len(episodes)} серій  •  {provider.name.upper()}  •  Esc → назад"
                ),
            )
            if episode is None:
                # Esc on Episode
                if has_translator_menu:
                    back_to_translators = True
                    break
                else:
                    return  # back to search
                    
            if episode.number == -1:
                favorites.toggle_favorite(anime)
                continue

            # ── Get stream ─────────────────────────────────────────────────
            _info(f"Отримання потоку для серії {episode.number}…")
            try:
                stream = provider.get_stream(anime, episode)
            except requests.exceptions.ConnectionError as exc:
                _err_network(exc, provider.name)
                continue
            except Exception as exc:
                _err(f"Помилка отримання потоку: {exc}")
                continue

            if not stream.qualities:
                _err("Потік недоступний. Спробуйте іншу серію або провайдер.")
                continue

            # ── Quality selection ──────────────────────────────────────────
            chosen: Quality | None = None
            # Try preferred quality first
            for q in stream.qualities:
                if q.label == preferred_quality:
                    chosen = q
                    break

            if chosen is None:
                # Prompt user to pick
                chosen = ui.select(
                    stream.qualities,
                    display_fn=lambda q: f"{q.label}",
                    prompt="Якість > ",
                    header=f"Серія {episode.number} — {len(stream.qualities)} варіантів якості",
                )

            if chosen is None:
                continue # back to episode list

            # ── Play ───────────────────────────────────────────────────────
            _info(f"▶  mpv  [{chosen.label}]…")
            player.play(quality=chosen, episode=episode, title=anime.title_ru)
            
            # After playback: mark as watched and loop back
            history.mark_watched(provider.name, str(anime.id), str(episode.number))

        if back_to_translators:
            continue
        else:
            break


# ─────────────────────────────────────────────────────────────────────
# MAIN SEARCH LOOP
# ─────────────────────────────────────────────────────────────────────

def run_main_loop(initial_provider: str, preferred_quality: str):
    """
    Outer loop: live-search anime → watch episodes → back to search.
    Provider can be switched inside the search fzf with Ctrl+1/2/3.
    """
    current_provider_name = initial_provider

    while True:
        # ── Live search (returns Anime + provider name) ────────────────
        result = ui.search_anime(initial_provider=current_provider_name)

        if result is None:
            _info("Вихід.")
            break

        anime, provider_name = result
        current_provider_name = provider_name  # remember for next search

        # ── Init provider ──────────────────────────────────────────────
        try:
            provider = _get_provider(provider_name)
        except SystemExit:
            continue

        _info(
            f"Обрано: {BOLD}{anime.display()}{RESET}  "
            f"({CYAN}{provider_name}{RESET})"
        )

        # ── Episode loop ───────────────────────────────────────────────
        episode_loop(provider, anime, preferred_quality)
        # After episode_loop returns → back to search (outer while loop)


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="anime-tui",
        description="TUI Програвач Аніме • Anilibria / YummyAnime / HDRezka",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади:
  anime-tui                              # відкрити з live-search
  anime-tui -p anilibria                 # почати з Anilibria
  anime-tui -p rezka                     # почати з HDRezka
  anime-tui --quality 1080p              # завжди 1080p
  anime-tui --list-providers             # список провайдерів
  REZKA_URL=https://rezka.ag anime-tui   # дзеркало HDRezka

  В інтерфейсі:
    Ctrl+1  →  перемкнути на АніЛібрія
    Ctrl+2  →  перемкнути на YummyAnime
    Ctrl+3  →  перемкнути на HDRezka
    Esc     →  назад / вихід
        """,
    )
    parser.add_argument(
        "-p", "--provider",
        metavar="ПРОВАЙДЕР",
        default=None,
        help="Стартовий провайдер: anilibria, yummyanime, rezka",
    )
    parser.add_argument(
        "--quality",
        metavar="ЯКІСТЬ",
        default=None,
        help="Бажана якість: 1080p, 720p, 480p",
    )
    parser.add_argument(
        "--list-providers",
        action="store_true",
        help="Показати список провайдерів та вийти",
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Створити дефолтний конфіг-файл і вийти",
    )
    return parser


def main():
    cfg.load()
    parser = build_parser()
    args = parser.parse_args()

    # ── Special flags ──────────────────────────────────────────────────
    if args.init_config:
        cfg.write_default_config()
        sys.exit(0)

    if args.list_providers:
        print(f"\n{BOLD}Доступні провайдери:{RESET}\n")
        for name, desc in PROVIDER_DESCRIPTIONS.items():
            print(f"  {GREEN}●{RESET} {BOLD}{name:<14}{RESET}  {DIM}{desc}{RESET}")
        print(f"\n{DIM}В інтерфейсі: Alt+1 АніЛібрія │ Alt+2 YummyAnime │ Alt+3 HDRezka{RESET}\n")
        sys.exit(0)

    # ── Resolve provider and quality ───────────────────────────────────
    provider_name = args.provider or cfg.get("default_provider", "anilibria")
    quality       = args.quality  or cfg.get("default_quality",  "720p")

    valid_providers = {"anilibria", "yummyanime", "rezka"}
    if provider_name not in valid_providers:
        _err(f"Невідомий провайдер '{provider_name}'. Використовую 'anilibria'.")
        provider_name = "anilibria"

    def show_splash():
        if not sys.stdout.isatty():
            return
        # Get terminal lines to vertically center the banner
        term_lines = shutil.get_terminal_size().lines
        padding = max(0, term_lines // 3)
        
        print("\033[2J\033[H", end="")
        print("\n" * padding, end="")
        lines = ui.BANNER.split("\n")
        for line in lines:
            print(line)
            sys.stdout.flush()
            time.sleep(0.06)
        time.sleep(0.6)

    # ── Run ────────────────────────────────────────────────────────────
    try:
        show_splash()
        run_main_loop(provider_name, quality)
    except KeyboardInterrupt:
        print(f"\n{DIM}Вихід…{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
