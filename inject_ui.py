import re

with open("anime_tui/ui.py", "r") as f:
    code = f.read()

# Add ALL_GENRES
genres_def = """
ALL_GENRES = [
    "Екшен", "Комедія", "Романтика", "Драма", "Фентезі", "Ісекай", 
    "Надприродне", "Пригоди", "Жахи", "Детектив", "Сьонен", "Сейнен", 
    "Повсякденність", "Меха", "Етті", "Спорт", "Музика", "Ігри", "Кіберпанк"
]

def search_anime(initial_provider: str = "anilibria", initial_query: str = "") -> Optional[tuple[Anime, str]]:"""

code = code.replace('def search_anime(initial_provider: str = "anilibria") -> Optional[tuple[Anime, str]]:', genres_def)

# Add alt_g_file
altg = """    provider_file = tmpdir / f"anime_tui_prov_{pid}"
    cache_file    = tmpdir / f"anime_tui_cache_{pid}.json"
    alt_g_file    = tmpdir / f"anime_tui_altg_{pid}"

    provider_file.write_text(initial_provider)
    
    try:
        while True:"""
code = code.replace("""    provider_file = tmpdir / f"anime_tui_prov_{pid}"\n    cache_file    = tmpdir / f"anime_tui_cache_{pid}.json"\n\n    provider_file.write_text(initial_provider)""", altg)

# Indent the block between `while True:` and `finally:`
lines = code.split("\n")
new_lines = []
in_while = False
for line in lines:
    if "while True:" in line:
        new_lines.append(line)
        in_while = True
        continue
    
    if in_while and "try:\n        provider_file.unlink()" in line:
        # Actually this is in the finally block. We'll replace it entirely later
        pass

    if in_while and line.startswith("def _cleanup"):
        in_while = False
        
    if in_while and line != "":
        new_lines.append("    " + line)
    else:
        new_lines.append(line)

code = "\n".join(new_lines)

# Fix finally and alt_g
# We need to replace the old try-finally around subprocess.run, and append the alt_g logic
old_try = """
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
        finally:
            try:
                provider_file.unlink()
            except Exception:
                pass"""

new_try = """
        try:
            result = subprocess.run(
                fzf_args,
                input=placeholder,
                stdout=subprocess.PIPE,
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
                continue"""

code = code.replace(old_try, new_try)

# Replace returns to not cleanup, because we do it in finally
code = code.replace("            _cleanup(cache_file)\n            return None", "            return None")
code = code.replace("        _cleanup(cache_file)\n\n        provider_name", "        provider_name")

# Add finally at the end of search_anime
code = code.replace("""        )
        return anime, provider_name""", """        )
        return anime, provider_name

    finally:
        _cleanup(provider_file)
        _cleanup(cache_file)
        _cleanup(alt_g_file)""")

# Add alt-g bind and initial_query
code = code.replace("""        "--prompt", f" > ",\n        "--header", header,""", """        "--prompt", f" > ",\n        "--query", initial_query,\n        "--header", header,""")
code = code.replace("""            f"+change-border-label( {t('header_search_title')}: {t('provider_favorites')} )"\n            f"+reload({search_cmd})"\n        ),\n    ]""", """            f"+change-border-label( {t('header_search_title')}: {t('provider_favorites')} )"\n            f"+reload({search_cmd})"\n        ),\n        "--bind", (\n            f"alt-g:execute-silent(echo __GENRE_SELECT__ > {alt_g_file}; echo {{q}} >> {alt_g_file})+abort"\n        ),\n    ]""")

with open("anime_tui/ui.py", "w") as f:
    f.write(code)
