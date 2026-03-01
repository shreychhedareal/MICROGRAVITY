#!/usr/bin/env python3
"""
Semantic search backend for the Swarm Credential Manager.
Provides CRUD and substring matching over the JSON vault without polluting LLM context.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

VAULT_PATH = Path("workspace/memory/credential_manager.json")


def _load_vault() -> Dict[str, List[Dict[str, Any]]]:
    if not VAULT_PATH.exists():
        return {}
    try:
        return json.loads(VAULT_PATH.read_text(encoding="utf-8"))
    except:
        return {}


def _save_vault(data: dict):
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VAULT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def search(query: str) -> str:
    """Fuzzy substring match for a platform name."""
    data = _load_vault()
    query_lower = query.lower()
    
    matches = []
    
    # Simple substring search across keys
    for platform, creds in data.items():
        if query_lower in platform:
            valid_creds = [c for c in creds if c.get("status") == "valid"]
            if valid_creds:
                matches.append({
                    "platform": platform,
                    "username": valid_creds[0].get("username"),
                    "password": valid_creds[0].get("password")
                })
            else:
                invalid_creds = [c for c in creds if c.get("status") == "invalid"]
                if invalid_creds:
                    reason = invalid_creds[-1].get("invalid_reason", "Unknown failure")
                    matches.append({
                        "platform": platform,
                        "status": "INVALID_NO_VALID_CREDS",
                        "latest_failure_reason": reason
                    })
    
    if not matches:
        return json.dumps({"status": "error", "message": f"No credentials found matching '{query}'"}, indent=2)
        
    return json.dumps({"status": "success", "results": matches}, indent=2)


def store(platform: str, username: str, password: str) -> str:
    """Store or update a credential."""
    data = _load_vault()
    platform_lower = platform.lower()
    
    if platform_lower not in data:
        data[platform_lower] = []
        
    for cred in data[platform_lower]:
        if cred.get("username") == username and cred.get("password") == password:
            cred["status"] = "valid"
            cred["last_updated"] = datetime.now().isoformat()
            _save_vault(data)
            return json.dumps({"status": "success", "message": f"Credential for '{platform}' updated and verified."})
            
    data[platform_lower].append({
        "username": username,
        "password": password,
        "status": "valid",
        "invalid_reason": "",
        "last_updated": datetime.now().isoformat()
    })
    
    _save_vault(data)
    return json.dumps({"status": "success", "message": f"Successfully stored new credential for '{platform}'."})


def invalidate(platform: str, username: str, reason: str) -> str:
    """Mark a credential explicitly invalid."""
    data = _load_vault()
    
    # We must find the exact platform because they passed it, but case-insensitive
    target_platform = None
    for p in data.keys():
        if platform.lower() == p.lower():
            target_platform = p
            break
            
    if not target_platform:
        return json.dumps({"status": "error", "message": f"No platform found matching '{platform}'"})
        
    updated = False
    for cred in data[target_platform]:
        if cred.get("username") == username:
            cred["status"] = "invalid"
            cred["invalid_reason"] = reason
            cred["last_updated"] = datetime.now().isoformat()
            updated = True
            
    if updated:
        _save_vault(data)
        return json.dumps({"status": "success", "message": f"Successfully invalidated '{username}' on '{platform}'. Reason logged."})
        
    return json.dumps({"status": "error", "message": f"Username '{username}' not found under '{platform}'."})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Swarm Native Credential Backend")
    subparsers = parser.add_subparsers(dest="action", required=True)
    
    # Search command
    search_p = subparsers.add_parser("search")
    search_p.add_argument("query", help="Keyword or semantic phrase to search for")
    
    # Store command
    store_p = subparsers.add_parser("store")
    store_p.add_argument("platform")
    store_p.add_argument("username")
    store_p.add_argument("password")
    
    # Invalidate command
    inv_p = subparsers.add_parser("invalidate")
    inv_p.add_argument("platform")
    inv_p.add_argument("username")
    inv_p.add_argument("reason")
    
    args = parser.parse_args()
    
    # Resolve relative vault path logic based on execution directory
    # Assumes executed from root `nanobot` dir or one level down.
    if not VAULT_PATH.parent.exists():
        # Fallback if running directly from script dir
        alternative_path = Path("../../workspace/memory/credential_manager.json").resolve()
        if alternative_path.parent.exists():
            VAULT_PATH = alternative_path
            
    if args.action == "search":
        print(search(args.query))
    elif args.action == "store":
        print(store(args.platform, args.username, args.password))
    elif args.action == "invalidate":
        print(invalidate(args.platform, args.username, args.reason))
