import time
import logging
from ui_agent_prototype.action_controller import ActionController
from ui_agent_prototype.perception import PerceptionEngine
from ui_agent_prototype.planner import UIPlanner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("UIAgent")

class UIAgent:
    """
    Standalone UI/UX Prototype Agent capable of planning, acting, and 
    communicating continuously.
    """
    
    def __init__(self, agent_id="UI_Worker_01", swarm_controller=None):
        self.agent_id = agent_id
        # Mock communication channel with larger "swarm"
        self.swarm = swarm_controller 
        
        # Sub-modules
        self.controller = ActionController()
        self.perception = PerceptionEngine()
        self.planner = UIPlanner(debug_mode=True)
        
        self.is_running = False
        self.current_objective = None

    def receive_directive(self, objective, swarm_context=None):
        """Receive a goal from an external orchestrator/user."""
        self.current_objective = objective
        logger.info(f"Agent {self.agent_id} received objective: {objective}")
        
        # Determine utility of objective based on unknown inputs
        utility = self.planner.analyze_utility(objective, software_context=swarm_context)
        logger.info(f"Initial utility assessment: {utility['confidence']*100}% confidence.")
        
        if utility['confidence'] > 0.5:
             self.start_evaluation_loop(swarm_context)
        else:
             logger.error("Objective utility too low or software misunderstood. Aborting.")

    def share_context_with_swarm(self, event_data):
        """Drive information to other agents."""
        logger.info(f"Broadcasting event to Swarm: {event_data.get('type')}")
        if self.swarm:
             self.swarm.broadcast(self.agent_id, event_data)

    def start_evaluation_loop(self, swarm_context=None):
        """
        Main execution loop.
        Continuously perceive -> analyze -> plan -> act -> evaluate
        """
        self.is_running = True
        logger.info(f"Entering continuous evaluation loop for: {self.current_objective}")
        
        max_steps = 10 # Safety break
        step = 0
        
        while self.is_running and step < max_steps:
             logger.info(f"--- Loop Iteration {step + 1} ---")
             
             # 1. Perceive: Capture state
             screen_path = self.perception.capture_screenshot()
             current_state = self.perception.analyze_with_vision(screen_path, self.current_objective)
             
             self.share_context_with_swarm({"type": "state_update", "content": current_state})
             
             # 2. Plan: Decide what to do based on state and objective
             logger.info("Thinking what to do next based on screen state...")
             plan = self.planner.generate_plan(self.current_objective, current_state, swarm_context)
             
             if not plan:
                  logger.warning("No plan generated. Awaiting state change.")
                  time.sleep(2)
                  continue

             # 3. Execute: Perform physical actions
             logger.info("Executing generated plan.")
             for action_step in plan:
                  self.execute_action(action_step)
                  time.sleep(1) # Simulated delay between sub-steps
                  
             # 4. Evaluate: Check if objective met (Mocking true after 1 loop)
             logger.info("Evaluating outcome of step.")
             # Assume success for the dummy test
             if step >= 0:
                 logger.info("Objective deemed complete.")
                 self.share_context_with_swarm({"type": "objective_completed", "objective": self.current_objective})
                 self.is_running = False
                 break

             step += 1
             time.sleep(2) # Pause before next cycle
             
        logger.info("Exited evaluation loop.")

    def execute_action(self, action_data):
        """Map logical action strings to ActionController methods."""
        act = action_data.get("action")
        logger.debug(f">> Executing: {action_data}")
        
        try:
             if act == "move_mouse":
                 self.controller.move_mouse(action_data['x'], action_data['y'])
             elif act == "single_click":
                 self.controller.single_click(button=action_data.get('button', 'left'))
             elif act == "double_click":
                 self.controller.double_click(button=action_data.get('button', 'left'))
             elif act == "scroll":
                 self.controller.scroll(action_data.get('amount', -100))
             elif act == "type_text":
                 self.controller.type_text(action_data['text'])
             elif act == "drag":
                 self.controller.drag(action_data['start_x'], action_data['start_y'],
                                      action_data['end_x'], action_data['end_y'])
             else:
                 logger.warning(f"Unknown action type: {act}")
        except Exception as e:
             logger.error(f"Failed to execute action {act}: {e}")
             self.share_context_with_swarm({"type": "error", "error": str(e)})

if __name__ == "__main__":
     # Mock run 
     agent = UIAgent(agent_id="Testbot_V1")
     # "Use unknown software" goal
     agent.receive_directive("Login to dashboard and navigate to settings")
