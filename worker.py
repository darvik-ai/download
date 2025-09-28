import os
import requests
import uuid
import time
import json
import random

# --- CONFIGURATION ---
BASE_URL = "https://user-gen-media-assets.s3.amazonaws.com/gemini_images/"
OUTPUT_DIR = "downloaded_images_server"
LOG_FILE = "successful_downloads_server.txt"
STATE_FILE = "download_state.json"
MAX_SUCCESS_REQUESTS = 1000

# --- STATE MANAGEMENT ---
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

# --- THE MAIN DOWNLOAD LOOP ---
def run_downloader():
    # Ensure directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Load the initial state
    download_state = load_state()
    
    print("--- WORKER STARTED ---", flush=True)

    while True:
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
            time.sleep(sleep_seconds)
        else:
            # Goal reached, idle peacefully.
            print("INFO: Goal reached. Worker is now idle. Checking again in 5 minutes.", flush=True)
            time.sleep(300)

if __name__ == '__main__':
    run_downloader()
