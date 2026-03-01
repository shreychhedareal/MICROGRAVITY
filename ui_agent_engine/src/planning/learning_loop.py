from typing import Dict, Any

class LearningLoop:
    """
    Evaluates the success of actions against goals and adjusts future planning.
    This module ties together perception and action prediction to learn from mistakes.
    """
    def __init__(self, vision_analyzer, action_predictor):
        self.vision = vision_analyzer
        self.predictor = action_predictor
        self.action_history = []

    def evaluate_action_success(self, action: Dict[str, Any], state_before: str, state_after: str) -> bool:
        """
        Determines if an action achieved its intended result by comparing visual states.
        """
        print(f"[LearningLoop] Evaluating success of action: {action['action']}")
        
        # Call VisionAnalyzer (VLM) to check if the state changed meaningfully
        # e.g., "Did the start menu open?"
        success = self.vision.visual_diff(state_before, state_after, action_context=action)
        
        if success:
             print("[LearningLoop] Action deemed SUCCESSFUL.")
        else:
             print("[LearningLoop] Action deemed FAILED.")
             
        # Record outcome to improve future prediction
        self.predictor.record_outcome(action, success)
        
        # Store in history for potential self-reflection later
        self.action_history.append({
            "action": action,
            "success": success,
            "state_before": state_before,
            "state_after": state_after
        })
        
        return success
