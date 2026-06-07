import requests

# Register & Login
email = "verify@test.com"
requests.post("http://localhost:8000/register", json={"email": email, "password": "pass"})
res = requests.post("http://localhost:8000/token", data={"username": email, "password": "pass"})
token = res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Create Bot for training test
payload = {"url": "https://example.com"}
res = requests.post("http://localhost:8000/create-bot", json=payload, headers=headers)
bot_id = res.json().get("bot_id")

# Test Manual Training
train_payload = {"bot_id": bot_id, "text": "We offer a 30-day money-back guarantee."}
train_res = requests.post("http://localhost:8000/train-manual", json=train_payload, headers=headers)
print("Train response:", train_res.status_code, train_res.json())

# Test Upgrade Plan
upgrade_payload = {"plan": "Pro"}
upgrade_res = requests.post("http://localhost:8000/upgrade-plan", json=upgrade_payload, headers=headers)
print("Upgrade response:", upgrade_res.status_code, upgrade_res.json())

