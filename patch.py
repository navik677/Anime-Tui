with open("anime_tui/ui.py", "r") as f:
    code = f.read()

import re
match = re.search(r'def search_anime\(.*?def _cleanup', code, flags=re.DOTALL)
if not match:
    print("Could not find search_anime function!")
    exit(1)

old_search_anime = match.group(0)

new_search_anime = """ALL_GENRES = [
    "Екшен", "Комедія", "Романтика", "Драма", "Фентезі", "Ісекай", 
    "Надприродне", "Пригоди", "Жахи", "Детектив", "Сьонен", "Сейнен", 
    "Повсякденність", "Меха", "Етті", "Спорт", "Музика", "Ігри", "Кіберпанк"
]

def search_anime(initial_provider: str = "anilibria", initial_query: str = "") -> Optional[tuple[Anime, str]]:
    \"\"\"
    Open fzf with live search and Ctrl+1/2/3 provider switcher.
    Returns (Anime, provider_name) or None if user cancelled.
    \"\"\"
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
                    f"{CYAN}{BOLD}  ANIME TUI{RESET} {DIM}• Anilibria / YummyAnime / HDRezka{RESET}\\n"
                    f" Alt+1 АніЛібрія │ Alt+2 YummyAnime │ Alt+3 HDRezka │ Alt+4 {t('provider_favorites')} \\n"
                    f" {t('header_nav_hint')}"
                )
            else:
                header = (
                    BANNER + "\\n"
                    f" [ Alt+1 АніЛібрія ]   [ Alt+2 YummyAnime ]   [ Alt+3 HDRezka ]   [ Alt+4 {t('provider_favorites')} ] \\n"
                    f" {t('header_nav_hint')}"
                )

            # Non-empty placeholder so fzf does NOT exit immediately on empty stdin.
            # The leading tab matches our --delimiter=\\t --with-nth=2 format.
            placeholder = f"\\t  ⌨   {t('header_search_prompt')}"

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
                "--delimiter", "\\t",
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
                    f"alt-4:execute-silent(echo favorites > {pf})"
                    f"+change-border-label( {t('header_search_title')}: {t('provider_favorites')} )"
                    f"+reload({search_cmd})"
                ),
                "--bind", (
                    f"alt-g:execute-silent(echo __GENRE_SELECT__ > {alt_g_file}; echo {{q}} >> {alt_g_file})+abort"
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

            # Parse "index\\tDisplay Text"
            parts = selected_line.split("\\t", 1)
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

def _cleanup"""

code = code.replace(old_search_anime, new_search_anime)

with open("anime_tui/ui.py", "w") as f:
    f.write(code)
