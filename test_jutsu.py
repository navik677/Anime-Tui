import requests
try:
    r = requests.get("https://jut.su", timeout=5)
    print("jut.su status:", r.status_code)
except Exception as e:
    print("jut.su error:", e)
