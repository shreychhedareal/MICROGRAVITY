import logging
import time
from ui_agent_prototype.agent import UIAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("TestDriver")

class MockSwarmController:
    """Simulates the Nanobot multi-agent framework."""
    def __init__(self):
        self.message_bus = []
        
    def broadcast(self, sender, data):
        logger.info(f"SWARM RECEIVED from {sender}: {data['type']}")
        self.message_bus.append({"sender": sender, "data": data})

if __name__ == "__main__":
    logger.info("Initializing UI/UX Prototype Agent Test")
    
    # 1. Setup Mock Swarm
    swarm = MockSwarmController()
    
    # 2. Initialize the standalone agent
    test_agent = UIAgent(agent_id="UI_Agent_01", swarm_controller=swarm)
    
    # 3. Define a complex objective
    # This involves: Opening software (utility check), viewing screen (perception),
    # generating a sequence (planner), executing it physically (action controller),
    # and broadcasting results to swarm.
    objective = "Open unknown application X, determine its utility, log in, and click settings."
    
    print("\n--- STARTING AGENT DIRECTIVE ---")
    print("WARNING: Please do not move your mouse for the next few seconds.\n")
    time.sleep(2)
    
    # 4. Trigger the agent
    test_agent.receive_directive(objective, swarm_context={"known_apps": ["system Y"]})
    
    # 5. Check Output Contexts
    print("\n--- FINAL SWARM STATE ---")
    print(f"Total events broadcasted: {len(swarm.message_bus)}")
    for msg in swarm.message_bus:
        print(f" - {msg['data']['type']}")
        
    logger.info("Test Run Complete.")
