import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.core.file_manager import FileManager

class GroupChatManager:
    """
    Manages persistence of Group Chat configurations and messages.
    - Groups are stored in `_group_chats.json` within the workspace directory
    - Messages are stored in `_group_messages_{group_id}.json`
    """
    def __init__(self, file_manager: FileManager):
        self.fm = file_manager

    def _get_storage_path(self, workspace_id: str) -> str:
        ws_path = self.fm._resolve_and_validate(workspace_id)
        return os.path.join(ws_path, "_group_chats.json")

    def list_groups(self, workspace_id: str) -> List[Dict[str, Any]]:
        path = self._get_storage_path(workspace_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading groups for {workspace_id}: {e}")
            return []

    def get_group(self, workspace_id: str, group_id: str) -> Optional[Dict[str, Any]]:
        groups = self.list_groups(workspace_id)
        for g in groups:
            if g["id"] == group_id:
                return g
        return None

    def create_group(self, workspace_id: str, name: str, member_ids: List[str], supervisor_id: str) -> Dict[str, Any]:
        groups = self.list_groups(workspace_id)
        group_id = f"group_{name.lower().replace(' ', '_')}_{len(groups)+1}"

        new_group = {
            "id": group_id,
            "name": name,
            "members": member_ids,
            "supervisor_id": supervisor_id,
            "supervisor_prompt": "",  # Empty = use default template (legacy mode)
            "workflow_supervisor_prompt": "",  # Empty = use default template (workflow mode)
            "created_at": datetime.now().isoformat()
        }

        groups.append(new_group)
        self._save_groups(workspace_id, groups)
        return new_group

    def update_group(self, workspace_id: str, group_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update group fields (supervisor_id, supervisor_prompt, name, etc.)."""
        groups = self.list_groups(workspace_id)
        for g in groups:
            if g["id"] == group_id:
                for key, value in updates.items():
                    if key != "id":  # Never allow id change
                        g[key] = value
                self._save_groups(workspace_id, groups)
                return g
        return None

    def delete_group(self, workspace_id: str, group_id: str):
        groups = self.list_groups(workspace_id)
        groups = [g for g in groups if g["id"] != group_id]
        self._save_groups(workspace_id, groups)

    def _save_groups(self, workspace_id: str, groups: List[Dict[str, Any]]):
        path = self._get_storage_path(workspace_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(groups, f, indent=2, ensure_ascii=False)
    
    # ========== Message Management ==========
    
    def _get_messages_path(self, workspace_id: str, group_id: str) -> str:
        """Get path to messages file for a specific group."""
        ws_path = self.fm._resolve_and_validate(workspace_id)
        return os.path.join(ws_path, f"_group_messages_{group_id}.json")
    
    def get_messages(self, workspace_id: str, group_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Load message history for a group (最近 limit 条)."""
        path = self._get_messages_path(workspace_id, group_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                all_messages = json.load(f)
            # Return latest limit with transformation
            messages = all_messages[-limit:] if len(all_messages) > limit else all_messages
            
            # Transform for frontend compatibility (name, role)
            for msg in messages:
                # Map 'agent' role to 'assistant'
                if msg.get("role") == "agent":
                    msg["role"] = "assistant"
                
                # Map 'agent_name' to 'name'
                if "agent_name" in msg and "name" not in msg:
                    msg["name"] = msg["agent_name"]
            
            return messages
        except Exception as e:
            print(f"Error loading messages for {group_id}: {e}")
            return []
    
    def add_message(self, workspace_id: str, group_id: str, role: str, 
                    content: str, agent_id: Optional[str] = None, 
                    agent_name: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Add a message to group chat history.
        
        Args:
            role: 'user' or 'agent'
            agent_id: agent ID (if role='agent')
            agent_name: agent display name (if role='agent')
            **kwargs: Additional fields to store (e.g., is_plan, plan_data)
        """
        messages = self._load_all_messages(workspace_id, group_id)
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if role == "agent" or role == "assistant":
            message["agent_id"] = agent_id
            message["agent_name"] = agent_name
            message["name"] = agent_name # Add standard 'name' field
        
        # Ensure role is 'assistant' for storage consistency if 'agent' was passed
        if message["role"] == "agent":
            message["role"] = "assistant"
            
        # Merge extra fields
        message.update(kwargs)
            
        messages.append(message)
        self._save_messages(workspace_id, group_id, messages)
        return message
    
    def _load_all_messages(self, workspace_id: str, group_id: str) -> List[Dict[str, Any]]:
        """Load all messages (内部使用，无limit)."""
        path = self._get_messages_path(workspace_id, group_id)
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def _save_messages(self, workspace_id: str, group_id: str, messages: List[Dict[str, Any]]):
        """Save messages to file."""
        path = self._get_messages_path(workspace_id, group_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

    def clear_messages(self, workspace_id: str, group_id: str):
        """Clear all messages for a group."""
        path = self._get_messages_path(workspace_id, group_id)
        if os.path.exists(path):
            os.remove(path)
            print(f"[GroupManager] Cleared messages for {group_id}")
