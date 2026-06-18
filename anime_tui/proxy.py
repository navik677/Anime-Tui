import requests
import sys
import os
import time

PROXY_CACHE_FILE = os.path.expanduser("~/.cache/anime-tui/proxy.txt")
PROXY_LIST_URL = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=elite"

class ProxyManager:
    _current_proxy = None

    @classmethod
    def get_working_proxy(cls, test_url="https://api.animevost.org/v1/last") -> dict | None:
        # Since we migrated to WARP and Custom Mirrors, free proxies are disabled
        # because they are slow, unreliable, and cause false-positive hangs.
        return None

    @classmethod
    def get_session(cls) -> requests.Session:
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        })
        proxies = cls.get_working_proxy()
        if proxies:
            session.proxies.update(proxies)
        return session
