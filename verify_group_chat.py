import asyncio
import os
import sys

# Add project root
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.file_manager import FileManager
from src.core.agent_registry import AgentRegistry
from src.core.meta_agent import MetaAgent
from src.core.model_agent import ModelAgent
from src.core.group_chat import GroupChat

async def main():
    print("Initializing GroupChat Verification...")
    
    # 1. Setup Environment
    data_root = os.path.join(PROJECT_ROOT, "data")
    registry_path = os.path.join(PROJECT_ROOT, "config", "agents_registry.json")
    
    fm = FileManager(data_root)
    registry = AgentRegistry(registry_path)
    meta = MetaAgent(fm, registry)
    
    # 2. Ensure Test Agents Exist (and are valid)
    # We need a Coder and a Reviewer
    target_provider = "ce"
    target_model = "gemini-2.0-flash-exp"
    
    ws_id = "default_workspace"
    
    # Simple check and create
    agents = registry.list_agents(workspace=ws_id)
    agent_ids = [a["id"] for a in agents]
    
    settings = {"provider_id": target_provider, "model_name": target_model}

    if "agent_coder" not in agent_ids:
        print("Creating agent_coder...")
        meta.create_agent(ws_id, "agent_coder", "Coder", "Expert Python Developer.", 
                          provider_id=target_provider, model_name=target_model)
    else:
        print("Updating agent_coder...")
        registry.update_agent("agent_coder", settings)
        
    if "agent_reviewer" not in agent_ids:
        print("Creating agent_reviewer...")
        meta.create_agent(ws_id, "agent_reviewer", "Reviewer", "QA Specialist.", 
                          provider_id=target_provider, model_name=target_model)
    else:
        print("Updating agent_reviewer...")
        registry.update_agent("agent_reviewer", settings)

    if "agent_supervisor" not in agent_ids:
         print("Creating agent_supervisor...")
         meta.create_agent(ws_id, "agent_supervisor", "Supervisor", "Project Manager.", 
                           provider_id=target_provider, model_name=target_model)
    else:
        print("Updating agent_supervisor...")
        registry.update_agent("agent_supervisor", settings)

    # 3. Instantiate ModelAgents
    coder = ModelAgent("agent_coder", ws_id, fm, registry)
    reviewer = ModelAgent("agent_reviewer", ws_id, fm, registry)
    supervisor = ModelAgent("agent_supervisor", ws_id, fm, registry)
    
    # 4. Init GroupChat
    chat = GroupChat(supervisor_agent=supervisor, max_turns=10)
    chat.add_agent(coder)
    chat.add_agent(reviewer)
    
    # 5. Run
    prompt = "Write a Python function to calculate the factorial of a number, then review it."
    await chat.run(prompt)
    
    # 6. Dump Log
    print("\n--- Interaction Log ---")
    for msg in chat.get_chat_log():
        role = msg.get("role")
        name = msg.get("name", "")
        content = msg.get("content", "")[:50] + "..."
        print(f"{role} ({name}): {content}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
