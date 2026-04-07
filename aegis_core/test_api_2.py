import requests

payload = {
    "keyword": "ASUS Dual GeForce RTX 5060 8GB",
    "email": "lakshmanchedde@gmail.com",
    "interval_minutes": 1 # Set to 1 minute for the live demo!
}

response = requests.post("http://localhost:8001/monitor/start", json=payload)
print(response.json())