from . import config as cfg
import os

_LOCALES = {
    "uk": {
        "err_unknown_provider": "Невідомий провайдер",
        "info_loading_translators": "Отримання списку озвучок…",
        "prompt_translator": "Озвучка > ",
        "header_translator_hint": "Оберіть озвучку  •  Esc → назад",
        "err_loading_translators": "Помилка отримання озвучок",
        "info_loading_episodes": "Завантаження списку серій…",
        "err_loading_episodes": "Помилка отримання серій",
        "err_no_episodes": "Список серій порожній або недоступний.",
        "prompt_episode": "Серія > ",
        "header_episodes_hint": "серій  •  {}  •  Esc → назад",
        "info_loading_stream": "Отримання потоку для серії",
        "err_loading_stream": "Помилка отримання потоку",
        "err_no_stream": "Потік недоступний. Спробуйте іншу серію або провайдер.",
        "prompt_quality": "Якість > ",
        "header_quality": "Серія {} — {} варіантів якості",
        "info_playing": "▶  mpv",
        "info_exit": "Вихід.",
        "info_selected": "Обрано",
        "provider_favorites": "Улюблені",
        "msg_empty": "  ·  Введіть назву аніме…",
        "msg_short": "  ·  Введіть ще кілька символів…",
        "msg_loading": "  ·  Завантаження…",
        "msg_none": "  ✗  Нічого не знайдено",
        "msg_err": "  ✗  Помилка: ",
        "msg_favorites_empty": "(Улюблені порожні)",
        "btn_add_favorite": "Додати в улюблені",
        "btn_remove_favorite": "Видалити з улюблених",
        "header_nav_hint": "↑↓ навігація │ Enter — обрати │ Esc — вихід",
        "header_search_prompt": "Введіть назву аніме та натисніть Enter…",
        "header_search_title": "Пошук Аніме",
        "err_fzf_not_found": "fzf не знайдено. Встановіть fzf.",
        "err_network": "Мережева помилка. Перевірте інтернет або VPN.",
        "hint_network": "Підказка: Перевірте підключення або VPN.",
        "error_prefix": "[помилка]",
        "cli_available_providers": "Доступні провайдери:",
        "prompt_select": "Оберіть > "
    },
    "ru": {
        "err_unknown_provider": "Неизвестный провайдер",
        "info_loading_translators": "Получение списка озвучек…",
        "prompt_translator": "Озвучка > ",
        "header_translator_hint": "Выберите озвучку  •  Esc → назад",
        "err_loading_translators": "Ошибка получения озвучек",
        "info_loading_episodes": "Загрузка списка серий…",
        "err_loading_episodes": "Ошибка получения серий",
        "err_no_episodes": "Список серий пуст или недоступен.",
        "prompt_episode": "Серия > ",
        "header_episodes_hint": "серий  •  {}  •  Esc → назад",
        "info_loading_stream": "Получение потока для серии",
        "err_loading_stream": "Ошибка получения потока",
        "err_no_stream": "Поток недоступен. Попробуйте другую серию или провайдер.",
        "prompt_quality": "Качество > ",
        "header_quality": "Серия {} — {} вариантов качества",
        "info_playing": "▶  mpv",
        "info_exit": "Выход.",
        "info_selected": "Выбрано",
        "provider_favorites": "Избранное",
        "msg_empty": "  ·  Введите название аниме…",
        "msg_short": "  ·  Введите еще несколько символов…",
        "msg_loading": "  ·  Загрузка…",
        "msg_none": "  ✗  Ничего не найдено",
        "msg_err": "  ✗  Ошибка: ",
        "msg_favorites_empty": "(Избранное пусто)",
        "btn_add_favorite": "Добавить в избранное",
        "btn_remove_favorite": "Удалить из избранного",
        "header_nav_hint": "↑↓ навигация │ Enter — выбрать │ Esc — выход",
        "header_search_prompt": "Введите название аниме и нажмите Enter…",
        "header_search_title": "Поиск Аниме",
        "err_fzf_not_found": "fzf не найден. Установите fzf.",
        "err_network": "Сетевая ошибка. Проверьте интернет или VPN.",
        "hint_network": "Подсказка: Проверьте подключение или VPN.",
        "error_prefix": "[ошибка]",
        "cli_available_providers": "Доступные провайдеры:",
        "prompt_select": "Выберите > "
    },
    "en": {
        "err_unknown_provider": "Unknown provider",
        "info_loading_translators": "Fetching translators…",
        "prompt_translator": "Translator > ",
        "header_translator_hint": "Select translator  •  Esc → back",
        "err_loading_translators": "Error fetching translators",
        "info_loading_episodes": "Loading episodes…",
        "err_loading_episodes": "Error fetching episodes",
        "err_no_episodes": "Episode list is empty or unavailable.",
        "prompt_episode": "Episode > ",
        "header_episodes_hint": "episodes  •  {}  •  Esc → back",
        "info_loading_stream": "Fetching stream for episode",
        "err_loading_stream": "Error fetching stream",
        "err_no_stream": "Stream unavailable. Try another episode or provider.",
        "prompt_quality": "Quality > ",
        "header_quality": "Episode {} — {} qualities",
        "info_playing": "▶  mpv",
        "info_exit": "Exit.",
        "info_selected": "Selected",
        "provider_favorites": "Favorites",
        "msg_empty": "  ·  Enter anime title…",
        "msg_short": "  ·  Enter a few more characters…",
        "msg_loading": "  ·  Loading…",
        "msg_none": "  ✗  Nothing found",
        "msg_err": "  ✗  Error: ",
        "msg_favorites_empty": "(Favorites are empty)",
        "btn_add_favorite": "Add to favorites",
        "btn_remove_favorite": "Remove from favorites",
        "header_nav_hint": "↑↓ navigate │ Enter — select │ Esc — exit",
        "header_search_prompt": "Enter anime title and press Enter…",
        "header_search_title": "Search Anime",
        "err_fzf_not_found": "fzf not found. Please install fzf.",
        "err_network": "Network error. Check internet or VPN.",
        "hint_network": "Hint: Check internet connection or VPN.",
        "error_prefix": "[error]",
        "cli_available_providers": "Available providers:",
        "prompt_select": "Select > "
    }
}

def get_language() -> str:
    lang = cfg.get("language", "auto")
    if lang == "auto":
        sys_lang = os.environ.get("LANG", "en").lower()
        if sys_lang.startswith("uk"):
            return "uk"
        elif sys_lang.startswith("ru"):
            return "ru"
        else:
            return "en"
    return lang if lang in _LOCALES else "en"

def t(key: str) -> str:
    lang = get_language()
    return _LOCALES[lang].get(key, _LOCALES["en"].get(key, key))
