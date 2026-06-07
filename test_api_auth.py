import requests

BASE_URL = "http://localhost:8000"

def test_auth():
    # 1. Register
    print("Registering...")
    res = requests.post(f"{BASE_URL}/register", json={"email": "api@test.com", "password": "password123"})
    print(f"Register: {res.status_code} {res.text}")
    
    # 2. Login
    print("Logging in...")
    res = requests.post(f"{BASE_URL}/token", data={"username": "api@test.com", "password": "password123"})
    print(f"Login: {res.status_code}")
    token = res.json()["access_token"]
    
    # 3. Me
    print("Getting /me...")
    res = requests.get(f"{BASE_URL}/me", headers={"Authorization": f"Bearer {token}"})
    print(f"Me: {res.status_code} {res.text}")
    
    # 4. Check DB
    import sqlite3
    import os
    db_path = os.path.abspath("db/sitegpt.db")
    print(f"Checking DB at {db_path}")
    conn = sqlite3.connect(db_path)
    users = conn.execute("SELECT email FROM users").fetchall()
    print(f"Users in DB: {users}")
    conn.close()

if __name__ == "__main__":
    test_auth()
