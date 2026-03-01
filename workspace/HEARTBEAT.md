# Heartbeat Tasks

This file is checked every 30 minutes by your nanobot agent.
Add tasks below that you want the agent to work on periodically.

If this file has no tasks (only headers and comments), the agent will skip the heartbeat.

## Active Tasks

- [ ] Execute `python nanobot/agent/machine_scanner.py` to continuously index the local OS and update MACHINE_ENV and REPO_CATALOG.
- [ ] Execute `python nanobot/agent/desktop_calibrator.py` to occasionally scan the desktop UI and cache stable icon X/Y coordinates to UI_ATLAS.

<!-- Add your periodic tasks below this line -->

## Completed

<!-- Move completed tasks here or delete them -->

