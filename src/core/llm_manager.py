"""
LLM Manager - 统一管理大模型提供商与实例
负责加载配置、实例化 LangChain Model、测试连通性。
"""

import os
import json
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

@dataclass
class LLMProvider:
    id: str
    type: str  # gemini, openai, openai_compatible, anthropic
    name: str
    models: List[str]
    base_url: Optional[str] = None
    api_key_env: str = "EMPTY"  # 对应 secrets.secrets["llm"][key] 的 key 名
    is_builtin: bool = False  # 系统内置供应商，用户不可删除

class LLMManager:
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "llm_providers.json")

    def __init__(self, config_path: str = None):
        if config_path:
            self.CONFIG_PATH = config_path
        self.providers: Dict[str, LLMProvider] = {}
        self.load_providers()

    def load_providers(self):
        """从 JSON 加载 Provider 配置"""
        if not os.path.exists(self.CONFIG_PATH):
            self.providers = {}
            return

        try:
            with open(self.CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                for p_data in data.get("providers", []):
                    try:
                        provider = LLMProvider(
                            id=p_data["id"],
                            type=p_data["type"],
                            name=p_data["name"],
                            models=p_data.get("models", []),
                            base_url=p_data.get("base_url"),
                            api_key_env=p_data.get("api_key_env", "EMPTY"),
                            is_builtin=p_data.get("is_builtin", False),
                        )
                        self.providers[provider.id] = provider
                    except Exception as e:
                        print(f"Error parsing provider {p_data.get('id')}: {e}")
        except Exception as e:
            print(f"Error loading providers: {e}")

    def save_providers(self):
        """保存 Provider 配置到 JSON"""
        # Convert LLMProvider objects to dicts
        providers_data = []
        for p in self.providers.values():
            if isinstance(p, LLMProvider):
                providers_data.append(p.__dict__)
            else:
                providers_data.append(p)
                
        data = {"providers": providers_data}
        try:
            with open(self.CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving providers: {e}")

    def get_provider(self, provider_id: str) -> Optional[LLMProvider]:
        return self.providers.get(provider_id)

    def add_provider(self, provider: LLMProvider):
        self.providers[provider.id] = provider
        self.save_providers()

    def remove_provider(self, provider_id: str):
        if provider_id in self.providers:
            del self.providers[provider_id]
            self.save_providers()

    def _get_api_key(self, api_key_env: str) -> str:
        """从 st.secrets 或环境变量获取 API Key"""
        if not api_key_env:
            return ""

        # 1. 如果看起来像直接的 Key (sk-...)，直接返回
        if api_key_env.startswith("sk-") or len(api_key_env) > 40: 
            return api_key_env

        # 2. 尝试从 secrets 获取 (仅在 streamlit 环境下)
        try:
            import streamlit as st
            # Check if running in streamlit
            if hasattr(st, 'secrets') and st.secrets:
                llm_secrets = st.secrets.get("llm", {})
                key = llm_secrets.get(api_key_env) or llm_secrets.get(api_key_env.lower())
                if key:
                    return key
        except:
            pass

        # 3. 尝试从 os.environ 获取
        return os.environ.get(api_key_env, str(api_key_env))

    def get_model(self, provider_id: str, model_name: str, temperature: float = 0.7):
        """获取 LangChain Model 实例"""
        provider = self.get_provider(provider_id)
        if not provider:
            raise ValueError(f"Provider not found: {provider_id}")

        api_key = self._get_api_key(provider.api_key_env)
        
        if provider.type == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            if not api_key:
                raise ValueError(f"Missing API Key for {provider.name}")
            
            kwargs = {
                "model": model_name,
                "google_api_key": api_key,
                "temperature": temperature,
                "timeout": 320  # 允许最多生成 5 分钟的超长文本
            }
            
            # Support Custom URL (Relay) for Gemini
            if provider.base_url:
                # Assuming base_url is full endpoint root, e.g. https://relay.com/v1beta
                # ChatGoogleGenerativeAI uses client_options={'api_endpoint': ...}
                # And transport="rest" usually helps.
                kwargs["transport"] = "rest"
                kwargs["client_options"] = {"api_endpoint": provider.base_url}
                
            return ChatGoogleGenerativeAI(**kwargs)
        
        elif provider.type == "openai" or provider.type == "openai_compatible":
            from langchain_openai import ChatOpenAI
            if not api_key and provider.type == "openai":
                raise ValueError(f"Missing API Key for {provider.name}")
            
            kwargs = {
                "model": model_name,
                "api_key": api_key or "EMPTY",
                "base_url": provider.base_url,
                "temperature": temperature,
                "timeout": 320,
                "max_retries": 1
            }
            
            # OpenRouter requires HTTP-Referer and X-Title headers for free models
            if provider.base_url and "openrouter.ai" in provider.base_url:
                kwargs["default_headers"] = {
                    "HTTP-Referer": "https://coworkai.xin",
                    "X-Title": "BASE Coworker AI"
                }
            
            return ChatOpenAI(**kwargs)
            
        elif provider.type == "anthropic":
            from langchain_anthropic import ChatAnthropic
            if not api_key:
                raise ValueError(f"Missing API Key for {provider.name}")
            return ChatAnthropic(
                model=model_name,
                api_key=api_key,
                temperature=temperature,
                timeout=120,  # 强制 120 秒超时
                max_retries=1
            )
            
        else:
            raise ValueError(f"Unsupported provider type: {provider.type}")

    def test_connection(self, provider_id: str) -> bool:
        """测试连接: 尝试调用模型生成简单回复"""
        provider = self.get_provider(provider_id)
        if not provider:
            return False, "Provider not found"
        
        try:
            # 使用列表第一个模型进行测试
            model_name = provider.models[0] if provider.models else "gpt-3.5-turbo" 
            llm = self.get_model(provider_id, model_name)
            response = llm.invoke("Hello, request test.")
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)

    def list_all_models(self) -> List[Dict[str, str]]:
        """返回所有可用模型列表供 UI 使用"""
        models = []
        for p in self.providers.values():
            for m in p.models:
                models.append({
                    "provider_id": p.id,
                    "provider_name": p.name,
                    "model_name": m,
                    "display": f"{p.name} - {m}"
                })
        return models
