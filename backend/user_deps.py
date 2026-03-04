"""
User-scoped dependency injection.（Supabase 版）
Provides per-request managers based on the authenticated user's ID.
"""
import os
from fastapi import Request, HTTPException
from src.core.file_manager import FileManager
from src.core.agent_registry import AgentRegistry
from src.core.workspace import WorkspaceManager
from src.core.group_manager import GroupChatManager
from src.core.llm_manager import LLMManager

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(PROJECT_ROOT, "data")


def get_user_id(request: Request) -> str:
    """Extract user_id from request state (set by JWT middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="未登录")
    return user_id


def get_user_data_root(request: Request) -> str:
    """Get the data root for the current user."""
    user_id = get_user_id(request)
    return os.path.join(DATA_ROOT, user_id)


def get_user_file_manager(request: Request) -> FileManager:
    """Create a FileManager scoped to the current user's data directory."""
    user_root = get_user_data_root(request)
    return FileManager(user_root)


def get_user_agent_registry(request: Request) -> AgentRegistry:
    """Create an AgentRegistry scoped to the current user."""
    user_id = get_user_id(request)
    return AgentRegistry(user_id)


def get_user_workspace_manager(request: Request) -> WorkspaceManager:
    """Create a WorkspaceManager scoped to the current user."""
    fm = get_user_file_manager(request)
    user_id = get_user_id(request)
    return WorkspaceManager(fm, user_id)


def get_user_group_manager(request: Request) -> GroupChatManager:
    """Create a GroupChatManager scoped to the current user."""
    user_id = get_user_id(request)
    return GroupChatManager(user_id)


def get_user_llm_manager(request: Request) -> LLMManager:
    """Create an LLMManager scoped to the current user."""
    user_id = get_user_id(request)
    return LLMManager(user_id)
