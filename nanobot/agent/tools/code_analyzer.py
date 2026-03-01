"""Code analysis and annotation tools."""

import ast
import os
from pathlib import Path
from typing import Any

from nanobot.agent.tools.base import Tool


class OutlineCodeTool(Tool):
    """Tool to extract semantic outlines (classes, methods, docstrings) from code."""

    @property
    def name(self) -> str:
        return "outline_code"

    @property
    def description(self) -> str:
        return "Parses a Python file and returns its architectural outline (classes, methods, and their docstrings) without the full function bodies. Extremely useful for understanding large codebases quickly."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the Python file."
                }
            },
            "required": ["file_path"]
        }

    async def execute(self, file_path: str, **kwargs: Any) -> str:
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return f"Error: File '{file_path}' does not exist or is not a file."
            
        if path.suffix != ".py":
            return f"Error: Outline tool currently only supports Python (.py) files. Got {path.suffix}"
            
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(path))
            
            output = [f"--- Outline for {path.name} ---"]
            
            for node in tree.body:
                if isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node)
                    doc_preview = f"  \"\"\"{docstring.split(chr(10))[0]}...\"\"\"" if docstring else ""
                    output.append(f"class {node.name}:{doc_preview}")
                    
                    for sub_node in node.body:
                        if isinstance(sub_node, ast.FunctionDef) or isinstance(sub_node, ast.AsyncFunctionDef):
                            prefix = "async def" if isinstance(sub_node, ast.AsyncFunctionDef) else "def"
                            func_doc = ast.get_docstring(sub_node)
                            f_doc_preview = f"  # {func_doc.split(chr(10))[0]}" if func_doc else ""
                            output.append(f"    {prefix} {sub_node.name}(...):{f_doc_preview}")
                            
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                    docstring = ast.get_docstring(node)
                    doc_preview = f"  \"\"\"{docstring.split(chr(10))[0]}...\"\"\"" if docstring else ""
                    output.append(f"{prefix} {node.name}(...):{doc_preview}")
                    
            if len(output) == 1:
                output.append("(No classes or functions found)")
                
            return "\n".join(output)
            
        except SyntaxError as e:
            return f"Error parsing code (Syntax Error): {str(e)}"
        except Exception as e:
            return f"Error outlining file: {str(e)}"
            
class AnnotateCodeTool(Tool):
    """Tool to append architectural or standard comments to files."""

    @property
    def name(self) -> str:
        return "annotate_code"

    @property
    def description(self) -> str:
        return "Appends an architectural comment block to the top of a file. Use this to permanently store your semantic understandings of what a script does directly inside the file."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The absolute path to the file."
                },
                "annotation": {
                    "type": "string",
                    "description": "The comment/docstring block to append at the top."
                }
            },
            "required": ["file_path", "annotation"]
        }

    async def execute(self, file_path: str, annotation: str, **kwargs: Any) -> str:
        path = Path(file_path).resolve()
        if not path.exists() or not path.is_file():
            return f"Error: File '{file_path}' does not exist or is not a file."
            
        try:
            content = path.read_text(encoding="utf-8")
            
            # Formally format depending on language
            comment_block = ""
            if path.suffix == ".py":
                comment_block = f'"""\n[AI ANNOTATION]\n{annotation}\n"""\n\n'
            elif path.suffix in [".js", ".ts", ".css", ".java", ".c", ".cpp"]:
                comment_block = f"/*\n[AI ANNOTATION]\n{annotation}\n*/\n\n"
            elif path.suffix in [".html", ".xml", ".md"]: # md comments
                comment_block = f"<!--\n[AI ANNOTATION]\n{annotation}\n-->\n\n"
            else:
                comment_block = f"# [AI ANNOTATION]\n# {annotation.replace(chr(10), chr(10)+'# ')}\n\n"
                
            new_content = comment_block + content
            path.write_text(new_content, encoding="utf-8")
            
            return f"Successfully added structural annotation to the top of '{path.name}'."
            
        except Exception as e:
            return f"Error annotating code: {str(e)}"
