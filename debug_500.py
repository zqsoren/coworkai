import requests
import json

url = "http://localhost:8000/api/group/chat"
payload = {
    "workspace_id": "workspace_zzzap建筑ai网站开发",
    "group_id": "group_zzzap网站开发_1",
    "message": "test"
}

try:
    print(f"Sending POST to {url}...")
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Response Body:")
    print(response.text)
except Exception as e:
    print(f"Request failed: {e}")
