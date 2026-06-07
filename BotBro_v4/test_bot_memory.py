import requests
import uuid

session_id = str(uuid.uuid4())
bot_id = "test_bot"
url = "http://localhost:8000/query"

# Step 1: Initial Question
print("\n--- User: What services do you have?")
res1 = requests.post(url, json={
    "session_id": session_id,
    "bot_id": bot_id,
    "query": "What specific services are included in your Creative Motion Design and AI & Software Engineering offerings?"
})
print(f"Bot: {res1.json()['answer'][:200]}...")

# Step 2: Providing Name and Phone
print("\n--- User: Yes, my name is John and my phone number is 01983832, and I want to create a map animated YouTube short video.")
res2 = requests.post(url, json={
    "session_id": session_id,
    "bot_id": bot_id,
    "query": "Yes, my name is John and my phone number is 01983832, and I want to create a map animated YouTube short video."
})
print(f"Bot: {res2.json()['answer'][:200]}...")

# Step 3: Direct to team
print("\n--- User: Yes, direct this to your Creative Motion Design team.")
res3 = requests.post(url, json={
    "session_id": session_id,
    "bot_id": bot_id,
    "query": "Yes, direct this to your Creative Motion Design team."
})
print(f"Bot: {res3.json()['answer'][:200]}...")

# Step 4: Final confirmation attempt
print("\n--- User: initiate the order now.")
res4 = requests.post(url, json={
    "session_id": session_id,
    "bot_id": bot_id,
    "query": "I already told you my name is John and number 01983832. Initiate the order now for the map animation."
})
print(f"Bot: {res4.json()['answer']}")

