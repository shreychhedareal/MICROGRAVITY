from pydantic import BaseModel, Field
import logging
from typing import Any, List, Dict, Optional

from agents.base import BaseSeekerAgent

logger = logging.getLogger(__name__)

# --- New Memory-Aware Schemas ---

class CodeEntity(BaseModel):
    name: str = Field(description="Name of the entity (variable, function, class, module).")
    entity_type: str = Field(description="Type: 'variable', 'function', 'class', 'module', 'iterable', 'condition'.")
    purpose: str = Field(description="Intended functionality and role in the broader architecture.")

class CodeContextMemory(BaseModel):
    paradigms_used: List[str] = Field(description="Architectural paradigms (e.g. 'Event-Driven', 'Functional', 'MVC').")
    related_files: List[str] = Field(description="Absolute or relative paths to files referencing or referenced by this code.")
    dependencies: List[str] = Field(description="External packages or internal modules required.")
    entities: List[CodeEntity] = Field(description="Detailed breakdown of the structures inside this code block.")

class CodingSchema(BaseModel):
    file_path: str = Field(description="The path where the code should be written or updated.")
    code_content: str = Field(description="The actual source code to be implemented (RAW text, no markdown blocks).")
    language: str = Field(description="The programming language of the code (e.g. 'python', 'javascript').")
    
    # New: The agent must explicitly map out its mental model of what it just wrote
    code_memory: CodeContextMemory = Field(description="Structured context memory of the code components, entities, and paradigms.")

class CodingSeeker(BaseSeekerAgent):
    """
    Coding Seeker: A specialized agent for implementing features that inherently 
    remembers the logic, variables, and architectural implications of the code it writes.
    """
    def __init__(self, model_name: str = "gpt-4o-mini"):
        super().__init__(
            name="CodingSeeker",
            description="Writes code and generates a structured memory graph of all variables, conditionals, and paradigms used.",
            model_name=model_name
        )

    @property
    def system_prompt(self) -> str:
        return (
            "You are the Coding Seeker, an expert programmer agent with deep structural memory.\n"
            "Your job is to write production-ready code AND meticulously document its mental model.\n"
            "You must map out every significant file path, module, component, variable, iterable, "
            "conditional, and architectural paradigm used into the `code_memory` schema.\n"
            "CRITICAL:\n"
            "1. Output valid JSON matching the exact schema.\n"
            "2. Do not write markdown blocks inside the code_content field; output RAW code text.\n"
            "3. The code_memory.entities list must be exhaustive, describing the intended functionality of each."
        )

    @property
    def output_schema(self) -> type[BaseModel]:
        return CodingSchema

    def run_tools(self, parsed_objective: BaseModel) -> Any:
        code_data: CodingSchema = parsed_objective
        logger.info(f"Generating {code_data.language} code for {code_data.file_path}")
        logger.info(f"Memory Graph Extracted: Paradigms: {code_data.code_memory.paradigms_used}, Entities tracked: {len(code_data.code_memory.entities)}")
        
        # In a real system:
        # 1. Write `code_data.code_content` to `code_data.file_path`
        # 2. Push `code_data.code_memory` to the Long-Term Semantic Graph Database (e.g. Neo4j or Meilisearch)
        
        return {
            "status": "success",
            "file_path": code_data.file_path,
            "bytes_written": len(code_data.code_content),
            "memory_graph_extracted": code_data.code_memory.model_dump()
        }
