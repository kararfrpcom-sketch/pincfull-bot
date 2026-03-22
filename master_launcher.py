import multiprocessing
import os
import subprocess
import time

def start_diagnostic_bot():
    print("🚀 Starting Diagnostic Bot (@panic2_bot)...")
    subprocess.run(["python", "bot_pa_v16.py"])

def start_admin_bot():
    print("🛡️ Starting Admin Management Bot...")
    subprocess.run(["python", "admin_bot.py"])

if __name__ == '__main__':
    print("💎 PincFull Pro Master System v18.2")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    
    # Create processes
    p1 = multiprocessing.Process(target=start_diagnostic_bot)
    p2 = multiprocessing.Process(target=start_admin_bot)

    # Start processes
    p1.start()
    time.sleep(2) # Brief delay to avoid log mixup
    p2.start()

    print("✅ Both bots are now running in the background!")
    print("Press Ctrl+C to stop both.")
    
    try:
        p1.join()
        p2.join()
    except KeyboardInterrupt:
        print("\n🛑 Stopping all bots...")
        p1.terminate()
        p2.terminate()
        print("Done.")
