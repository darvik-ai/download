import os
import requests
import uuid
import time
import json
import random
import threading
from flask import Flask, render_template_string

app = Flask(__name__)

# ==============================================================================
# ==> CONFIGURATION
# ==============================================================================
BASE_URL = "https://user-gen-media-assets.s3.amazonaws.com/gemini_images/"
OUTPUT_DIR = "downloaded_images_server"
LOG_FILE = "successful_downloads_server.txt"
STATE_FILE = "download_state.json"
MAX_SUCCESS_REQUESTS = 1000

# ==============================================================================
# ==> GLOBAL STATE MANAGEMENT
# ==============================================================================
DEFAULT_STATE = {
    "total_attempts": 0,
    "total_successful": 0,
    "total_failed": 0,
}

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return DEFAULT_STATE.copy()
    return DEFAULT_STATE.copy()

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=4)

download_state = load_state()
download_thread = None
download_stop_event = threading.Event()

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ==============================================================================
# ==> BACKGROUND DOWNLOADER (WITH FORCED LOG FLUSHING)
# ==============================================================================

def background_downloader():
    global download_state
    # Short pause to ensure the logging system is ready before the first print
    time.sleep(2)
    print("INFO: Background downloader thread started.", flush=True)

    while not download_stop_event.is_set():
        if download_state.get("total_successful", 0) < MAX_SUCCESS_REQUESTS:
            download_state["total_attempts"] += 1
            filename = f"{uuid.uuid4()}.png"
            full_url = f"{BASE_URL}{filename}"
            
            print(f"ATTEMPT: #{download_state['total_attempts']} | Trying URL: {full_url}", flush=True)

            try:
                response = requests.get(full_url, stream=True, timeout=15)
                
                if response.status_code == 200:
                    print(f"-> SUCCESS! RESPONSE: 200 OK", flush=True)
                    download_state["total_successful"] += 1
                    local_path = os.path.join(OUTPUT_DIR, filename)
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    with open(LOG_FILE, 'a') as f_log:
                        f_log.write(full_url + '\n')
                else:
                    print(f"-> FAILED. RESPONSE: {response.status_code}", flush=True)
                    download_state["total_failed"] += 1
            
            except requests.exceptions.RequestException as e:
                download_state["total_failed"] += 1
                print(f"-> ERROR: Network request failed: {e}", flush=True)

            save_state(download_state)

            sleep_seconds = random.randint(2 * 60, 3 * 60)
            print(f"INFO: Sleeping for {sleep_seconds / 60:.1f} minutes...", flush=True)
            print("-" * 40, flush=True)
            for _ in range(sleep_seconds):
                if download_stop_event.is_set(): break
                time.sleep(1)
        else:
            for _ in range(60):
                if download_stop_event.is_set(): break
                time.sleep(1)
    
    print("INFO: Background downloader thread has stopped.", flush=True)

# ==============================================================================
# ==> FLASK ROUTES
# ==============================================================================
@app.route('/')
def index():
    current_state = load_state()
    status_msg = ""
    
    if current_state.get("total_successful", 0) < MAX_SUCCESS_REQUESTS:
        status_msg = "Actively downloading..."
    else:
        status_msg = f"Goal of {MAX_SUCCESS_REQUESTS} successful downloads reached. Downloader is idle."

    template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Image Downloader Status</title>
        <meta http-equiv="refresh" content="60">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background-color: #f4f4f9; color: #333; }
            .container { background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 15px rgba(0,0,0,0.1); max-width: 600px; margin: auto; }
            h1 { color: #2c3e50; text-align: center; margin-bottom: 30px; }
            p { font-size: 1.1em; line-height: 1.6; }
            strong { color: #34495e; }
            .success { color: #27ae60; font-weight: bold; }
            .failure { color: #c0392b; font-weight: bold; }
            .status { background-color: #ecf0f1; border-left: 5px solid #3498db; padding: 15px; margin-top: 20px; border-radius: 4px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Image Downloader Status</h1>
            <p><strong>Total Attempts:</strong> {{ state.get('total_attempts', 0) }}</p>
            <p><strong class="success">Total Images Downloaded:</strong> {{ state.get('total_successful', 0) }} / {{ max_success }}</p>
            <p><strong class="failure">Total Failed Attempts:</strong> {{ state.get('total_failed', 0) }}</p>
            <div class="status">
                <p><strong>Current Status:</strong> {{ status_message }}</p>
            </div>
            <p style="margin-top: 30px; font-size: 0.9em; text-align: center; color: #7f8c8d;">
                <i>This page refreshes automatically every 60 seconds.</i>
            </p>
        </div>
    </body>
    </html>
    """
    return render_template_string(template, state=current_state, status_message=status_msg, max_success=MAX_SUCCESS_REQUESTS)

# ==============================================================================
# ==> SERVER STARTUP
# ==============================================================================

def start_downloader_thread():
    global download_thread
    if download_thread is None or not download_thread.is_alive():
        download_thread = threading.Thread(target=background_downloader, daemon=True)
        download_thread.start()
        print("INFO: Downloader thread starting sequence initiated.", flush=True)

if __name__ == '__main__':
    start_downloader_thread()
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nINFO: Server shutting down...", flush=True)
    finally:
        download_stop_event.set()
        print("INFO: Application exiting.", flush=True)
