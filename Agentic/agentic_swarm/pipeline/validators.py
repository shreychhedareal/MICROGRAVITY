import json
import json_repair
import logging
from typing import Any, Type, Dict
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

class PipelineValidator:
    """
    Validates LLM raw text output against a strictly defined Pydantic schema.
    Returns the parsed object or raises a structured error that the agent can use for feedback.
    """
    
    @staticmethod
    def validate_json_output(raw_text: str, schema_class: Type[BaseModel]) -> BaseModel:
        """
        Extracts JSON from the text (handles markdown code blocks if necessary)
        and validates it against the Pydantic schema.
        """
        # Clean markdown if present
        cleaned_text = raw_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
            
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
            
        cleaned_text = cleaned_text.strip()
        
        try:
            # Use json_repair to handle truncated outputs (like unterminated strings)
            parsed_json = json_repair.loads(cleaned_text)
            if not isinstance(parsed_json, dict):
                raise ValueError("Parsed JSON is not a dictionary.")
        except Exception as e:
            logger.error(f"Failed to decode JSON from LLM output: {e}")
            raise ValueError(f"JSONDecodeError: Ensure your output is perfectly formatted JSON. Error details: {e}\nRaw output received: {raw_text}")
            
        try:
            return schema_class(**parsed_json)
        except ValidationError as e:
            logger.error(f"Pydantic Validation failed: {e}")
            raise ValueError(f"SchemaValidationError: Your JSON did not match the required schema. Error details:\n{e.json()}\nJSON received: {parsed_json}")

# Example Schema for a System Command
class SystemCommandSchema(BaseModel):
    command: str
    explanation: str
    is_safe: bool
