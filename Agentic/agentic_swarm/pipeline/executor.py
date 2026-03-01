import os
import logging
from typing import Dict, Any, Type
from pydantic import BaseModel
import openai

# Use litellm or configure openai to use a specific provider
from pipeline.validators import PipelineValidator
from pipeline.analytical_scripts import AnalyticalScripts

logger = logging.getLogger(__name__)

class LLMExecutor:
    """
    Handles communication with the Language Model.
    """
    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.0):
        self.model_name = model_name
        self.temperature = temperature
        
        # In a real app, ensure API keys are set in environment
        # openai.api_key = os.getenv("OPENAI_API_KEY") 

    def generate_response(self, system_prompt: str, user_prompt: str, response_format: dict = None) -> str:
        """
        Calls the LLM with the provided prompts.
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            kwargs = {
                "model": self.model_name,
                "messages": messages,
                "temperature": self.temperature,
            }

            if response_format:
                kwargs["response_format"] = response_format
                
            response = openai.chat.completions.create(**kwargs)
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM API Error: {e}")
            raise Exception(f"Failed to communicate with LLM: {str(e)}")

class PipelineExecutor:
    """
    Coordinates the execution and validation loop for a Seeker Agent.
    """
    def __init__(self, llm_executor: LLMExecutor):
        self.llm = llm_executor
        
    def execute_with_validation(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        schema_class: Type[BaseModel],
        max_retries: int = 3
    ) -> BaseModel:
        """
        Runs the LLM and validates output against schema.
        If validation fails, it enters Feedback Processing Mode and retries.
        """
        current_user_prompt = user_prompt
        
        for attempt in range(max_retries):
            logger.info(f"Execution Attempt {attempt + 1}/{max_retries}")
            
            try:
                # 1. Prompt Execution
                raw_response = self.llm.generate_response(
                    system_prompt=system_prompt,
                    user_prompt=current_user_prompt,
                    response_format={"type": "json_object"}
                )
                
                logger.debug(f"Raw Output: {raw_response}")
                
                # 2. Analytical Script Enforcement (Regex/Word Detection)
                # Ensure the raw text survives basic mechanical constraints BEFORE json parsing
                is_valid, analytic_msg = AnalyticalScripts.run_regex_enforcement(raw_response)
                if not is_valid:
                    raise ValueError(f"AnalyticalScriptFailure: {analytic_msg}")
                
                # 3. Schema Validation
                validated_data = PipelineValidator.validate_json_output(raw_response, schema_class)
                
                # If we parse successfully, return it
                return validated_data
                
            except ValueError as ve:
                logger.warning(f"Validation failed on attempt {attempt + 1}: {ve}")
                
                # Enter Feedback Processing Mode: Append error to prompt and retry
                error_feedback = f"\n\n[SYSTEM FEEDBACK: Your previous output failed validation. Please fix the following error and try again:\n{str(ve)}]"
                current_user_prompt += error_feedback
                
                if attempt == max_retries - 1:
                    logger.error("Max retries exceeded. Triggering Human-In-The-Loop fallback.")
                    # In a real event-driven system, you'd emit to the EventBus here.
                    raise Exception(f"HITL_REQUIRED: Failed to generate valid output after {max_retries} attempts. Last Error: {ve}")

        raise Exception("Unexpected pipeline failure.")
