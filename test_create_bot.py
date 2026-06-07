import requests

# Register
requests.post("http://localhost:8000/register", json={"email": "test422@test.com", "password": "pass"})

# Login
res = requests.post("http://localhost:8000/token", data={"username": "test422@test.com", "password": "pass"})
token = res.json()["access_token"]

payload = {
    "url": "https://example.com",
    "facebook_url": None
}
headers = {"Authorization": f"Bearer {token}"}
response = requests.post("http://localhost:8000/create-bot", json=payload, headers=headers)
print(response.status_code)
print(response.json())
