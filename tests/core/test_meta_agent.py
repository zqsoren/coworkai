import unittest
import os
import shutil
import json
import sys
from unittest.mock import MagicMock

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.meta_agent import MetaAgent
from src.core.file_manager import FileManager
from src.core.agent_registry import AgentRegistry

class TestMetaAgent(unittest.TestCase):
    TEST_DATA_ROOT = os.path.join(PROJECT_ROOT, "data_test_meta")
    TEST_CONFIG_DIR = os.path.join(PROJECT_ROOT, "config_test_meta")
    TEST_REGISTRY = os.path.join(TEST_CONFIG_DIR, "registry.json")

    def setUp(self):
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        os.makedirs(self.TEST_DATA_ROOT)
        
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)
        os.makedirs(self.TEST_CONFIG_DIR)

        self.fm = FileManager(self.TEST_DATA_ROOT)
        self.ar = AgentRegistry(self.TEST_REGISTRY)
        self.meta = MetaAgent(self.fm, self.ar)

    def tearDown(self):
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)

    def test_create_agent(self):
        result = self.meta.create_agent(
            workspace_id="ws_001",
            agent_id="coder",
            name="Coder Agent",
            role_desc="Write code",
            tools=["code_tools"],
            skills=["git"]
        )
        
        self.assertIn("创建成功", result)
        
        # Verify Directory
        self.assertTrue(os.path.exists(os.path.join(self.TEST_DATA_ROOT, "ws_001", "coder")))
        self.assertTrue(os.path.exists(os.path.join(self.TEST_DATA_ROOT, "ws_001", "coder", "config.json")))
        
        # Verify Registry
        agent = self.ar.get_agent("coder")
        self.assertIsNotNone(agent)
        self.assertEqual(agent["name"], "Coder Agent")
        self.assertIn("code_tools", agent["tools"])

if __name__ == "__main__":
    unittest.main()
