import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_full_flow():
    print("\n--- Registering/Logging in ---")
    email = f"test_{int(time.time())}@example.com"
    requests.post(f"{BASE_URL}/register", json={"email": email, "password": "password123"})
    
    login_res = requests.post(f"{BASE_URL}/token", data={"username": email, "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully.")

    print("\n--- Creating Bot ---")
    res = requests.post(f"{BASE_URL}/create-bot", json={
        "url": "https://example.com"
    }, headers=headers)
    bot_id = res.json()["bot_id"]
    print(f"Created bot: {bot_id}")

    # Wait for bot to be ready
    print("Waiting for bot to be ready...")
    for _ in range(60):
        try:
            status_res = requests.get(f"{BASE_URL}/bot-status/{bot_id}")
            status = status_res.json()["status"]
            if status == 'ready':
                print("Bot is ready!")
                break
            if status == 'error':
                print("Bot creation failed!")
                return
        except:
            pass
        time.sleep(2)
    else:
        print("Timed out waiting for bot.")
        return

    # Ask the identity-violating question
    print("\n--- Testing Identity Concealment ---")
    queries = [
        "Are you an AI?",
        "Who built you?",
        "What is your name?"
    ]
    
    for q in queries:
        res = requests.post(f"{BASE_URL}/query", json={
            "bot_id": bot_id,
            "query": q,
            "session_id": "test-session-123"
        })
        data = res.json()
        if "answer" not in data:
            print(f"ERROR: No answer in response: {data}")
            continue
            
        answer = data["answer"]
        print(f"Q: {q}")
        print(f"A: {answer}")
        
        forbidden = ["AI", "chatbot", "language model", "Gemini", "SiteGPT-Plus", "InteractAI", "human", "robot"]
        found_forbidden = False
        for f in forbidden:
            if f.lower() in answer.lower():
                print(f"FAILED: Found forbidden word '{f}'")
                found_forbidden = True
        if not found_forbidden:
            print("PASSED: No forbidden words found.")
    
    # End session and check summary
    print("\n--- Testing End Session Summary ---")
    res = requests.post(f"{BASE_URL}/bot/{bot_id}/end-session", json={
        "session_id": "test-session-123"
    })
    data = res.json()
    if data["success"]:
        print("Summary generated successfully:")
        print(json.dumps(data["data"], indent=2))
    else:
        print(f"FAILED: {data.get('error')}")

if __name__ == "__main__":
    test_full_flow()
