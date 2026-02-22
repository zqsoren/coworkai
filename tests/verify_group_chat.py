import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def verify_group_chat():
    print("Starting Group Chat Verification...")

    # 1. Create a Workspace
    ws_name = f"GroupTest_{str(uuid.uuid4())[:8]}"
    print(f"Creating workspace: {ws_name}")
    resp = requests.post(f"{BASE_URL}/api/workspace/create", json={"name": ws_name})
    if resp.status_code != 200:
        print(f"Failed to create workspace: {resp.text}")
        return
    ws_id = resp.json()["workspace_id"]
    print(f"Workspace created: {ws_id}")

    # 2. Create Agents
    agent_ids = []
    for i in range(2):
        agent_name = f"Agent_{i}_{str(uuid.uuid4())[:4]}"
        print(f"Creating agent: {agent_name}")
        payload = {
            "name": agent_name,
            "system_prompt": f"You are agent {i}. Always respond with 'I am agent {i}'.",
            "provider_id": "gemini_default", 
            "model_name": "gemini-2.0-flash",
            "workspace_id": ws_id 
        }
        # agent create takes workspace_id in body (CreateAgentRequest)
        resp = requests.post(f"{BASE_URL}/api/agent/create", json=payload)
        if resp.status_code != 200:
             # Fallback if gemini_default invalid, try to list providers? 
             # For now, let's assume 'ce' exists as seen in view_file earlier or just rely on backend default handling.
             print(f"Failed to create agent: {resp.text}")
        
        # Determine agent ID (response format might vary, let's check)
        # CreateAgentResponse has agent_id
        if resp.status_code == 200:
            agent_ids.append(resp.json()["agent_id"])
    
    if len(agent_ids) < 2:
        print("Not enough agents created. Aborting.")
        return

    print(f"Agents created: {agent_ids}")

    # 3. Create Group
    group_name = "Test Group"
    print(f"Creating group: {group_name}")
    payload = {
        "workspace_id": ws_id,
        "name": group_name,
        "member_ids": agent_ids
    }
    resp = requests.post(f"{BASE_URL}/api/group/create", json=payload)
    if resp.status_code != 200:
        print(f"Failed to create group: {resp.text}")
        return
    group_id = resp.json()["group_id"]
    print(f"Group created: {group_id}")

    # 4. List Groups
    print("Listing groups...")
    resp = requests.get(f"{BASE_URL}/api/group/list", params={"workspace_id": ws_id})
    groups = resp.json()["groups"]
    print(f"Groups found: {len(groups)}")
    found = False
    for g in groups:
        if g["id"] == group_id:
            found = True
            break
    
    if not found:
        print("Created group not found in list!")
        return
    else:
        print("Group verified in list.")

    # 5. Send Chat Message
    print("Sending chat message to group...")
    chat_payload = {
        "workspace_id": ws_id,
        "group_id": group_id,
        "message": "Hello everyone!",
        "history": [] 
    }
    # Note: Backend expects 'message' and 'history' in body? 
    # Let's check router: ChatRequest(workspace_id, group_id, message, history)
    resp = requests.post(f"{BASE_URL}/api/group/chat", json=chat_payload)
    if resp.status_code != 200:
        print(f"Chat failed: {resp.text}")
    else:
        print("Chat response received:")
        print(json.dumps(resp.json(), indent=2))

    print("Verification Complete.")

if __name__ == "__main__":
    try:
        verify_group_chat()
    except Exception as e:
        print(f"An error occurred: {e}")
