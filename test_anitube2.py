import requests
from bs4 import BeautifulSoup

url = "https://anitube.in.ua/2827-borto-nove-pokolnnya-nauto.html"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, "lxml")

print("Iframes:")
for iframe in soup.find_all("iframe"):
    print("  -", iframe.get("src"))

print("\nScripts:")
for script in soup.find_all("script"):
    if script.string and "player" in script.string.lower():
        print("  -", script.string[:200])

