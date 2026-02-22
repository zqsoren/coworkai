import unittest
import os
import shutil
import json
import sys

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.base_agent import BaseAgent
from src.core.agent_registry import AgentRegistry
from src.core.file_manager import FileManager

class TestAgentSystem(unittest.TestCase):
    TEST_DATA_ROOT = os.path.join(PROJECT_ROOT, "data_test")
    TEST_CONFIG_DIR = os.path.join(PROJECT_ROOT, "config_test")
    TEST_REGISTRY = os.path.join(TEST_CONFIG_DIR, "registry.json")

    def setUp(self):
        # Setup directories
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        os.makedirs(self.TEST_DATA_ROOT)
        
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)
        os.makedirs(self.TEST_CONFIG_DIR)

        # Init FileManager and Registry
        self.fm = FileManager(self.TEST_DATA_ROOT)
        self.ar = AgentRegistry(self.TEST_REGISTRY)

    def tearDown(self):
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)

    def test_registry_management(self):
        """Test registering and retrieving agents"""
        # Register an agent
        config = {
            "name": "Test Agent",
            "workspace": "ws_test",
            "model_tier": "tier1",
            "tools": ["read_file"],
            "skills": ["deep_research"]
        }
        self.ar.register_agent("agent_test", config)
        
        # Retrieve
        fetched = self.ar.get_agent("agent_test")
        self.assertEqual(fetched["name"], "Test Agent")
        self.assertEqual(fetched["model_tier"], "tier1")
        
        # List
        agents = self.ar.list_agents(workspace="ws_test")
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["id"], "agent_test")

    def test_base_agent_instantiation(self):
        """Test BaseAgent initialization and context loading"""
        # Setup agent files
        ws_id = "ws_test"
        agent_id = "agent_x"
        self.fm.ensure_agent_dirs(ws_id, agent_id)
        
        # Write local config
        config_path = f"{ws_id}/{agent_id}/config.json"
        local_config = {
            "name": "Local Agent",
            "system_prompt": "Local Prompt",
            "model_tier": "tier2"
        }
        self.fm.write_file(config_path, json.dumps(local_config))
        
        # Write a context file
        self.fm.write_file(f"{ws_id}/{agent_id}/active/memory.md", "Last session data", force=True)
        
        # Instantiate
        agent = BaseAgent(agent_id, ws_id, self.fm)
        
        # Check properties loaded from local config
        self.assertEqual(agent.name, "Local Agent")
        self.assertEqual(agent.system_prompt, "Local Prompt")
        
        # Check context loading
        context = agent.load_context()
        self.assertIn("memory.md", context)
        self.assertIn("Last session data", context)
        
        # Check System Prompt construction
        full_prompt = agent.get_full_system_prompt()
        self.assertIn("Local Prompt", full_prompt)
        self.assertIn("Last session data", full_prompt)
        self.assertIn("重要规则", full_prompt)

    def test_agent_file_request(self):
        """Test agent file operations"""
        ws_id = "ws_test"
        agent_id = "agent_y"
        self.fm.ensure_agent_dirs(ws_id, agent_id)
        agent = BaseAgent(agent_id, ws_id, self.fm)
        
        # Request change to active file
        cr = agent.request_file_change("active/plan.md", "New Plan")
        self.assertIsNotNone(cr)
        self.assertEqual(cr.new_content, "New Plan")
        
        # Save output
        out_path = agent.save_output("result.txt", "Outcome")
        self.assertTrue(out_path.endswith("result.txt"))
        # Verify content safely using direct OS read (since FM denies read access to output/)
        full_out_path = os.path.join(self.TEST_DATA_ROOT, ws_id, agent_id, "output", "result.txt")
        self.assertTrue(os.path.exists(full_out_path))
        with open(full_out_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content, "Outcome")

if __name__ == "__main__":
    unittest.main()
