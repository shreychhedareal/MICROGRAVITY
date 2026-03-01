from typing import List, Dict, Any
import json
from litellm import completion

class GoalManager:
    """
    Manages high-level goals and breaks them down into actionable UI steps using an LLM.
    """
    def __init__(self, model_name: str = "gemini/gemini-3-flash-preview"):
        self.model_name = model_name
        self.current_goal = None
        self.subtasks = []
        self.completed_tasks = []

    def set_goal(self, goal_description: str):
        """
        Receives a high-level goal from the user or swarm.
        """
        self.current_goal = goal_description
        print(f"[GoalManager] Received new goal: {goal_description}")
        self._breakdown_goal(goal_description)

    def _breakdown_goal(self, goal: str):
        """
        Uses LLM to break down a goal into subtasks.
        """
        print(f"[GoalManager] Prompting LLM to break down goal...")
        
        prompt = f"""
        You are a UI automation agent. Break down the following high-level user goal into a sequence of atomic GUI actions.
        Available actions are:
        - {{"action": "click", "target": "element_description", "app_window": "optional app name if background window", "description": "why"}}
        - {{"action": "type", "text": "text to type", "app_window": "optional app name if background window", "description": "why"}}
        - {{"action": "hotkey", "keys": ["alt", "tab"], "description": "why"}}
        - {{"action": "press", "key": "enter", "description": "why"}}
        - {{"action": "wait", "duration": seconds_as_float, "description": "why"}}
        
        If the user mentions an application by name (e.g. "VS Code", "Chrome", "Notepad"), add the `"app_window"` field to the action so the agent captures that specific buffer instead of the whole desktop.
        
        Goal: {goal}
        
        Output ONLY a valid JSON array of action objects. Do not include markdown formatting or other text.
        """
        
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse response
            content = response.choices[0].message.content.strip()
            # Remove potential markdown block wrappers
            if content.startswith("```json"):
                content = content[7:-3]
            elif content.startswith("```"):
                content = content[3:-3]
                
            self.subtasks = json.loads(content)
            print(f"[GoalManager] Successfully planned {len(self.subtasks)} subtasks.")
            
        except Exception as e:
            print(f"[GoalManager ERROR] Failed to plan subtasks: {e}")
            # Fallback to mock for resilient execution
            self.subtasks = [
                {"action": "wait", "duration": 1.0, "description": "Wait (Fallback task)"}
            ]

    def get_next_action(self) -> Dict[str, Any]:
        """
        Retrieves the next action to perform.
        """
        if not self.subtasks:
             return None
        action = self.subtasks.pop(0)
        self.completed_tasks.append(action)
        return action
        
    def goal_completed(self) -> bool:
        """Check if all subtasks are finished."""
        return len(self.subtasks) == 0 and self.current_goal is not None

    def replan_recovery(self, failed_action: Dict[str, Any], state_after: str, vision_analyzer: Any):
        """
        Generates and inserts recovery steps at the front of the queue to fix a failed action.
        """
        print(f"[GoalManager] Action failed: {failed_action['action']} on '{failed_action.get('target', 'unknown')}'. Initiating recovery replan...")
        recovery_steps = self._plan_recovery_steps(failed_action, state_after, vision_analyzer)
        
        if recovery_steps:
            # Insert recovery steps AT THE FRONT of the queue to fix the immediate issue
            self.subtasks = recovery_steps + self.subtasks
            print(f"[GoalManager] Successfully injected {len(recovery_steps)} recovery tasks into the queue.")
        else:
            print("[GoalManager] Could not generate recovery steps. Continuing blindly...")
            
    def _plan_recovery_steps(self, failed_action: Dict[str, Any], state_after: str, vision_analyzer: Any) -> List[Dict[str, Any]]:
        """Uses VLM to look at the screen and generate the fix."""
        prompt = f"""
        You are an autonomous UI Agent tracking your own execution. 
        You just attempted the following action: {failed_action}
        However, your Semantic Feedback Loop detected that the action FAILED to achieve its intention. 
        
        Look at the attached current screen state image. Why did it fail? 
        Perhaps it clicked the taskbar icon and opened a thumbnail preview instead of the app window?
        
        Generate a short JSON array of immediate recovery *actions* to fix the situation.
        Available actions are:
        - {{"action": "click", "target": "element_description", "description": "why"}}
        - {{"action": "press", "key": "enter", "description": "why"}}
        
        For example, if a Chrome thumbnail preview is open, output:
        [{{ "action": "click", "target": "Chrome taskbar thumbnail preview", "description": "To actually focus the window from the preview." }}]
        
        Output ONLY a valid JSON array. Do not include markdown or other text.
        """
        try:
            from PIL import Image
            img = Image.open(state_after)
            
            response = vision_analyzer.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[prompt, img],
                config={"temperature": 0.2, "response_mime_type": "application/json"}
            )
            
            content = response.text.strip()
            recovery_tasks = json.loads(content)
            return recovery_tasks
            
        except Exception as e:
            print(f"[GoalManager ERROR] Failed to plan recovery steps: {e}")
            return []
