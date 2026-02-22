import unittest
import os
import sys
import shutil
import json
from unittest.mock import MagicMock

# Ensure src is importable
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.core.file_manager import FileManager
from src.core.workspace import WorkspaceManager
from src.core.agent_registry import AgentRegistry
from src.core.base_agent import BaseAgent
from src.core.meta_agent import MetaAgent
from src.graph.agent_graph import create_compiled_graph
from langchain_core.messages import HumanMessage, AIMessage

class TestSystemIntegration(unittest.TestCase):
    """End-to-End System Integration Test"""
    
    TEST_DATA_ROOT = os.path.join(PROJECT_ROOT, "data_integration_test")
    TEST_CONFIG_DIR = os.path.join(PROJECT_ROOT, "config_integration_test")
    
    def setUp(self):
        # Clean env
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        os.makedirs(self.TEST_DATA_ROOT)
        
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)
        os.makedirs(self.TEST_CONFIG_DIR)
        
        # Init Core Components
        self.fm = FileManager(self.TEST_DATA_ROOT)
        self.wm = WorkspaceManager(self.fm)
        self.ar = AgentRegistry(os.path.join(self.TEST_CONFIG_DIR, "registry.json"))
        self.meta = MetaAgent(self.fm, self.ar)

    def tearDown(self):
        if os.path.exists(self.TEST_DATA_ROOT):
            shutil.rmtree(self.TEST_DATA_ROOT)
        if os.path.exists(self.TEST_CONFIG_DIR):
            shutil.rmtree(self.TEST_CONFIG_DIR)

    def test_full_workflow(self):
        """
        Scenario:
        1. User creates a Workspace "Project Alpha"
        2. User creates an Agent "Dev Bot"
        3. Agent writes a file (File Tool) -> Change Request
        4. User approves change
        5. File is verified on disk
        """
        
        # 1. Create Workspace
        ws_id = self.wm.create_workspace("Project Alpha")
        self.assertTrue(os.path.exists(os.path.join(self.TEST_DATA_ROOT, ws_id)))
        
        # 2. Create Agent
        agent_id = "agent_dev_bot"
        self.meta.create_agent(
            workspace_id=ws_id,
            agent_id=agent_id,
            name="Dev Bot",
            role_desc="Developer",
            tools=["write_file", "read_file"],
            model_tier="tier1"
        )
        
        # Verify Agent Config
        agent = self.ar.get_agent(agent_id)
        self.assertIsNotNone(agent)
        self.assertEqual(agent["name"], "Dev Bot")
        
        # 3. Simulate Agent Execution (Mocking LLM to call tool)
        # We invoke the graph with a mocked LLM response that calls 'write_file'
        
        # Mock State
        state = {
            "messages": [HumanMessage(content="Write a hello world file")],
            "current_agent": agent_id,
            "current_workspace": ws_id,
            "agent_config": agent,
            "pending_changes": [],
            "approval_status": None,
            "context": "",
            "needs_approval": False
        }
        
        # To strictly test graph logic without real LLM, we can unit test the graph nodes
        # But here we want integration.
        # Ideally we'd use a real LLM but that requires API keys.
        # So we will manually execute the agent node logic or use a mocked LLM object
        # injected into the graph? 
        # LangGraph nodes use `_get_llm`. We can patch `_get_llm` to return a mock.
        
        with unittest.mock.patch("src.graph.nodes._get_llm") as mock_get_llm:
            mock_llm = MagicMock()
            mock_get_llm.return_value = mock_llm
            
            # 1. Agent processes input -> decides to call tool
            msg_with_tool_call = AIMessage(
                content="",
                tool_calls=[{
                    "name": "write_file",
                    "args": {"path": "active/hello.txt", "content": "Hello World"},
                    "id": "call_123"
                }]
            )
            mock_llm.bind_tools.return_value.invoke.return_value = msg_with_tool_call
            
            # Invoke Graph
            graph = create_compiled_graph()
            
            # Step 1: Agent Node
            # We can run the graph, but `_get_tools` also needs to be mocked or real.
            # Real tools should work if we setup paths correctly.
            # `src.tools.file_tools` relies on `init_file_tools(fm)`. 
            # We MUST init file tools globally for this process.
            from src.tools.file_tools import init_file_tools
            init_file_tools(self.fm)
            
            # Run graph until end or interrupt? 
            # LangGraph run logic:
            # 1. router (pass) -> agent
            # 2. agent (mocked llm) -> returns msg with tool_call
            # 3. conditional -> tools
            # 4. tools (execution) -> execute write_file -> returns ChangeRequest JSON
            # 5. conditional -> approval?
            
            res = graph.invoke(state)
            
            # 4. output should contain pending_changes
            pending = res.get("pending_changes", [])
            self.assertEqual(len(pending), 1)
            cr = pending[0]
            # Normalize path for Windows compatibility test
            self.assertEqual(cr["file_path"].replace("\\", "/"), f"{ws_id}/{agent_id}/active/hello.txt") 
            self.assertEqual(cr["status"], "pending")
            
            # 5. Simulate User Approval
            from src.core.file_manager import ChangeRequest as CRParams
            
            cr_obj = CRParams(
                file_path=cr["file_path"],
                original_content=cr["original_content"],
                new_content=cr["new_content"],
                status="approved"
            )
            self.fm.apply_change(cr_obj)
            
            # 6. Verify file on disk
            full_path = os.path.join(self.TEST_DATA_ROOT, ws_id, agent_id, "active", "hello.txt")
            self.assertTrue(os.path.exists(full_path))
            with open(full_path, "r") as f:
                self.assertEqual(f.read(), "Hello World")

if __name__ == "__main__":
    unittest.main()
