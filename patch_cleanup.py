import os
import glob

loop_path = r'C:\Users\HP\nanobot\nanobot\agent\loop.py'
with open(loop_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Logic to inject:
# Check for .cleanup_telegram trigger file
# Delete telegram sessions if found
new_logic = '''
        # One-time Telegram cleanup logic
        trigger_file = os.path.join(self.workspace, ".cleanup_telegram")
        if os.path.exists(trigger_file):
            logger.info("One-time Telegram cleanup triggered.")
            telegram_sessions = glob.glob(os.path.join(self.workspace, "sessions", "telegram_*.jsonl"))
            for session_file in telegram_sessions:
                try:
                    with open(session_file, 'w') as f:
                        f.write('')
                    logger.info(f"Cleared Telegram session: {os.path.basename(session_file)}")
                except Exception as e:
                    logger.error(f"Failed to clear {session_file}: {e}")
            
            # Revert the state: delete the trigger file
            try:
                os.remove(trigger_file)
                logger.info("Cleanup completed. Trigger removed to prevent future deletions.")
            except Exception as e:
                logger.error(f"Failed to remove trigger file: {e}")
'''

# Inject after workspace resolution in __init__
marker = 'self.workspace = workspace'
if marker in content and 'cleanup_telegram' not in content:
    content = content.replace(marker, marker + new_logic)
    with open(loop_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched loop.py with self-reverting cleanup logic")
else:
    print("Failed to patch loop.py or already patched")
