import requests

api = "https://api.animevost.org/v1"

# Last updates
r = requests.get(f"{api}/last")
print("Last updates:", r.json()["data"][0]["title"])

# Search
r = requests.post(f"{api}/search", data={"name": "Naruto"})
print("Search:", r.json()["data"][0]["title"])
print("Search ID:", r.json()["data"][0]["id"])

# Episodes (playlist)
anime_id = r.json()["data"][0]["id"]
r = requests.post(f"{api}/playlist", data={"id": anime_id})
print("Playlist:", r.json()[:2])
