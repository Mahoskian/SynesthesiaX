import requests
import json
import time
import threading
import webbrowser
import os
from config import CLIENT_ID, CLIENT_SECRET
from flask import Flask, request, jsonify

# https://developer.spotify.com/dashboard
# http://localhost:8888/login

# 🔹 Replace with your Spotify Developer credentials
REDIRECT_URI = "http://localhost:8888/callback"

# 🔹 Spotify API URLs
AUTH_URL = "https://accounts.spotify.com/authorize"
TOKEN_URL = "https://accounts.spotify.com/api/token"
CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
TRACK_AUDIO_FEATURES = "https://api.spotify.com/v1/audio-features/"
TRACK_AUDIO_ANALYSIS = "https://api.spotify.com/v1/audio-analysis/"

# Get the absolute path of the directory where the script is running
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "spotify_tokens.json")

# 🔹 Scopes (Permissions)
SCOPES = "user-read-currently-playing user-read-playback-state"

app = Flask(__name__)
access_token = None
refresh_token = None

# 🔹 Load tokens from file if available
def load_tokens():
    global access_token, refresh_token
    try:
        with open(TOKEN_FILE, "r") as f:
            token_data = json.load(f)
            access_token = token_data.get("access_token")
            refresh_token = token_data.get("refresh_token")
    except FileNotFoundError:
        print("⚠️ spotify_tokens.json not found. No tokens loaded.")

# 🔹 Save tokens to file
def save_tokens(token_data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

@app.route("/")
def home():
    return "Go to /login to authenticate with Spotify."

@app.route("/login")
def login():
    auth_request_url = (
        f"{AUTH_URL}?client_id={CLIENT_ID}&response_type=code"
        f"&redirect_uri={REDIRECT_URI}&scope={SCOPES}"
    )
    webbrowser.open(auth_request_url)
    return "Opening Spotify login..."

@app.route("/callback")
def callback():
    global access_token, refresh_token

    auth_code = request.args.get("code")
    if not auth_code:
        return "Error: Authorization code not received", 400

    # 🔹 Exchange the auth code for an access token
    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(TOKEN_URL, data=data)
    token_info = response.json()
    print("Token Response:", token_info)  # Debugging

    if "access_token" not in token_info:
        return f"Error: 'access_token' not found in response. Full response: {token_info}", 400

    access_token = token_info["access_token"]
    refresh_token = token_info.get("refresh_token", None)
    save_tokens(token_info)
    return "Authorization successful! Tokens saved."

def refresh_access_token():
    """Automatically refresh the Spotify access token using the refresh token."""
    global access_token, refresh_token
    if not refresh_token:
        print("⚠️ No refresh token available! Re-authentication needed.")
        return None

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
    }
    response = requests.post(TOKEN_URL, data=data)
    new_token_info = response.json()
    if "access_token" in new_token_info:
        access_token = new_token_info["access_token"]
        save_tokens(new_token_info)
        print("✅ Access token refreshed successfully.")
        return access_token
    else:
        print("⚠️ Failed to refresh access token:", new_token_info)
        return None

def get_current_song():
    """Fetch the currently playing song from Spotify and auto-refresh token if needed."""
    global access_token
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(CURRENTLY_PLAYING_URL, headers=headers)
    if response.status_code == 401:  # Token expired
        print("🔄 Token expired. Refreshing...")
        access_token = refresh_access_token()
        headers["Authorization"] = f"Bearer {access_token}"
        response = requests.get(CURRENTLY_PLAYING_URL, headers=headers)

    if response.status_code == 200:
        data = response.json()
        track = data["item"]
        track_name = track["name"]
        artist_name = track["artists"][0]["name"]
        track_id = track["id"]

        print("--------------------------------------------------------")

        print("\n🎵 Now Playing:")
        print(f"   Track: {track_name}")
        print(f"   Artist: {artist_name}")
        print(f"   ID: {track_id}")
    
        return {
            "track_name": track_name,
            "artist_name": artist_name,
            "track_id": track_id
        }
    print("🚫 No song currently playing or token expired.")
    return None

@app.route("/refresh-token")
def refresh_token_route():
    """Manually refresh the access token (for testing)."""
    new_token = refresh_access_token()
    return jsonify({"message": "Token refreshed", "access_token": new_token})

def start_song_monitor():
    """Continuously check the currently playing song every 60 seconds."""
    while True:
        get_current_song()
        time.sleep(10)

if __name__ == "__main__":
    load_tokens()
    # Start the background thread to monitor songs
    threading.Thread(target=start_song_monitor, daemon=True).start()
    app.run(port=8888)
