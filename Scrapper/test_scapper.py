import requests
import json

# The configuration
url = "http://127.0.0.1:8000/api/v1/scrape"
payload = {
    "keyword": "samsung galaxy a55"
}
headers = {
    "Content-Type": "application/json"
}

try:
    # Making the POST request
    response = requests.post(url, json=payload, headers=headers)

    # Check if the request was successful
    response.raise_for_status()

    # Parse and print the JSON response
    data = response.json()
    print("--- Success! ---")
    print(json.dumps(data, indent=4))

except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
    print(f"Response Body: {response.text}")
except Exception as err:
    print(f"An error occurred: {err}")