"""
fzf-based TUI with:
  - Live search (results update on Enter or after typing)
  - In-UI provider switcher (Ctrl+1 / Ctrl+2 / Ctrl+3)
  - Episode & quality selection menus
"""
from __future__ import annotations
import subprocess
import sys
import os
import json
import tempfile
import re
import shutil
from pathlib import Path
from typing import TypeVar, Callable, Optional

from .models import Anime, Episode, Quality
from .i18n import t

T = TypeVar("T")

# ── ANSI colours ──────────────────────────────────────────────────────
from .theme import RESET, BOLD, CYAN, MAGENTA, YELLOW, DIM, FZF_COLORS

RAW_BANNER = r"""
  ░█████╗░███╗░░██╗██╗███╗░░░███╗███████╗  ████████╗██╗░░░██╗██╗
  ██╔══██╗████╗░██║██║████╗░████║██╔════╝  ╚══██╔══╝██║░░░██║██║
  ███████║██╔██╗██║██║██╔████╔██║█████╗░░  ░░░██║░░░██║░░░██║██║
  ██╔══██║██║╚████║██║██║╚██╔╝██║██╔══╝░░  ░░░██║░░░██║░░░██║██║
  ██║░░██║██║░╚███║██║██║░╚═╝░██║███████╗  ░░░██║░░░╚██████╔╝██║
  ╚═╝░░╚═╝╚═╝░░╚══╝╚═╝╚═╝░░░░╚═╝╚══════╝  ░░░╚═╝░░░░╚═════╝░╚═╝
"""

def _generate_gradient_banner():
    colors = [87, 81, 75, 69, 63, 57, 93, 129, 165, 201, 207, 213]
    out = []
    lines = RAW_BANNER.strip("\n").split("\n")
    for line in lines:
        colored_line = ""
        length = max(len(line), 1)
        for j, char in enumerate(line):
            color_idx = int((j / length) * (len(colors) - 1))
            colored_line += f"\033[38;5;{colors[color_idx]}m{char}"
        out.append(colored_line + "\033[0m")
    out.append(f"{DIM}  TUI Anime Player  •  Anilibria / YummyAnime / HDRezka{RESET}")
    return "\n".join(out)

BANNER = _generate_gradient_banner()

PROVIDER_LABELS = {
    "anilibria":  "АніЛібрія",
    "yummyanime": "YummyAnime",
    "rezka":      "HDRezka",
    "favorites":  "Улюблені",
}

def _check_fzf():
    r = subprocess.run(["which", "fzf"], capture_output=True)
    if r.returncode != 0:
        print(f"{YELLOW}[ERROR]{RESET} fzf не знайдено. sudo pacman -S fzf", file=sys.stderr)
        sys.exit(1)


# ─────────────────────────────────────────────────────────────────────
# LIVE SEARCH WITH PROVIDER SWITCHER
# ─────────────────────────────────────────────────────────────────────

ALL_GENRES = [
    "Екшен", "Комедія", "Романтика", "Драма", "Фентезі", "Ісекай", 
    "Надприродне", "Пригоди", "Жахи", "Детектив", "Сьонен", "Сейнен", 
    "Повсякденність", "Меха", "Етті", "Спорт", "Музика", "Ігри", "Кіберпанк"
]

def search_anime(initial_provider: str = "anilibria", initial_query: str = "") -> Optional[tuple[Anime, str]]:
    """
    Open fzf with live search and Ctrl+1/2/3 provider switcher.
    Returns (Anime, provider_name) or None if user cancelled.
    """
    _check_fzf()

    pid = os.getpid()
    tmpdir = Path(tempfile.gettempdir())
    provider_file = tmpdir / f"anime_tui_prov_{pid}"
    cache_file    = tmpdir / f"anime_tui_cache_{pid}.json"
    alt_g_file    = tmpdir / f"anime_tui_altg_{pid}"

    provider_file.write_text(initial_provider)

    try:
        while True:
            env = os.environ.copy()
            env["ANIME_TUI_CACHE"] = str(cache_file)
            src_root = str(Path(__file__).parent.parent)
            prev_path = env.get("PYTHONPATH", "")
            env["PYTHONPATH"] = f"{src_root}:{prev_path}" if prev_path else src_root

            py  = sys.executable
            pf  = str(provider_file)
            cf  = str(cache_file)
            label = PROVIDER_LABELS.get(initial_provider, initial_provider)
            if initial_provider == "favorites":
                label = t("provider_favorites")

            # Use reload(cmd) parentheses form — allows safe action chaining with +
            # {q} is fzf's placeholder for the current query string
            search_cmd = f"{py} -m anime_tui.search_cli {pf} {{q}}"

            term_width = shutil.get_terminal_size((80, 20)).columns

            if term_width < 75:
                header = (
                    f"{CYAN}{BOLD}  ANIME TUI{RESET} {DIM}• Anilibria / YummyAnime / HDRezka / AnimeVost{RESET}\n"
                    f" Alt+1 АніЛібрія │ Alt+2 YummyAnime │ Alt+3 HDRezka │ Alt+5 AnimeVost \n"
                    f" Alt+G Жанри │ Alt+T Тема │ Alt+D Завантаження │ {t('header_nav_hint')}"
                )
            else:
                header = (
                    BANNER + "\n"
                    f"{DIM}[ Alt+1 АніЛібрія ]   [ Alt+2 YummyAnime ]   [ Alt+3 HDRezka ]   [ Alt+5 AnimeVost ]   [ Alt+4 Улюблені ]{RESET}\n"
                    f"{DIM}[ Alt+G Жанри ]   [ Alt+T Змінити Тему ]   [ Alt+D Завантаження ]   ↑↓ навігація | Enter — обрати | Esc — вихід{RESET}"
                )

            # Non-empty placeholder so fzf does NOT exit immediately on empty stdin.
            # The leading tab matches our --delimiter=\t --with-nth=2 format.
            placeholder = f"\t  ⌨   {t('header_search_prompt')}"

            fzf_args = [
                "fzf",
                "--disabled",           # fzf does NOT filter — results come from reload
                "--ansi",
                "--layout=reverse",
                "--border=rounded",
                "--border-label", f" {t('header_search_title')}: {label} ",
                "--border-label-pos=3",
                "--padding=1,2",
                "--margin=1,2",
                "--height=100%",
                f"--color={FZF_COLORS}",
                "--prompt", f" > ",
                "--query", initial_query,
                "--header", header,
                "--header-first",
                "--info=inline",
                "--delimiter", "\t",
                "--with-nth", "2",      # hide index column; show only display text
                "--preview", f"{py} -m anime_tui.preview {{1}}",
                "--preview-window", "right:45%,border-left,<120(bottom:45%,border-top)",
                "--no-sort",
                "--no-exit-0",          # do NOT exit when list is empty
                "--no-select-1",        # do NOT auto-select single item
                # Trigger initial search for top 10
                "--bind", f"start:reload({search_cmd})",
                # Also reload on every keystroke after ≥2 chars (search_cli
                # returns a placeholder for short queries, so it's cheap)
                "--bind", f"change:reload({search_cmd})",
                # ── Provider switch (alt-1/2/3, universally supported in fzf) ─────────
                "--bind", (
                    f"alt-1:execute-silent(echo anilibria > {pf})"
                    f"+change-border-label( {t('header_search_title')}: АніЛібрія )"
                    f"+reload({search_cmd})"
                ),
                "--bind", (
                    f"alt-2:execute-silent(echo yummyanime > {pf})"
                    f"+change-border-label( {t('header_search_title')}: YummyAnime )"
                    f"+reload({search_cmd})"
                ),
                "--bind", (
                    f"alt-3:execute-silent(echo rezka > {pf})"
                    f"+change-border-label( {t('header_search_title')}: HDRezka )"
                    f"+reload({search_cmd})"
                ),
                "--bind", (
                    f"alt-5:execute-silent(echo animevost > {pf})"
                    f"+change-border-label( {t('header_search_title')}: AnimeVost )"
                    f"+reload({search_cmd})"
                ),
                "--bind", (
                    f"alt-4:execute-silent(echo favorites > {pf})"
                    f"+change-border-label( {t('header_search_title')}: {t('provider_favorites')} )"
                    f"+reload({search_cmd})"
                ),
                "--bind", (
                    f"alt-g:execute-silent(echo __GENRE_SELECT__ > {alt_g_file}; echo {{q}} >> {alt_g_file})+abort"
                ),
                "--bind", (
                    f"alt-t:execute-silent(echo __THEME_SELECT__ > {alt_g_file})+abort"
                ),
                "--bind", (
                    f"alt-d:execute-silent(echo __DOWNLOADS_UI__ > {alt_g_file})+abort"
                ),
            ]

            try:
                result = subprocess.run(
                    fzf_args,
                    input=placeholder,          # non-empty — prevents immediate fzf exit
                    stdout=subprocess.PIPE,     # capture selected item
                    # stderr NOT captured — fzf errors are visible in terminal
                    text=True,
                    env=env,
                )
            except FileNotFoundError:
                print(f"[ERROR] {t('err_fzf_not_found')}", file=sys.stderr)
                return None

            if alt_g_file.exists():
                content = alt_g_file.read_text(encoding="utf-8").splitlines()
                try: alt_g_file.unlink()
                except: pass
                if content and content[0] == "__GENRE_SELECT__":
                    current_query = content[1] if len(content) > 1 else ""
                    chosen_genre = select(ALL_GENRES, prompt="Оберіть жанр > ", header="Пошук за жанром")
                    if chosen_genre:
                        initial_query = f"{current_query} genre:{chosen_genre}".strip()
                    else:
                        initial_query = current_query
                    initial_provider = provider_file.read_text().strip()
                    continue
                elif content and content[0] == "__THEME_SELECT__":
                    from .theme import THEMES
                    chosen_theme = select(list(THEMES.keys()), prompt="Оберіть тему > ", header="Зміна теми (Застосується миттєво)")
                    if chosen_theme:
                        from . import config as cfg
                        if not cfg._CONFIG_FILE.exists():
                            cfg.write_default_config()
                        cfg_content = cfg._CONFIG_FILE.read_text(encoding="utf-8")
                        cfg_content = re.sub(r'theme\s*=\s*".*"', f'theme = "{chosen_theme}"', cfg_content)
                        cfg._CONFIG_FILE.write_text(cfg_content, encoding="utf-8")
                        # Restart to apply global imports
                        os.execv(sys.executable, [sys.executable, "-m", "anime_tui.main"])
                    else:
                        initial_query = content[1] if len(content) > 1 else ""
                        initial_provider = provider_file.read_text().strip()
                        continue
                elif content and content[0] == "__DOWNLOADS_UI__":
                    subprocess.run([sys.executable, "-m", "anime_tui.status_ui"])
                    initial_provider = provider_file.read_text().strip()
                    continue

            # fzf exit codes:
            #   0   = item selected normally
            #   1   = no match (shouldn't happen with --no-exit-0, but handle it)
            #   2   = error (invalid args, etc.) — fzf already printed reason to stderr
            #   130 = Esc / Ctrl+C
            if result.returncode in (2, 130):
                return None
            if result.returncode not in (0, 1):
                return None

            selected_line = result.stdout.strip()

            # Reject placeholder / error / empty selections
            if not selected_line or selected_line.lstrip().startswith(("⌨", "✗", "·")):
                return None

            # Parse "index\tDisplay Text"
            parts = selected_line.split("\t", 1)
            try:
                idx = int(parts[0])
            except (ValueError, IndexError):
                return None

            # Read cache written by search_cli
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                item = data[idx]
            except Exception:
                return None

            provider_name = item.get("provider", initial_provider)
            anime = Anime(
                id=item["id"],
                title_ru=item["title_ru"],
                title_en=item.get("title_en"),
                year=item.get("year"),
                genres=item.get("genres", []),
                status=item.get("status"),
                provider=provider_name,
                _meta=item.get("_meta", {}),
            )
            return anime, provider_name

    finally:
        _cleanup(provider_file)
        _cleanup(cache_file)
        _cleanup(alt_g_file)

def _cleanup(path: Path):
    try:
        path.unlink()
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────
# GENERIC SELECTOR  (episodes, quality)
# ─────────────────────────────────────────────────────────────────────

def select(
    items: list[T],
    display_fn: Callable[[T], str] = str,
    prompt: str = "Оберіть > ",
    header: Optional[str] = None,
) -> Optional[T]:
    """Show items in fzf, return selected item or None."""
    if not items:
        return None

    _check_fzf()
    labels = [display_fn(item) for item in items]

    fzf_args = [
        "fzf",
        "--prompt", f" {prompt}",
        "--layout=reverse",
        "--border=rounded",
        "--padding=1,2",
        "--margin=1,2",
        "--height=100%",
        f"--color={FZF_COLORS}",
        "--info=inline",
        "--ansi",
        "--no-sort",
    ]
    if header:
        fzf_args += ["--border-label", f" {header} ", "--border-label-pos=3"]

    try:
        result = subprocess.run(
            fzf_args,
            input="\n".join(labels),
            stdout=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError:
        print("[ERROR] fzf не знайдено.", file=sys.stderr)
        sys.exit(1)

    if result.returncode != 0:
        return None

    chosen = result.stdout.strip()
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    for item, label in zip(items, labels):
        stripped_label = ansi_escape.sub('', label).strip()
        if stripped_label == chosen:
            return item
    return None


def confirm(message: str) -> bool:
    choice = select(["Так", "Ні"], prompt=f"{message} > ")
    return choice == "Так"
