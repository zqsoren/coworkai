import json
import asyncio
from typing import List, Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from src.core.model_agent import ModelAgent

# Phase 1: Plan Initialization Protocol
SUPERVISOR_INIT_PROTOCOL = """
# TASK: PLAN INITIALIZATION
Analyze the user request. Break it down into a clear Goal, Deliverables, and Execution Process.

OUTPUT FORMAT (JSON ONLY):
{{
    "goal": "The overall objective of this discussion",
    "deliverables": "The concrete outputs expected (e.g., Code, PRD, Diagram)",
    "process": ["Step 1: Agent X does...", "Step 2: Agent Y does..."],
    "explanation": "Brief rationale for this plan"
}}
"""

# Phase 2: Execution Protocol
SUPERVISOR_EXECUTION_PROTOCOL = """
# TASK: EXECUTION
Current Plan Status:
- Goal: {goal} (READ ONLY)
- Deliverables: {deliverables} (READ ONLY)
- Process: {process}
- Current Step Index: {current_step_index}

Select the next agent to execute the current step. You may update the process steps if needed, but DO NOT modify the Goal.

OUTPUT FORMAT (JSON ONLY):
{{
    "next_agent": "<agent_name>",
    "instruction": "<specific task for the agent>",
    "update_process": ["Remaining Step 1", "Remaining Step 2"] (Optional, use only if process needs change),
    "status": "CONTINUE" | "FINISH"
}}
"""

class GroupChat:
    def __init__(self, supervisor_agent: ModelAgent, max_turns: int = 20, initial_state: Dict[str, Any] = None):
        self.supervisor = supervisor_agent
        self.members: Dict[str, ModelAgent] = {}
        self.history: List[Dict[str, Any]] = []
        self.max_turns = max_turns
        
        # [NEW] Structured State (Persisted)
        default_state = {
            "plan_initialized": False,
            "goal": "",
            "deliverables": "",
            "process": [],
            "current_step_index": 0
        }
        self.chat_state = initial_state if initial_state else default_state
        # SSE event callback (injected externally by the streaming route)
        self._on_event = None

    async def _fire(self, event: dict):
        """Forward event to SSE callback if set."""
        if self._on_event:
            try:
                await self._on_event(event)
            except Exception:
                pass

    def add_agent(self, agent: ModelAgent):
        """Add a worker agent to the group."""
        self.members[agent.name] = agent

    def _build_supervisor_prompt(self, protocol_template: str, **kwargs) -> str:
        """
        Assemble the Composable Prompt:
        User_Prompt + Roster + Protocol
        """
        # 1. User Defined Prompt (Personality)
        user_prompt = self.supervisor.system_prompt
        
        # 2. Roster
        roster = []
        for name, agent in self.members.items():
            roster.append(f"- Name: {name}, Role: {agent.description}")
        roster_str = "\n".join(roster)
        
        # 3. Protocol (formatted with context)
        protocol = protocol_template.format(agent_roster=roster_str, **kwargs)
        
        final_prompt = f"{user_prompt}\n\n# Team Roster\n{roster_str}\n\n{protocol}"
        return final_prompt

    async def run(self, initial_prompt: str):
        """Start the chat loop."""
        print(f"\n[GroupChat] Starting with prompt: {initial_prompt}")
        self.history.append({"role": "user", "content": initial_prompt})
        
        turn = 0
        while turn < self.max_turns:
            should_continue = await self.step()
            if not should_continue:
                break
            turn += 1
        
        if turn >= self.max_turns:
            print("[GroupChat] Max turns reached. Forcing termination.")

    async def step(self) -> bool:
        """
        Execute one cycle. Branches based on phase.
        """
        # Phase 1: Initialization
        if not self.chat_state["plan_initialized"]:
            return await self._phase1_initialize_plan()
        
        # Phase 2: Execution
        return await self._phase2_execute_step()

    async def _phase1_initialize_plan(self) -> bool:
        """Generate the initial plan."""
        print("\n[GroupChat] Phase 1: Initializing Plan...")
        
        system_prompt = self._build_supervisor_prompt(SUPERVISOR_INIT_PROTOCOL)
        
        
        user_request = "Start discussion"
        if self.history and len(self.history) > 0:
            user_request = self.history[-1].get('content', "Start discussion")

        # Use full history as context
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Current User Request: {user_request}")
        ]
        
    def _extract_json(self, content: str) -> dict:
        """Robustly extract JSON from potentially messy LLM output."""
        import regex
        
        # 1. Try stripping markdown code blocks first
        clean_content = content.replace("```json", "").replace("```", "").strip()
        try:
            return json.loads(clean_content)
        except json.JSONDecodeError:
            pass
            
        # 2. Regex to find the first valid JSON object
        # This regex looks for the outermost curly braces, handling nested braces recursively if using the right engine,
        # but for standard re, we can try a greedy match constrained by valid JSON structure or just simple brace counting.
        # Simple brace counting is more robust for "Extra data" issues.
        
        try:
            start = content.find('{')
            if start == -1: raise ValueError("No JSON found")
            
            # Smart stack-based brace matching that ignores braces inside strings
            balance = 0
            end = -1
            in_string = False
            escaped = False
            
            for i in range(start, len(content)):
                char = content[i]
                
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == '\\':
                        escaped = True
                    elif char == '"':
                        in_string = False
                else:
                    if char == '"':
                        in_string = True
                    elif char == '{':
                        balance += 1
                    elif char == '}':
                        balance -= 1
                        if balance == 0:
                            end = i
                            break
            
            if end != -1:
                json_str = content[start : end + 1]
                return json.loads(json_str)
        except Exception as e:
            print(f"JSON Extraction Error: {e}")
            pass
        
        # 3. Fallback: Try a dirty fix for common trailing text issues (if brace counting failed)
        try:
            # Sometimes LLMs mess up braces. Try finding last } via rfind as backup
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                 return json.loads(content[start : end + 1])
        except:
             pass

        # 4. Last resort: raise original error to be caught by caller
        return json.loads(clean_content)

    async def _phase1_initialize_plan(self) -> bool:
        """Generate the initial plan."""
        print("\n[GroupChat] Phase 1: Initializing Plan...")
        
        system_prompt = self._build_supervisor_prompt(SUPERVISOR_INIT_PROTOCOL)
        
        # Use full history as context
        last_msg_content = "Start Planning"
        if self.history:
             last_msg_content = str(self.history[-1].get("content", ""))
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Current User Request: {last_msg_content}")
        ]
        
        try:
            print("[GroupChat] Invoking LLM for Plan...")
            response = await self.supervisor.llm.ainvoke(messages)
            print(f"[GroupChat] Raw Plan Response: {response.content}")
            
            plan = self._extract_json(response.content)
            
            # Normalize Keys
            plan = {k.lower(): v for k, v in plan.items()}
            
            # Persist State
            self.chat_state["goal"] = plan.get("goal", "")
            self.chat_state["deliverables"] = plan.get("deliverables", "")
            self.chat_state["process"] = plan.get("process", [])
            self.chat_state["plan_initialized"] = True
            self.chat_state["current_step_index"] = 0 # [FIX] Initialize step index
            
            # Additional Safety: If goal empty, flag error
            if not self.chat_state["goal"]:
                 print("[GroupChat] Warning: Generated plan has empty goal.")
            
            plan_md = f"""# 📅 项目计划
**目标**: {self.chat_state['goal']}
**产物**: {self.chat_state['deliverables']}

**执行流程**:
""" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(self.chat_state['process'])])
            
            # Save to history with special flag for UI if needed
            self.history.append({
                "role": "assistant",
                "name": "Supervisor",
                "content": plan_md,
                "is_plan": True, # Marker for backend/frontend
                "plan_data": plan # Raw data for Right Panel
            })

            # Fire plan event immediately for SSE
            await self._fire({"type": "plan", "data": plan})
            
            print(f"[Supervisor] Plan Generated: {self.chat_state['goal']}")
            return True
 # Continue to execution phase immediately? 
                        # User said "Default Accept", so we return True. 
                        # Frontend loop will see CONTINUE? No, frontend sees response.
                        # Wait, step() returns boolean for internal loop.
                        # If called via API /chat/turn, this function runs ONCE.
                        # So we return True here, the API saves the message, returns to Frontend.
                        # Frontend sees message, Status defaults to... ?
                        # We need to ensure API returns status CONTINUE so frontend calls again immediately.
            
        except Exception as e:
            print(f"[GroupChat] Plan Init Failed: {e}")
            self.history.append({
                "role": "system", 
                "content": f"Critical Error: Failed to generate plan. {e}"
            })
            return False

    async def _phase2_execute_step(self) -> bool:
        """Execute output based on current plan."""
        print(f"\n[GroupChat] Phase 2: Executing Step {self.chat_state['current_step_index']}...")
        
        # Build Context
        context_args = {
            "goal": self.chat_state["goal"],
            "deliverables": self.chat_state["deliverables"],
            "process": json.dumps(self.chat_state["process"], ensure_ascii=False),
            "current_step_index": self.chat_state["current_step_index"] + 1
        }
        
        system_prompt = self._build_supervisor_prompt(SUPERVISOR_EXECUTION_PROTOCOL, **context_args)
        
        # Build Conversation History String
        conversation_str = ""
        for msg in self.history:
            role = msg.get("role")
            content = msg.get("content")
            name = msg.get("name", role)
            conversation_str += f"\n[{name}]: {content}"
            
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Current Conversation History:\n{conversation_str}\n\nMake your decision based on the Plan.")
        ]
        
        # ... (Rest of logic similar to original _query_supervisor + execution) ...
        # Need to implement the decision parsing and agent calling here.
        
        response = await self.supervisor.llm.ainvoke(messages)
        try:
            decision = self._extract_json(response.content)
        except:
             print(f"[Supervisor] JSON Parse Error in Phase 2")
             return False
             
        # ... logic continues ...
        return await self._execute_decision(decision)


    async def _execute_decision(self, decision: dict) -> bool:
        if decision.get("status") == "FINISH":
            print(f"\n[Supervisor] FINISH triggered.")
            # [NEW] Add a closing message to inform the user
            closing_msg = decision.get("instruction")
            if not closing_msg or closing_msg == "None":
                closing_msg = "本次讨论目标已达成。是否还有其他指示？"
            
            self.history.append({
                "role": "assistant",
                "name": "Supervisor",
                "content": closing_msg
            })
            return False

        # Handle Process Update
        if "update_process" in decision and decision["update_process"]:
             print(f"[Supervisor] Process Updated: {decision['update_process']}")
             self.chat_state["process"] = decision["update_process"]
             # Reset index if needed? Or just append? 
             # Simplest assumption: update_process REPLACES the remaining steps.
             # Or it replaces the WHOLE process list?
             # Let's assume replace whole for simplicity or just the remaining.
             # Protocol said: "update_process": ["Remaining Step 1", ...]
             # So we overwrite.
             self.chat_state["process"] = decision["update_process"]
             self.chat_state["current_step_index"] = 0 # Restart index on new process? 
                                                       # Or supervisor manages it.
                                                       # Let's trust supervisor list.

        next_agent_name = decision.get("next_agent")
        instruction = decision.get("instruction")
        
        # [NEW] Append Supervisor Instruction to History
        supervisor_msg_content = f"@{next_agent_name}，{instruction}"
        self.history.append({
            "role": "assistant",
            "name": "Supervisor",
            "content": supervisor_msg_content
        })
        
        print(f"\n[Supervisor] -> Assigned to [{next_agent_name}]: {instruction}")

        # Validate Agent
        agent = self.members.get(next_agent_name)
        if not agent:
            print(f"[System] Error: Supervisor selected unknown agent '{next_agent_name}'.")
            return True

        # Execution
        response = await agent.execute_with_context(
            instruction, self.history, on_event=self._on_event
        )
        print(f"[{next_agent_name}] -> {response[:100]}...")

        # Update History
        self.history.append({
            "role": "assistant",
            "name": next_agent_name,
            "content": response
        })
        
        # Increment Step Index
        self.chat_state["current_step_index"] += 1
        
        return True

    async def _query_supervisor_legacy(self) -> Dict[str, Any]:
         # Valid for backward compatibility if needed, but we replaced step() logic.
         pass

    def get_chat_log(self) -> List[Dict[str, Any]]:
        return self.history

    async def get_final_result(self) -> str:
        # Simple heuristic: last message
        if not self.history:
            return ""
        return self.history[-1]["content"]

    # ============================================================
    # Workflow Mode (New)
    # ============================================================
    
    async def generate_workflow(self, user_request: str) -> dict:
        """
        Generate a complete workflow plan using the Supervisor.
        This is called ONCE at the beginning.
        
        Args:
            user_request: The user's initial request
        
        Returns:
            Workflow plan as dict (JSON structure)
        """
        from src.core.workflow_prompts import build_workflow_supervisor_prompt
        
        # Build roster for workflow planning
        roster = []
        for name, agent in self.members.items():
            roster.append(f"- Name: {name}, Role: {agent.description}")
        roster_str = "\n".join(roster)
        
        # Get workflow supervisor prompt
        system_prompt = build_workflow_supervisor_prompt(roster_str)
        
        print(f"\n[GroupChat] Generating workflow plan for: {user_request[:100]}...")
        
        # Query supervisor for workflow plan
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_request)
        ]
        
        raw_response = await self.supervisor.llm.ainvoke(messages)
        content = raw_response.content
        
        # Clean JSON markdown if present
        content = content.replace("```json", "").replace("```", "").strip()
        
        try:
            workflow = json.loads(content)
            print(f"[GroupChat] ✓ Workflow generated: {workflow.get('plan_name', 'Untitled')}")
            print(f"[GroupChat] Steps: {len(workflow.get('workflow', []))}")
            return workflow
        except json.JSONDecodeError as e:
            print(f"[GroupChat] ✗ Failed to parse workflow JSON: {e}")
            print(f"[GroupChat] Raw output: {content}")
            # Return fallback workflow
            return {
                "plan_name": "Fallback Plan",
                "description": "Supervisor failed to generate valid workflow",
                "workflow": []
            }
    
    async def execute_workflow(self, workflow: dict, initial_history: list = None, on_step_complete = None) -> list:
        """
        Execute a pre-generated workflow plan.
        
        Args:
            workflow: Workflow plan (from generate_workflow)
            initial_history: Initial conversation history (optional)
            on_step_complete: Optional async callback(step_result_dict)
        
        Returns:
            Complete conversation history after execution
        """
        from src.core.workflow_executor import WorkflowExecutor
        
        # Initialize history
        if initial_history:
            self.history = initial_history.copy()
        
        # Create executor and run
        executor = WorkflowExecutor(workflow, self.members, self.history)
        self.history = await executor.execute(on_step_complete=on_step_complete)
        
        return self.history

