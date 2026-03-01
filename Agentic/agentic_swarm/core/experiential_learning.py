import logging
from typing import Dict, Any, List

from core.memory import MemoryAdapter

logger = logging.getLogger(__name__)

class ExperientialLearningModule:
    """
    Analyzes historical execution ledgers to identify successful 'Path Functions' 
    and package them into reusable 'Process IPs'.
    """
    def __init__(self, memory: MemoryAdapter):
        self.memory = memory

    def internalize_successful_sequence(self, sequence_name: str, target_objective: str) -> str:
        """
        Scans the ledger for a specific objective, extracts the exact path of agents called, 
        and registers it as a reusable Process IP.
        """
        ledger = self.memory.get_execution_history()
        
        # 1. Filter ledger for the target objective
        # In this MVP, we assume a linear extraction. 
        # Real system: uses graph heuristics to find the exact sub-DAG that solved the goal.
        path_function = []
        state_delta = "Achieved Goal: " + target_objective
        estimated_cost = 0.0
        
        for trace in ledger:
            if "error" not in str(trace.get("result", "")).lower():
                path_function.append({
                    "step_id": trace["id"],
                    "agent": trace["caller"],
                    "target": trace["target"],
                    "action": trace["input"]
                })
                # Simplistic cost estimate per node hop
                estimated_cost += 0.01 
                
        if not path_function:
            logger.warning(f"No successful path found for objective '{target_objective}'. Cannot internalize.")
            return None
            
        # 2. Package and Isolate into a Process IP
        ip_id = self.memory.internalize_process_ip(
            name=sequence_name,
            path_function=path_function,
            state_delta=state_delta,
            cost=estimated_cost
        )
        
        logger.info(f"✨ Experiential Learning Complete. Path Function isolated into IP [{ip_id}].")
        return ip_id

    def factor_constraints(self, target_ip_name: str, max_budget: float) -> bool:
        """
        Constraint Factoring/Deal Structuring: Decides if an IP is worth executing based on budget and success rate.
        """
        ips = self.memory.get_available_process_ips()
        target_ip = next((ip for ip in ips.values() if ip.name == target_ip_name), None)
        
        if not target_ip:
            logger.warning(f"Process IP '{target_ip_name}' not found.")
            return False
            
        # Tradeoff analysis
        if target_ip.cost_estimate > max_budget:
            logger.warning(f"Constraint Failed: IP '{target_ip.name}' costs {target_ip.cost_estimate}, exceeding budget {max_budget}.")
            return False
            
        logger.info(f"Constraint Passed: IP '{target_ip.name}' approved for execution.")
        return True
