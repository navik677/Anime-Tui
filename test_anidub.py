import requests

url = "https://v11.anidub.digital"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
try:
    resp = requests.get(url, headers=headers, timeout=10)
    print("Status:", resp.status_code)
    print("Length:", len(resp.text))
    if "Cloudflare" in resp.text:
        print("Cloudflare protection detected!")
except Exception as e:
    print("Error:", e)
