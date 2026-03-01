import os
import glob
from pathlib import Path
from nanobot.agent.memory import MemoryStore

def scan_machine_env(workspace_path: str):
    """
    Simulated Machine Scanner.
    In a real extension, this would query Windows Registry or MacOS /Applications.
    For now, it crawls common developer paths to populate MACHINE_ENV.md.
    """
    workspace = Path(workspace_path)
    store = MemoryStore(workspace)
    
    apps_discovered = []
    # Just a mock check for some common dev tools to simulate mapping
    if os.path.exists("C:/Program Files/Google/Chrome/Application/chrome.exe"):
        apps_discovered.append("| Google Chrome | C:/Program Files/Google/Chrome/Application/chrome.exe | Web Browsing |")
    if os.path.exists("C:/Users/HP/AppData/Local/Programs/Microsoft VS Code/Code.exe"):
        apps_discovered.append("| VS Code | C:/Users/HP/AppData/Local/Programs/Microsoft VS Code/Code.exe | Code Editing |")
    
    # Update MACHINE_ENV
    if apps_discovered:
        content = store.read_text("MACHINE_ENV.md")
        if content:
            for app in apps_discovered:
                if app.split("|")[1].strip() not in content:
                    content = content.replace("| (Pending) | (Pending) | (Pending) |", app + "\n| (Pending) | (Pending) | (Pending) |")
            store.write_text("MACHINE_ENV.md", content)
        
    # Scan for Repos in common locations (just the workspace parent for this demo)
    repos_discovered = []
    parent_dir = workspace.parent
    for d in parent_dir.iterdir():
        if d.is_dir() and (d / ".git").exists():
            repos_discovered.append(f"| {d.name} | {d.absolute()} | Mixed | Discovered via auto-scan |")
            
    # Update REPO_CATALOG
    if repos_discovered:
        content = store.read_text("REPO_CATALOG.md")
        if content:
            for repo in repos_discovered:
                if repo.split("|")[1].strip() not in content:
                    content = content.replace("| (Pending) | (Pending) | (Pending) | (Pending) |", repo + "\n| (Pending) | (Pending) | (Pending) | (Pending) |")
            store.write_text("REPO_CATALOG.md", content)

if __name__ == "__main__":
    scan_machine_env("c:/Users/HP/nanobot/workspace")
    print("Machine and Repo scan complete. Memory updated.")
