import requests
url = "https://api.libria.fun/v3/title/updates"
try:
    r = requests.get(url, timeout=5)
    print("libria.fun status:", r.status_code)
except Exception as e:
    print("libria.fun error:", e)

url2 = "https://api.anilibria.tv/v3/title/updates"
try:
    r = requests.get(url2, timeout=5)
    print("anilibria.tv status:", r.status_code)
except Exception as e:
    print("anilibria.tv error:", e)
