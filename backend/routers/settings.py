from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from src.core.llm_manager import LLMManager, LLMProvider
from backend.user_deps import get_user_llm_manager

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Models
class ProviderModel(BaseModel):
    id: str
    type: str
    name: str
    models: List[str]
    base_url: Optional[str] = None
    api_key_env: str = "EMPTY"

class TestConnectionRequest(BaseModel):
    provider_id: str

@router.get("/providers", response_model=List[Dict])
def list_providers(request: Request):
    """List all configured providers."""
    lm = get_user_llm_manager(request)
    lm.load_providers()
    providers = []
    for p in lm.providers.values():
        if hasattr(p, '__dict__'):
            providers.append(p.__dict__)
        else:
            providers.append(p)
    return providers

@router.get("/models", response_model=List[Dict])
def list_models(request: Request):
    """List all available models flat list."""
    lm = get_user_llm_manager(request)
    lm.load_providers()
    return lm.list_all_models()

@router.post("/provider")
def add_or_update_provider(provider: ProviderModel, request: Request):
    """Add or update a provider."""
    try:
        lm = get_user_llm_manager(request)
        new_p = LLMProvider(
            id=provider.id,
            type=provider.type,
            name=provider.name,
            models=provider.models,
            base_url=provider.base_url,
            api_key_env=provider.api_key_env
        )
        lm.add_provider(new_p)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/provider/{provider_id}")
def delete_provider(provider_id: str, request: Request):
    """Delete a provider. Cannot delete builtin providers."""
    lm = get_user_llm_manager(request)
    lm.load_providers()
    provider = lm.get_provider(provider_id)
    if provider and getattr(provider, 'is_builtin', False):
        raise HTTPException(status_code=403, detail="内置供应商不可删除")
    try:
        lm.remove_provider(provider_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test-connection")
def test_connection(req: TestConnectionRequest, request: Request):
    """Test connection to a provider."""
    lm = get_user_llm_manager(request)
    success, msg = lm.test_connection(req.provider_id)
    if not success:
         raise HTTPException(status_code=400, detail=msg)
    return {"status": "success", "message": msg}
