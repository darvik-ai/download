import os
import json
from flask import Flask, render_template_string

app = Flask(__name__)

# --- CONFIGURATION ---
STATE_FILE = "download_state.json"
MAX_SUCCESS_REQUESTS = 1000
DEFAULT_STATE = { "total_attempts": 0, "total_successful": 0, "total_failed": 0 }

# --- STATE READING FUNCTION ---
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return DEFAULT_STATE.copy()
    return DEFAULT_STATE.copy()

# --- FLASK ROUTE ---
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
