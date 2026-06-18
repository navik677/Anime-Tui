import requests
try:
    r = requests.get("https://kodikapi.com/search", timeout=5)
    print("kodik status:", r.status_code)
except Exception as e:
    print("kodik error:", e)
