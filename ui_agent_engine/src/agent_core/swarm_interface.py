import queue
from typing import Callable, Any

class SwarmInterface:
    """
    A communication stub to integrate this UI Agent into a larger swarm architecture.
    """
    def __init__(self):
        self.task_queue = queue.Queue()
        self.result_callbacks = []
        
    def submit_task(self, task_description: str, priority: int = 1):
        """
        Called by other agents in the swarm to request UI interactions.
        """
        print(f"[SwarmInterface] Task received: {task_description}")
        self.task_queue.put((priority, task_description))
        
    def get_next_task(self) -> str:
        """
        Called by the UIAgent to get the next task from the swarm.
        """
        if not self.task_queue.empty():
             # In real implementation, handle tuple unpacking and PriorityQueue
             return self.task_queue.get()[1]
        return None
        
    def register_callback(self, callback: Callable[[str, Any], None]):
        """
        Registers a callback so the UI Agent can report task completion or derived info back to the swarm.
        """
        self.result_callbacks.append(callback)
        
    def report_result(self, task_id: str, result_data: Any):
        """
        Broadcasts the result of a UI action back to the swarm.
        """
        print(f"[SwarmInterface] Broadcasting result for {task_id}")
        for callback in self.result_callbacks:
             callback(task_id, result_data)
