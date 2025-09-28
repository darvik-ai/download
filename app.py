import os
import requests
import uuid
import time
import json
import random
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify

app = Flask(__name__)

# ==============================================================================
# ==> CONFIGURATION - CHANGE THESE VARIABLES
# ==============================================================================

# 1. The base URL where the images are stored.
#    (Must end with a forward slash '/')
# https://user-gen-media-assets.s3.amazonaws.com/gemini_images/5df452ce-91b6-433d-bb97-abe2eed3aab8.png
BASE_URL = "https://user-gen-media-assets.s3.amazonaws.com/gemini_images/"

# 2. The local directory where you want to save the downloaded images.
OUTPUT_DIR = "downloaded_images_server"

# 3. The name of the file to store the list of successfully found URLs.
LOG_FILE = "successful_downloads_server.txt"

# 4. State file to persist download progress and timers.
STATE_FILE = "download_state.json"

# 5. Maximum number of successful downloads before stopping.
MAX_SUCCESS_REQUESTS = 1000

# 6. Time window for active downloading (e.g., 48 hours).
ACTIVE_DOWNLOAD_WINDOW_HOURS = 24

# 7. Cooldown period after an active window (e.g., 48 hours before restarting).
COOLDOWN_WINDOW_HOURS = 12

# ==============================================================================
# ==> GLOBAL STATE (for persistence and background thread communication)
# ==============================================================================
# Default state structure
DEFAULT_STATE = {
    "total_attempts": 0,
    "total_successful": 0,
    "total_failed": 0,
    "downloading_active": False,
    "current_active_window_start": None, # datetime string when current active window began
    "current_cooldown_window_start": None, # datetime string when current cooldown window began
}

# Load state from file or use default
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            state = json.load(f)
            # Convert datetime strings back to datetime objects
            for key in ["current_active_window_start", "current_cooldown_window_start"]:
                if state.get(key):
                    state[key] = datetime.fromisoformat(state[key])
            return state
    return DEFAULT_STATE.copy()

# Save state to file
def save_state(state):
    with open(STATE_FILE, 'w') as f:
        # Convert datetime objects to ISO format strings for JSON serialization
        state_copy = state.copy()
        for key in ["current_active_window_start", "current_cooldown_window_start"]:
            if state_copy.get(key):
                state_copy[key] = state_copy[key].isoformat()
        json.dump(state_copy, f, indent=4)

download_state = load_state()
download_thread = None
download_stop_event = threading.Event() # Event to signal the download thread to stop

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# ==> BACKGROUND DOWNLOADER THREAD FUNCTION
# ==============================================================================

def background_downloader():
    global download_state
    
    # Initialize/restore active window if needed
    if not download_state["current_active_window_start"] and not download_state["current_cooldown_window_start"]:
        print("Starting new active download window.")
        download_state["current_active_window_start"] = datetime.now()
        download_state["downloading_active"] = True
        save_state(download_state)
    elif download_state["current_cooldown_window_start"]:
        cooldown_end_time = download_state["current_cooldown_window_start"] + timedelta(hours=COOLDOWN_WINDOW_HOURS)
        if datetime.now() < cooldown_end_time:
            print(f"Still in cooldown period. Resuming active download in {cooldown_end_time - datetime.now()}.")
            download_state["downloading_active"] = False # Ensure not active during cooldown
            save_state(download_state)
        else:
            print("Cooldown period finished. Starting new active download window.")
            download_state["current_cooldown_window_start"] = None
            download_state["current_active_window_start"] = datetime.now()
            download_state["downloading_active"] = True
            save_state(download_state)
    elif download_state["current_active_window_start"]:
        active_window_end_time = download_state["current_active_window_start"] + timedelta(hours=ACTIVE_DOWNLOAD_WINDOW_HOURS)
        if datetime.now() < active_window_end_time:
            print(f"Resuming active download within window. Time left: {active_window_end_time - datetime.now()}.")
            download_state["downloading_active"] = True
            save_state(download_state)
        else:
            print("Active download window finished. Starting cooldown.")
            download_state["current_active_window_start"] = None
            download_state["current_cooldown_window_start"] = datetime.now()
            download_state["downloading_active"] = False
            save_state(download_state)


    while not download_stop_event.is_set():
        # Check active window and cooldown periods
        now = datetime.now()

        if download_state["downloading_active"]:
            active_window_end_time = download_state["current_active_window_start"] + timedelta(hours=ACTIVE_DOWNLOAD_WINDOW_HOURS)
            if now >= active_window_end_time:
                print(f"Active download window of {ACTIVE_DOWNLOAD_WINDOW_HOURS} hours finished. Entering {COOLDOWN_WINDOW_HOURS} hour cooldown.")
                download_state["current_active_window_start"] = None
                download_state["current_cooldown_window_start"] = now
                download_state["downloading_active"] = False
                save_state(download_state)
                # No need to break the loop, just enter cooldown phase and wait for next check
                
        if not download_state["downloading_active"]: # If currently in cooldown or active window ended
            if download_state["current_cooldown_window_start"]:
                cooldown_end_time = download_state["current_cooldown_window_start"] + timedelta(hours=COOLDOWN_WINDOW_HOURS)
                if now >= cooldown_end_time:
                    print(f"Cooldown period of {COOLDOWN_WINDOW_HOURS} hours finished. Restarting active download window.")
                    download_state["current_cooldown_window_start"] = None
                    download_state["current_active_window_start"] = now
                    download_state["downloading_active"] = True
                    save_state(download_state)
                else:
                    # Still in cooldown, just sleep for a while and recheck
                    print(f"Still in cooldown. Next check in 60 seconds. Remaining: {cooldown_end_time - now}")
                    time.sleep(60) # Sleep for a shorter period during cooldown to recheck status
                    continue # Skip actual download attempt
            else: # Should not happen if logic is sound, but as a fallback
                print("Download state inconsistent. Resetting to active.")
                download_state["current_active_window_start"] = now
                download_state["downloading_active"] = True
                save_state(download_state)
        
        # Only proceed with download attempts if active and not stopped by success limit
        if download_state["downloading_active"] and download_state["total_successful"] < MAX_SUCCESS_REQUESTS:
            download_state["total_attempts"] += 1
            filename = f"{uuid.uuid4()}.png"
            full_url = f"{BASE_URL}{filename}"
            local_path = os.path.join(OUTPUT_DIR, filename)

            print(f"\nAttempt #{download_state['total_attempts']} | Trying: {filename[:23]}...")

            try:
                response = requests.get(full_url, stream=True, timeout=10)

                if response.status_code == 200:
                    download_state["total_successful"] += 1
                    print(f"✅ SUCCESS! ({download_state['total_successful']}/{MAX_SUCCESS_REQUESTS}) Downloading to {local_path}")
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    # Append to log file
                    with open(LOG_FILE, 'a') as f_log:
                        f_log.write(full_url + '\n')
                else:
                    download_state["total_failed"] += 1
                    # print(f"❌ Failed with status code: {response.status_code}") # Too verbose for random guessing
                
            except requests.exceptions.RequestException as e:
                download_state["total_failed"] += 1
                print(f"❌ Network Error: {e}")

            save_state(download_state) # Save state after each attempt

            if download_state["total_successful"] >= MAX_SUCCESS_REQUESTS:
                print(f"Goal of {MAX_SUCCESS_REQUESTS} successful downloads reached. Stopping downloader.")
                download_state["downloading_active"] = False # Mark as inactive
                save_state(download_state)
                break # Exit the loop if max successes reached

            # Random sleep between 2 and 10 minutes
            sleep_time_seconds = random.randint(1 * 60, 3 * 60)
            print(f"Sleeping for {sleep_time_seconds / 60:.1f} minutes...")
            for _ in range(sleep_time_seconds):
                if download_stop_event.is_set():
                    break # Allow server shutdown to interrupt long sleep
                time.sleep(1)
        else:
            # If not active for downloading, or if max successes reached, just sleep and check again
            if download_state["total_successful"] >= MAX_SUCCESS_REQUESTS:
                print(f"Max successful downloads ({MAX_SUCCESS_REQUESTS}) reached. Download thread is idle.")
            else:
                print("Download thread is currently in a paused/cooldown state.")
            
            # Sleep longer if idle, but check stop event periodically
            for _ in range(60): # Check every minute
                if download_stop_event.is_set():
                    break
                time.sleep(1)

    print("Background downloader thread finished.")


# ==============================================================================
# ==> FLASK ROUTES
# ==============================================================================

@app.route('/')
def index():
    global download_state
    current_state = load_state() # Reload state for up-to-date info
    
    status_msg = ""
    if current_state["downloading_active"]:
        if current_state["current_active_window_start"]:
            active_end_time = current_state["current_active_window_start"] + timedelta(hours=ACTIVE_DOWNLOAD_WINDOW_HOURS)
            time_left = active_end_time - datetime.now()
            status_msg = f"Actively downloading. Window ends in {time_left.days}d {time_left.seconds//3600}h {(time_left.seconds%3600)//60}m."
        else:
            status_msg = "Actively downloading."
    elif current_state["current_cooldown_window_start"]:
        cooldown_end_time = current_state["current_cooldown_window_start"] + timedelta(hours=COOLDOWN_WINDOW_HOURS)
        time_left = cooldown_end_time - datetime.now()
        status_msg = f"In cooldown period. Will resume in {time_left.days}d {time_left.seconds//3600}h {(time_left.seconds%3600)//60}m."
    elif current_state["total_successful"] >= MAX_SUCCESS_REQUESTS:
        status_msg = f"Maximum successful downloads ({MAX_SUCCESS_REQUESTS}) reached. Downloader is stopped."
    else:
        status_msg = "Downloader is paused or has not started its active window."

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Downloader Status</title>
        <meta http-equiv="refresh" content="60"> <style>
            body { font-family: Arial, sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
            .container { background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }
            h1 { color: #0056b3; text-align: center; margin-bottom: 30px; }
            p { font-size: 1.1em; line-height: 1.6; }
            strong { color: #007bff; }
            .success { color: #28a745; font-weight: bold; }
            .failure { color: #dc3545; font-weight: bold; }
            .status { background-color: #e9ecef; border-left: 5px solid #007bff; padding: 15px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Image Downloader Status</h1>
            <p><strong>Total Attempts:</strong> {{ state.total_attempts }}</p>
            <p><strong class="success">Total Images Downloaded (Success):</strong> {{ state.total_successful }}</p>
            <p><strong class="failure">Total Images Failed:</strong> {{ state.total_failed }}</p>
            <div class="status">
                <p><strong>Current Status:</strong> {{ status_message }}</p>
                {% if state.current_active_window_start %}
                    <p><strong>Active Window Started:</strong> {{ state.current_active_window_start.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                {% endif %}
                {% if state.current_cooldown_window_start %}
                    <p><strong>Cooldown Started:</strong> {{ state.current_cooldown_window_start.strftime('%Y-%m-%d %H:%M:%S') }}</p>
                {% endif %}
            </div>
            <p style="margin-top: 30px; font-size: 0.9em; text-align: center; color: #666;">
                <i>This page refreshes every 60 seconds to show the latest status.</i>
            </p>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, state=current_state, status_message=status_msg)

@app.route('/status_json')
def status_json():
    current_state = load_state()
    # Convert datetime objects to string for JSON
    for key in ["current_active_window_start", "current_cooldown_window_start"]:
        if current_state.get(key):
            current_state[key] = current_state[key].isoformat()
    return jsonify(current_state)


# ==============================================================================
# ==> SERVER STARTUP AND SHUTDOWN
# ==============================================================================

def start_downloader_thread():
    global download_thread, download_stop_event
    if download_thread is None or not download_thread.is_alive():
        download_stop_event.clear() # Clear the stop event
        download_thread = threading.Thread(target=background_downloader, daemon=True)
        download_thread.start()
        print("Downloader thread started.")
    else:
        print("Downloader thread is already running.")

def stop_downloader_thread():
    global download_thread, download_stop_event
    if download_thread and download_thread.is_alive():
        print("Signaling downloader thread to stop...")
        download_stop_event.set() # Set the stop event
        download_thread.join(timeout=30) # Wait for the thread to finish (max 30 seconds)
        if download_thread.is_alive():
            print("Warning: Downloader thread did not terminate gracefully.")
        else:
            print("Downloader thread stopped.")
    else:
        print("No active downloader thread to stop.")


if __name__ == '__main__':
    start_downloader_thread()
    try:
        app.run(host='0.0.0.0', port=5000, debug=False) # debug=True can cause issues with threading
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        stop_downloader_thread()
        print("Application exiting.")
