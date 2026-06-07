import asyncio
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)
try:
    response = client.post("/query", json={"bot_id": "088863dd", "query": "Hello"})
    print(response.status_code)
    print(response.json())
except Exception as e:
    import traceback
    traceback.print_exc()
