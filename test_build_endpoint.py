"""Test script to verify build endpoint is working and logging"""

import requests
import json
import time

print("=" * 60)
print("TESTING BUILD ENDPOINT")
print("=" * 60)

url = "http://127.0.0.1:8000/api/build"
payload = {
    "place_id": "ChIJJ7VUaS0bdkgRRxOOSvN_HaE"  # Dominion Theatre
}

print(f"\n[TEST] Sending POST request to: {url}")
print(f"[TEST] Payload: {json.dumps(payload, indent=2)}")

try:
    response = requests.post(url, json=payload, timeout=5)
    print(f"\n[TEST] Response status: {response.status_code}")
    print(f"[TEST] Response body: {response.text}")
    
    if response.status_code == 202:
        data = response.json()
        session_id = data.get("session_id")
        print(f"\n[TEST] Session ID: {session_id}")
        print(f"[TEST] Cached: {data.get('cached', False)}")
        print(f"\n[TEST] Check your backend terminal for [ENDPOINT] and [BUILD] logs!")
        print(f"[TEST] The logs should show the build starting...")
    else:
        print(f"\n[TEST] ERROR: Unexpected status code {response.status_code}")
        
except requests.exceptions.ConnectionError:
    print("\n[TEST] ERROR: Could not connect to backend!")
    print("[TEST] Make sure the backend is running on http://127.0.0.1:8000")
except Exception as e:
    print(f"\n[TEST] ERROR: {e}")

print("\n" + "=" * 60)

