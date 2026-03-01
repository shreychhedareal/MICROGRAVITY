import asyncio
import logging
import os
import tempfile
import sys

os.environ["GEMINI_API_KEY"] = "INSERT_API_KEY"

# Ensure nanobot is in Python path for local testing
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from nanobot.swarm.broker.lmdb_broker import LMDBBroker
from nanobot.swarm.state.duckdb_ledger import DuckDBLedger
from nanobot.swarm.agents.seeker import GenericSeekerAgent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def main():
    logger.info("Starting Agent Browser Validation...")
    
    # Setup Temporary Databases for Broker and Ledger
    temp_dir = tempfile.TemporaryDirectory()
    db_path = temp_dir.name
    
    lmdb_path = os.path.join(db_path, "lmdb")
    duckdb_path = os.path.join(db_path, "ledger.duckdb")
    
    broker = LMDBBroker(lmdb_path)
    ledger = DuckDBLedger(duckdb_path)
    
    # Initialize the seeker agent
    agent = GenericSeekerAgent("browser_tester", broker, ledger)
    
    objective = (
        "Use the browser tool to navigate to 'https://example.com', "
        "extract the main heading text (H1), and output a JSON object "
        "with 'heading' as the key. Then close the browser."
    )
    
    logger.info(f"Target Objective: {objective}")
    
    # Execute the agent operational loop directly
    result = await agent._run_operational_mode(objective)
    
    logger.info("Agent Execution Complete.")
    print("\n--- Final Agent Result ---")
    print(result)
    
    # Cleanup
    broker.close()
    ledger.close()
    temp_dir.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
