import logging
import uuid
import datetime
from enum import Enum
from typing import Dict, Any, Callable, Coroutine
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"

class DurableTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    objective: str
    target_agent: str
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    state_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Serialized scratchpad state for pause/resume.")
    created_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    cron_schedule: str = Field(default="", description="Optional standard cron string if repeating.")

class DurableEventBus:
    """
    Manages pausable, interruptible, and continuous tasks across the Swarm.
    In a true production environment, this wraps around Celery or Temporal.io.
    """
    def __init__(self, memory_adapter: Any):
        self.memory = memory_adapter
        self.active_tasks: Dict[str, DurableTask] = {}
        
    def enqueue_task(self, objective: str, target_agent: str, cron_schedule: str = "") -> str:
        """Schedules a new task in the queue."""
        task = DurableTask(objective=objective, target_agent=target_agent, cron_schedule=cron_schedule)
        self.active_tasks[task.task_id] = task
        # Serialize to persistent memory adapter
        self.memory.save_state(f"task:{task.task_id}", task.model_dump())
        logger.info(f"⏳ Task Enqueued: [{task.task_id}] -> {target_agent}")
        return task.task_id

    def pause_task(self, task_id: str, current_state: Dict[str, Any]) -> bool:
        """Interrupts an executing task, serializing its immediate state."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.status = TaskStatus.PAUSED
            task.state_snapshot = current_state
            self.memory.save_state(f"task:{task.task_id}", task.model_dump())
            logger.warning(f"⏸️ Task Paused: [{task_id}]. State serialized to Memory.")
            return True
        return False

    def resume_task(self, task_id: str) -> Dict[str, Any]:
        """Loads a paused task from memory, returning the snapshot so the agent can hydrate it."""
        task_data = self.memory.get_state(f"task:{task_id}")
        if not task_data:
            logger.error(f"Cannot resume task {task_id}. Not found in Memory.")
            return {}
            
        task = DurableTask(**task_data)
        if task.status != TaskStatus.PAUSED:
            logger.warning(f"Task {task_id} is not Paused (Current: {task.status}).")
            return {}
            
        task.status = TaskStatus.RUNNING
        self.active_tasks[task_id] = task
        logger.info(f"▶️ Task Resumed: [{task_id}]. State hydrated.")
        return task.state_snapshot
        
    def complete_task(self, task_id: str):
        """Marks task as complete, or resets it to pending if it is a cron job."""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            if task.cron_schedule:
                # If it's a cron job, it resets to wait for the next trigger
                task.status = TaskStatus.PENDING
                task.state_snapshot = {} # Clear run state
                logger.info(f"🔄 Cron Task Completed: [{task_id}]. Resetting for next schedule.")
            else:
                task.status = TaskStatus.COMPLETED
                logger.info(f"✅ One-Off Task Completed: [{task_id}].")
            self.memory.save_state(f"task:{task.task_id}", task.model_dump())
