import multiprocessing
import os
import subprocess
import time

def run_script(script_name):
    print(f"🚀 Starting {script_name}...")
    # Use Popen to avoid blocking the parent process
    subprocess.Popen(["python", script_name])

if __name__ == '__main__':
    print("💎 PincFull Pro Master System v19.1")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Start Diagnostic Bot
    run_script("bot_pa_v16.py")
    
    time.sleep(3) # Wait for first bot to init
    
    # Start Admin Bot
    run_script("admin_bot.py")

    print("\n✅ Both bots are now starting in separate processes!")
    print("Check Telegram to verify operation.")
    
    # Keep the main process alive so we can see output if any
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 Shutting down master...")
        # Since they are Popen in background, they might keep running
        # User should use pkill -f .py to be sure
