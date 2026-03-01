"""Diagnostic logging for agent self-healing."""

import logging
from datetime import datetime
from pathlib import Path

class DiagnosticLogManager:
    """
    Writes structured diagnostic information to isolated log files
    that the agent can later read to debug its own failures.
    """
    
    def __init__(self, workspace: Path):
        self.log_dir = workspace / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
    def _write_log(self, filename: str, severity: str, message: str) -> None:
        """Helper to append a timestamped message to a specific log."""
        filepath = self.log_dir / filename
        timestamp = datetime.now().isoformat()
        entry = f"[{timestamp}] [{severity}] {message}\n"
        
        try:
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            # We don't want the logger crashing the main system
            logging.error(f"Failed to write to diagnostic log {filename}: {e}")

    def log_error(self, message: str, severity: str = "ERROR") -> None:
        """Log stack traces, tool crashes, and unexpected exceptions."""
        self._write_log("errors.log", severity, message)
        
    def log_network(self, message: str, severity: str = "WARN") -> None:
        """Log API timeouts, proxy issues, and connection drops."""
        self._write_log("network.log", severity, message)
        
    def log_analysis(self, message: str, severity: str = "INFO") -> None:
        """Log internal architectural decisions and semantic chunking results."""
        self._write_log("analysis.log", severity, message)
