import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.model_agent import ModelAgent
from src.core.workflow_executor import WorkflowExecutor
from src.core.agent_registry import AgentRegistry
from src.core.file_manager import FileManager

async def test_workflow():
    print("Initializing test...")
    
    # Mock Objects
    class MockLLM:
        async def ainvoke(self, messages):
            print(f"MockLLM received {len(messages)} messages")
            content = messages[-1].content
            return type('obj', (object,), {'content': f"Mock response to: {content[:20]}...", 'tool_calls': []})

    class MockAgent(ModelAgent):
        def __init__(self, name):
            self.name = name
            self.description = "Mock Agent"
            self.config = {}
            self.system_prompt = "You are a mock agent."
            self.llm = MockLLM()
            self.file_manager = None
            self.workspace_id = "test_ws"
            self.agent_id = name
            
        async def execute_with_context(self, instruction, history):
            print(f"[{self.name}] Executing: {instruction[:50]}...")
            return f"Result from {self.name}"

    # Setup Agents
    agents = {
        "AgentA": MockAgent("AgentA"),
        "AgentB": MockAgent("AgentB")
    }

    # Mock Workflow
    workflow = {
        "plan_name": "Test Workflow",
        "description": "Testing workflow execution",
        "workflow": [
            {
                "step": 1,
                "step_name": "Step 1",
                "executor_agent": "AgentA",
                "executor_prompt": "Do task A for {user_input}",
                "reviewer_agent": "AgentB",
                "reviewer_prompt": "Review {step_result}",
                "max_revision_rounds": 1
            }
        ]
    }

    history = [{"role": "user", "content": "Test input"}]

    print("Starting executor...")
    executor = WorkflowExecutor(workflow, agents, history)
    result = await executor.execute()
    print("Execution finished!")
    print(result)

if __name__ == "__main__":
    asyncio.run(test_workflow())
