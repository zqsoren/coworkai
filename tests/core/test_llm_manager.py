import unittest
import os
import sys
import json
import shutil
from unittest.mock import MagicMock, patch

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.llm_manager import LLMManager, LLMProvider

class TestLLMManager(unittest.TestCase):
    
    TEST_CONFIG_DIR = os.path.join(PROJECT_ROOT, "config_test")
    TEST_CONFIG_FILE = os.path.join(TEST_CONFIG_DIR, "llm_providers.json")

    def setUp(self):
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)
        os.makedirs(self.TEST_CONFIG_DIR)
        
        # Patch config path
        self.original_path = LLMManager.CONFIG_PATH
        LLMManager.CONFIG_PATH = self.TEST_CONFIG_FILE

        # Create dummy config
        dummy_data = {
            "providers": [
                {
                    "id": "test_provider",
                    "type": "openai_compatible",
                    "name": "Test Provider",
                    "base_url": "http://localhost:1234/v1",
                    "api_key_env": "TEST_KEY",
                    "models": ["model-a", "model-b"]
                }
            ]
        }
        with open(self.TEST_CONFIG_FILE, "w") as f:
            json.dump(dummy_data, f)

    def tearDown(self):
        LLMManager.CONFIG_PATH = self.original_path
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)

    def test_load_providers(self):
        mgr = LLMManager()
        self.assertIn("test_provider", mgr.providers)
        p = mgr.get_provider("test_provider")
        self.assertEqual(p.name, "Test Provider")
        self.assertEqual(p.models, ["model-a", "model-b"])

    def test_add_provider(self):
        mgr = LLMManager()
        new_p = LLMProvider(
            id="new_p", type="gemini", name="New Gemini", models=["gemini-pro"]
        )
        mgr.add_provider(new_p)
        
        # Verify in memory
        self.assertIn("new_p", mgr.providers)
        
        # Verify file
        with open(self.TEST_CONFIG_FILE, "r") as f:
            data = json.load(f)
            ids = [p["id"] for p in data["providers"]]
            self.assertIn("new_p", ids)

    def test_get_model_openai_compatible(self):
        mgr = LLMManager()
        
        # Mocking secrets or env
        with patch.dict(os.environ, {"TEST_KEY": "sk-test"}):
            # Patch st.secrets to fail so it falls back to env
            with patch("streamlit.secrets", side_effect=FileNotFoundError):
                # We need to mock ChatOpenAI to avoid actual init
                with patch("src.core.llm_manager.ChatOpenAI") as MockChat:
                    mgr.get_model("test_provider", "model-a")
                    MockChat.assert_called_with(
                        model="model-a",
                        api_key="sk-test",
                        base_url="http://localhost:1234/v1",
                        temperature=0.7
                    )

    def test_list_all_models(self):
        mgr = LLMManager()
        models = mgr.list_all_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["display"], "Test Provider - model-a")

if __name__ == "__main__":
    unittest.main()
