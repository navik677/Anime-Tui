import requests
from bs4 import BeautifulSoup
import json

url = "https://anitube.in.ua/index.php?do=search"
data = {"do": "search", "subaction": "search", "story": "Наруто"}
r = requests.post(url, data=data)
soup = BeautifulSoup(r.text, "lxml")
for item in soup.select("article.story")[:2]:
    a = item.select_one("h2.story_c_title a")
    if a:
        print("Found:", a.text, a["href"])
        
        # Test episode page
        r2 = requests.get(a["href"])
        s2 = BeautifulSoup(r2.text, "lxml")
        print("Iframes:", [i["src"] for i in s2.select("iframe") if "src" in i.attrs])
