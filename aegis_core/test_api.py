import requests
import json

# The product you want to search
payload = {
    "keyword": "ASUS Dual GeForce RTX 5060 8GB"
}

print("🚀 Firing keyword into AEGIS Gateway on Port 8001...")

# Hit YOUR API on port 8001 (which will internally hit your friend's on 8000)
response = requests.post("http://localhost:8001/analyze", json=payload)

print("\n--- API RESPONSE ---")
try:
    print(json.dumps(response.json(), indent=2))
except Exception:
    print(response.text)

