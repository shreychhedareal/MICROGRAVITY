import json
import os
import cv2
import numpy as np
from typing import Dict, Any, List, Optional
from pathlib import Path

class UIMemoryAgent:
    """
    Manages the 'UI Atlas' - a persistent, multi-session map of UI elements, 
    layouts, and behaviors. This reduces VLM reliance by caching known states.
    """
    def __init__(self, workspace_path: Path):
        self.workspace = workspace_path
        self.long_term_dir = self.workspace / "agent_memory" / "long_term"
        self.short_term_dir = self.workspace / "agent_memory" / "short_term"
        self.atlas_path = self.long_term_dir / "ui_atlas.json"
        self.templates_dir = self.long_term_dir / "templates"
        
        # Ensure directories exist
        self.long_term_dir.mkdir(parents=True, exist_ok=True)
        self.short_term_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.atlas = self._load_atlas()

    def _load_atlas(self) -> Dict[str, Any]:
        if self.atlas_path.exists():
            try:
                with open(self.atlas_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[UIMemoryAgent] Error loading atlas: {e}")
        return {
            "contexts": {
                "Desktop": {"type": "FIXED", "elements": {}},
                "Taskbar": {"type": "FIXED", "elements": {}}
            },
            "global_elements": {},
            "layout_patterns": {},
            "version": "2.1"
        }

    def save_atlas(self):
        try:
            self.atlas_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.atlas_path, 'w', encoding='utf-8') as f:
                json.dump(self.atlas, f, indent=2)
        except Exception as e:
            print(f"[UIMemoryAgent] Error saving atlas: {e}")

    def classify_context(self, context: str, context_type: str = "DYNAMIC"):
        """Classifies a context as FIXED (Desktop/SysUI) or DYNAMIC (Apps)."""
        if context not in self.atlas["contexts"]:
            self.atlas["contexts"][context] = {"elements": {}, "last_seen": None}
        self.atlas["contexts"][context]["type"] = context_type
        self.save_atlas()

    def record_window_state(self, context: str, rect: List[int]):
        """Records the window boundaries [x, y, w, h] to check for stability later."""
        if context not in self.atlas["contexts"]:
            self.classify_context(context)
        self.atlas["contexts"][context]["last_rect"] = rect
        # We don't necessarily need to persist this if it's session-local, 
        # but for cross-step stability we track it in memory.
        
    def is_context_stable(self, context: str, current_rect: List[int]) -> bool:
        """Checks if the window hasn't moved since last recorded state."""
        if context in self.atlas["contexts"]:
            last_rect = self.atlas["contexts"][context].get("last_rect")
            return last_rect == current_rect
        return False

    def remember_element(self, context: str, label: str, data: Dict[str, Any], template: Optional[np.ndarray] = None):
        """
        Stores an element's coordinates, type, and optional CV template.
        """
        if context not in self.atlas["contexts"]:
            self.atlas["contexts"][context] = {"elements": {}, "last_seen": None, "type": "DYNAMIC"}
        
        element_key = label.lower()
        
        # Heuristic for invariants: search bars, taskbars, menus are usually invariant
        is_invariant = any(keyword in element_key for keyword in ["search", "taskbar", "start", "menu", "address"]) \
                      or data.get("is_invariant", False)

        self.atlas["contexts"][context]["elements"][element_key] = {
            "coords": data.get("coords"), # [x, y, w, h]
            "type": data.get("type", "unknown"),
            "behavior": data.get("behavior", "static"),
            "description": data.get("description", label),
            "is_invariant": is_invariant
        }
        self.atlas["contexts"][context]["last_seen"] = os.path.getmtime(self.atlas_path) if self.atlas_path.exists() else 0
        
        if template is not None:
            template_path = self.templates_dir / f"{context}_{element_key}.png"
            cv2.imwrite(str(template_path), template)
            self.atlas["contexts"][context]["elements"][element_key]["template_path"] = str(template_path)
            
        self.save_atlas()

    def recall_element(self, context: str, label: str) -> Optional[Dict[str, Any]]:
        """Retrieves element data from the atlas."""
        element_key = label.lower()
        # 1. Search in specific context
        if context in self.atlas["contexts"]:
            elements = self.atlas["contexts"][context]["elements"]
            if element_key in elements:
                return elements[element_key]
        
        # 2. Search in global elements (e.g., Taskbar, Start Button)
        if element_key in self.atlas["global_elements"]:
            return self.atlas["global_elements"][element_key]
            
        return None

    def get_context_map(self, context: str) -> Dict[str, Any]:
        """Returns the full element map for a given window/app context."""
        return self.atlas["contexts"].get(context, {"elements": {}})

    def update_layout(self, context: str, screen_size: tuple):
        """Records the typical layout/bounds of a context."""
        if context not in self.atlas["contexts"]:
            self.atlas["contexts"][context] = {"elements": {}}
        self.atlas["contexts"][context]["typical_screen_size"] = screen_size
        self.save_atlas()

    def sync_element(self, context: str, label: str, new_coords: List[int]):
        """
        Updates an element's position in the long-term Atlas. 
        Used when CV detects a shift (e.g., icon moved).
        """
        element_key = label.lower()
        if context in self.atlas["contexts"] and element_key in self.atlas["contexts"][context]["elements"]:
            old_coords = self.atlas["contexts"][context]["elements"][element_key]["coords"]
            if old_coords != new_coords:
                print(f"[UIMemoryAgent] Syncing '{label}' in {context}: {old_coords} -> {new_coords}")
                self.atlas["contexts"][context]["elements"][element_key]["coords"] = new_coords
                self.save_atlas()

    def get_short_term_path(self, filename: str) -> Path:
        """Returns a path within the short-term volatile memory dir."""
        return self.short_term_dir / filename
