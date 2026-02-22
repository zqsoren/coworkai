import requests
import sys
import time
import json

BASE_URL = "http://localhost:8000"

def test_health():
    print(f"Testing {BASE_URL}/...")
    try:
        resp = requests.get(f"{BASE_URL}/")
        print(f"✅ Status: {resp.status_code}")
        print(f"   Response: {resp.json()}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        print("Tip: Make sure the server is running on port 8000")
        return False

def test_workspaces():
    print(f"\nTesting {BASE_URL}/api/workspaces...")
    resp = requests.get(f"{BASE_URL}/api/workspaces")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Found {len(data)} workspaces")
        for ws in data[:3]:
            print(f"   - {ws['name']} ({ws['id']})")
        return data
    else:
        print(f"❌ Error: {resp.text}")
        return []

def test_agents(workspace_id):
    print(f"\nTesting {BASE_URL}/api/agents?workspace_id={workspace_id}...")
    resp = requests.get(f"{BASE_URL}/api/agents", params={"workspace_id": workspace_id})
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Found {len(data)} agents")
        for agent in data[:3]:
             print(f"   - {agent['name']} ({agent['id']})")
        return data
    else:
        print(f"❌ Error: {resp.text}")
        return []

def test_chat(agent_id, workspace_id):
    print(f"\nTesting {BASE_URL}/api/chat/invoke...")
    payload = {
        "message": "Hello! Please reply with 'System Online'.",
        "agent_id": agent_id,
        "workspace_id": workspace_id
    }
    print(f"   Sending: {json.dumps(payload)}")
    
    start_time = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/api/chat/invoke", json=payload, timeout=60)
        elapsed = time.time() - start_time
        
        if resp.status_code == 200:
            data = resp.json()
            print(f"✅ Success ({elapsed:.2f}s)")
            print(f"   Response: {data['response']}")
        else:
            print(f"❌ Error ({resp.status_code}): {resp.text}")
    except Exception as e:
         print(f"❌ Chat failed: {e}")


if __name__ == "__main__":
    print("=== AgentOS Backend Connectivity Test ===\n")
    
    if not test_health():
        sys.exit(1)
    
    workspaces = test_workspaces()
    if workspaces:
        # Use first workspace
        ws_id = workspaces[0]["id"]
        
        agents = test_agents(ws_id)
        if agents:
            # Use first agent
            agent_id = agents[0]["id"]
            test_chat(agent_id, ws_id)
        else:
            print("\n⚠️ No agents found in default workspace. Skipping chat test.")
    else:
        print("\n⚠️ No workspaces found. Skipping deep tests.")
