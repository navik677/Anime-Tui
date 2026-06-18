import re
with open("anime_tui/providers/yummyanime.py", "r") as f:
    content = f.read()

new_logic = """
        if not items:
            # Fallback: look for Kodik AJAX player (xfplayer)
            xfplayer = soup.find("div", class_="xfplayer")
            if xfplayer and xfplayer.get("data-params"):
                params = xfplayer["data-params"]
                ajax_url = f"{BASE_URL}/engine/ajax/controller.php?{params}"
                try:
                    r = self.session.get(ajax_url, timeout=DEFAULT_TIMEOUT)
                    data = r.json()
                    if data.get("success") and data.get("data"):
                        url = data["data"]
                        if not url.startswith("http"):
                            url = "https:" + url.replace("\\\\/", "/")
                        episodes.append(Episode(
                            number=1,
                            title="Фільм / Повний епізод",
                            _meta={"embed_url": url},
                        ))
                        return episodes
                except Exception as e:
                    pass

            # Fallback 2: look for a player iframe (movie)
"""

content = content.replace("        if not items:\n            # Fallback: look for a player iframe (movie)", new_logic.strip("\n"))

with open("anime_tui/providers/yummyanime.py", "w") as f:
    f.write(content)
