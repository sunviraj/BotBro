import asyncio
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
try:
    response = client.post("/token", data={"username": "admin@botbro.com", "password": "wrongpassword"})
    print("Response Code:", response.status_code)
    print("Body:", response.json())
except Exception as e:
    print("Exception caught:")
    import traceback
    traceback.print_exc()
