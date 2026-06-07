import asyncio
from fastapi.testclient import TestClient
from api.main import app, DB_PATH
import sqlite3

# Fetch the actual context for bot_id 088863dd to reproduce it exactly
client = TestClient(app)
try:
    response = client.post("/query", json={"bot_id": "088863dd", "query": "Hello"})
    print("Response Code:", response.status_code)
except Exception as e:
    print("Exception caught:")
    import traceback
    traceback.print_exc()
