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
import time
import shutil
import subprocess
import json
import tempfile
from pathlib import Path

import requests.exceptions

from . import config as cfg
from . import ui, player, history, favorites
from .i18n import t
from .models import Anime, Episode, Quality, Stream
from .providers.base import BaseProvider


# ── Provider registry ──────────────────────────────────────────────────
def _get_provider(name: str) -> BaseProvider:
    from .providers.anilibria import AnilibriaProvider
    from .providers.yummyanime import YummyAnimeProvider
    from .providers.rezka import RezkaProvider
    from .providers.animevost import AnimeVostProvider

    mapping = {
        "anilibria":  AnilibriaProvider,
        "yummyanime": YummyAnimeProvider,
        "rezka":      RezkaProvider,
        "animevost":  AnimeVostProvider,
    }
    cls = mapping.get(name)
    if cls is None:
        _err(f"{t('err_unknown_provider')}: '{name}'. {t('cli_available_providers')} {', '.join(mapping)}")
        sys.exit(1)
    return cls()


PROVIDER_DESCRIPTIONS = {
    "anilibria":  "АніЛібрія  — офіційне API, аніме з озвучкою",
    "yummyanime": "YummyAnime — скрейпінг + yt-dlp",
    "rezka":      "HDRezka    — фільми та серіали з кількома озвучками",
    "animevost":  "AnimeVost  — швидке API, стабільно без VPN",
}

from .theme import CYAN, GREEN, YELLOW, RED, DIM, BOLD, RESET


def _err(msg: str):
    print(f"{RED}{t('error_prefix')}{RESET} {msg}", file=sys.stderr)


def _err_network(exc: Exception, provider: str):
    msg = str(exc)
    if len(msg) > 100:
        msg = msg[:100] + "…"
    print(f"{RED}{t('error_prefix')}{RESET} {t('err_network')} [{provider}]: {msg}", file=sys.stderr)
    print(f"{YELLOW}  {t('hint_network')}{RESET}", file=sys.stderr)


def _info(msg: str):
    print(f"{CYAN}[info]{RESET} {msg}")

def spawn_bg_download(anime: Anime, provider_name: str, quality_label: str, episodes: list[Episode]):
    job_data = {
        "provider": provider_name,
        "quality": quality_label,
        "anime": {
            "id": anime.id,
            "title_ru": anime.title_ru,
            "_meta": anime._meta,
        },
        "episodes": [
            {
                "number": ep.number,
                "title": ep.title,
                "_meta": ep._meta,
            } for ep in episodes
        ]
    }
    
    tmpdir = Path(tempfile.gettempdir())
    job_file = tmpdir / f"anime_tui_bg_job_{int(time.time()*1000)}.json"
    job_file.write_text(json.dumps(job_data, ensure_ascii=False), encoding="utf-8")
    
    if os.name == 'nt':
        subprocess.Popen(
            [sys.executable, "-m", "anime_tui.bg_downloader", str(job_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
        )
    else:
        subprocess.Popen(
            [sys.executable, "-m", "anime_tui.bg_downloader", str(job_file)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
    _info(f"{GREEN}Завантаження ({len(episodes)} серій) додано у фон!{RESET}")
    time.sleep(1.5)


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
            _info(t("info_loading_translators"))
            try:
                translators = provider.get_translators(anime)
                if len(translators) > 1:
                    has_translator_menu = True
                    tr = ui.select(
                        translators,
                        display_fn=lambda t: t["name"],
                        prompt=t("prompt_translator"),
                        header=f"{BOLD}{anime.display()}{RESET}\n {t('header_translator_hint')}",
                    )
                    if tr is None:
                        return # Back to search
                    anime._meta["translator_id"] = tr["id"]
                elif len(translators) == 1:
                    anime._meta["translator_id"] = translators[0]["id"]
            except Exception as exc:
                _err(f"{t('err_loading_translators')}: {exc}")

        _info(t("info_loading_episodes"))
        try:
            episodes = provider.get_episodes(anime)
        except requests.exceptions.ConnectionError as exc:
            _err_network(exc, provider.name)
            if has_translator_menu: continue
            else: return
        except Exception as exc:
            _err(f"{t('err_loading_episodes')}: {exc}")
            if has_translator_menu: continue
            else: return

        if not episodes:
            _err(t("err_no_episodes"))
            if has_translator_menu: continue
            else: return

        back_to_translators = False
        while True:
            watched_eps = history.get_watched_episodes(provider.name, str(anime.id))
            is_fav = favorites.is_favorite(provider.name, anime.id)

            def ep_display(ep):
                if ep.number == -1:
                    return f"{YELLOW}{'★' if is_fav else '☆'}{RESET} {ep.title}"
                if ep.number == -2:
                    return f"{CYAN}📥{RESET} {ep.title}"
                ep_id = str(ep.number)
                mark = f"{ui.MAGENTA}✓{ui.RESET} " if ep_id in watched_eps else "  "
                return f"{mark}{ep.display()}"

            fav_title = t("btn_remove_favorite") if is_fav else t("btn_add_favorite")
            fav_ep = Episode(number=-1, title=fav_title)
            download_all_ep = Episode(number=-2, title=t("btn_download_all"))
            display_episodes = [fav_ep, download_all_ep] + episodes

            # Calculate watched progress
            watched_count = len([e for e in episodes if str(e.number) in watched_eps])
            total_eps = len(episodes)
            bar_len = 10
            filled = int((watched_count / total_eps) * bar_len) if total_eps > 0 else 0
            progress_bar = f"{GREEN}{'■' * filled}{DIM}{'□' * (bar_len - filled)}{RESET}"
            progress_text = f" {progress_bar} {watched_count}/{total_eps} "

            episode = ui.select(
                display_episodes,
                display_fn=ep_display,
                prompt=t("prompt_episode"),
                header=(
                    f"{BOLD}{anime.display()}{RESET}\n"
                    f" {len(episodes)} {t('header_episodes_hint').format(provider.name.upper())} │ {progress_text}"
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

            if episode.number == -2:
                # Download all
                _info(f"{t('info_loading_stream')} 1…")
                if not episodes: continue
                first_ep = episodes[0]
                try:
                    stream = provider.get_stream(anime, first_ep)
                except requests.exceptions.ConnectionError as exc:
                    _err_network(exc, provider.name)
                    continue
                except Exception as exc:
                    _err(f"{t('err_loading_stream')}: {exc}")
                    continue
                
                if not stream.qualities:
                    _err(t("err_no_stream"))
                    continue
                
                chosen = ui.select(
                    stream.qualities,
                    display_fn=lambda q: f"{q.label}",
                    prompt=t("prompt_quality"),
                    header=t("header_quality").format("ALL", len(stream.qualities)),
                )
                if not chosen:
                    continue
                
                spawn_bg_download(anime, provider.name, chosen.label, episodes)
                continue

            # Normal episode action menu
            action = ui.select(
                [
                    {"id": "play", "title": t("btn_play")},
                    {"id": "download", "title": t("btn_download")}
                ],
                display_fn=lambda x: x["title"],
                prompt=t("prompt_action"),
                header=f"{BOLD}{episode.display()}{RESET}"
            )
            
            if not action:
                continue

            # ── Get stream ─────────────────────────────────────────────────
            _info(f"{t('info_loading_stream')} {episode.number}…")
            try:
                stream = provider.get_stream(anime, episode)
            except requests.exceptions.ConnectionError as exc:
                _err_network(exc, provider.name)
                continue
            except Exception as exc:
                _err(f"{t('err_loading_stream')}: {exc}")
                continue

            if not stream.qualities:
                _err(t("err_no_stream"))
                continue

            # ── Quality selection ──────────────────────────────────────────
            chosen = None
            if preferred_quality == "best" and stream.qualities:
                chosen = stream.qualities[0]
            else:
                for q in stream.qualities:
                    if q.label == preferred_quality:
                        chosen = q
                        break

            if chosen is None:
                chosen = ui.select(
                    stream.qualities,
                    display_fn=lambda q: f"{q.label}",
                    prompt=t("prompt_quality"),
                    header=t("header_quality").format(episode.number, len(stream.qualities)),
                )

            if chosen is None:
                continue

            # ── Action ──────────────────────────────────────────────────────
            if action["id"] == "play":
                _info(f"{t('info_playing')} [{chosen.label}]…")
                player.play(quality=chosen, episode=episode, title=anime.title_ru)
                history.mark_watched(provider.name, str(anime.id), str(episode.number))
            elif action["id"] == "download":
                spawn_bg_download(anime, provider.name, chosen.label, [episode])

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
            _info(t("info_exit"))
            break

        anime, provider_name = result
        current_provider_name = provider_name  # remember for next search

        # ── Init provider ──────────────────────────────────────────────
        try:
            provider = _get_provider(provider_name)
        except SystemExit:
            continue

        _info(
            f"{t('info_selected')}: {BOLD}{anime.display()}{RESET}  "
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
    Ctrl+5  →  перемкнути на AnimeVost
    Esc     →  назад / вихід
        """,
    )
    parser.add_argument(
        "-p", "--provider",
        metavar="ПРОВАЙДЕР",
        default=None,
        help="Стартовий провайдер: anilibria, yummyanime, rezka, animevost",
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
        print(f"\n{BOLD}{t('cli_available_providers')}{RESET}\n")
        for name, desc in PROVIDER_DESCRIPTIONS.items():
            print(f"  {GREEN}●{RESET} {BOLD}{name:<14}{RESET}  {DIM}{desc}{RESET}")
        print(f"\n{DIM}В інтерфейсі: Alt+1 АніЛібрія │ Alt+2 YummyAnime │ Alt+3 HDRezka │ Alt+5 AnimeVost{RESET}\n")
        sys.exit(0)

    # ── Resolve provider and quality ───────────────────────────────────
    provider_name = args.provider or cfg.get("default_provider", "anilibria")
    quality       = args.quality  or cfg.get("default_quality",  "best")

    valid_providers = {"anilibria", "yummyanime", "rezka", "animevost"}
    if provider_name not in valid_providers:
        _err(f"Невідомий провайдер '{provider_name}'. Використовую 'animevost'.")
        provider_name = "animevost"

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
        print(f"\n{DIM}{t('info_exit')}{RESET}")
        sys.exit(0)


if __name__ == "__main__":
    main()
