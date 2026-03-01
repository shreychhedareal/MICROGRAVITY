import sys
import logging
import time
from ui_agent_prototype.agent import UIAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("Driver")

class MockSwarmController:
    """Simulates the Nanobot multi-agent framework."""
    def __init__(self):
        self.message_bus = []
        
    def broadcast(self, sender, data):
        logger.info(f"SWARM RECEIVED from {sender}: {data['type']}")
        self.message_bus.append({"sender": sender, "data": data})

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: No objective provided.")
        print("Usage: python run_ui_agent.py \"<your objective here>\"")
        print("Example: python run_ui_agent.py \"Open chrome and click on the search bar\"")
        sys.exit(1)
        
    objective = sys.argv[1]
    
    logger.info(f"Initializing UI/UX Agent...")
    
    swarm = MockSwarmController()
    agent = UIAgent(agent_id="CLI_Agent", swarm_controller=swarm)
    
    print("\n" + "="*40)
    print(f"STARTING AGENT DIRECTIVE:")
    print(f"'{objective}'")
    print("="*40)
    print("\nWARNING: Please do not move your mouse. The agent may take control.\n")
    time.sleep(2)
    
    agent.receive_directive(objective)
    
    print("\n--- EXECUTION COMPLETE ---")
    print("Events broadcasted back to swarm:")
    for msg in swarm.message_bus:
        print(f" - [{msg['data']['type'].upper()} Event] Data: {msg['data']}")
