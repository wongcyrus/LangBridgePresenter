#!/usr/bin/env python3
import os
import json
import subprocess
import sys

# Paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
CDKTF_DIR = os.path.join(BACKEND_DIR, "cdktf")
ADMIN_TOOLS_CONFIG = os.path.join(BACKEND_DIR, "admin_tools", "config.py")
PRELOADER_CONFIG = os.path.join(BACKEND_DIR, "presentation-preloader", "config.py")
TESTS_ENV = os.path.join(BACKEND_DIR, "tests", ".env.test")
CDKTF_ENV = os.path.join(CDKTF_DIR, ".env")

def get_cdktf_outputs():
    # 1. Check for static output file in backend dir (passed from deploy machine)
    static_output_file = os.path.join(BACKEND_DIR, "cdktf_outputs.json")
    if os.path.exists(static_output_file):
        print(f"Loading configuration from {static_output_file}...")
        try:
            with open(static_output_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {static_output_file}: {e}")
            # Fallback to dynamic fetch if file is corrupt? No, explicit file should be trusted.
            return None

    # 2. Fallback: Fetch dynamically from CDKTF
    print(f"Fetching CDKTF outputs from {CDKTF_DIR}...")
    temp_output_file = os.path.join(CDKTF_DIR, "cdktf_outputs.json")
    try:
        # Run npx cdktf output to a temporary file
        # Redirect stdout to capture logs, but send JSON to the file
        subprocess.run(
            ["npx", "cdktf", "output", "--outputs-file-include-sensitive-outputs", "--outputs-file", "cdktf_outputs.json"],
            cwd=CDKTF_DIR,
            check=True,
            stdout=subprocess.PIPE, # Capture stdout to prevent clutter
            stderr=subprocess.PIPE  # Capture stderr
        )
        
        if not os.path.exists(temp_output_file):
            print("Error: Output file not created")
            return None

        with open(temp_output_file, 'r') as f:
            data = json.load(f)
            
        # ALWAYS save to backend/cdktf_outputs.json for future use
        print(f"Saving fetched outputs to {static_output_file}...")
        with open(static_output_file, 'w') as f:
            json.dump(data, f, indent=2)
            
        return data

    except subprocess.CalledProcessError as e:
        print(f"Error running cdktf output: {e}")
        print(e.stderr.decode() if e.stderr else "")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from file: {e}")
        return None
    finally:
        # Clean up temp file
        if os.path.exists(temp_output_file):
            os.remove(temp_output_file)

def read_env_file(filepath):
    env_vars = {}
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def update_python_config(filepath, config_data):
    print(f"Updating {filepath}...")
    try:
        with open(filepath, 'w') as f:
            for key, value in config_data.items():
                f.write(f'{key}="{value}"\n')
        print(f"Successfully updated {filepath}")
    except Exception as e:
        print(f"Error updating {filepath}: {e}")

def update_test_env(filepath, env_data):
    print(f"Updating {filepath}...")
    try:
        with open(filepath, 'w') as f:
            for key, value in env_data.items():
                f.write(f'{key}={value}\n')
        print(f"Successfully updated {filepath}")
    except Exception as e:
        print(f"Error updating {filepath}: {e}")

def main():
    # 1. Get CDKTF Outputs
    outputs = get_cdktf_outputs()
    if not outputs:
        print("Failed to get CDKTF outputs. Exiting.")
        sys.exit(1)

    # Flatten outputs if they are nested under a stack name (e.g., "cdktf")
    if "project-id" not in outputs:
        found = False
        for key, value in outputs.items():
            if isinstance(value, dict) and "project-id" in value:
                print(f"Found outputs in stack: {key}")
                outputs = value
                found = True
                break
        if not found:
            print("Error: 'project-id' not found in CDKTF outputs.")
            print(f"Available top-level keys: {list(outputs.keys())}")
            # Print one level deeper for debugging
            for k, v in outputs.items():
                print(f"  Key '{k}' has keys: {list(v.keys()) if isinstance(v, dict) else 'not a dict'}")
            sys.exit(1)

    # Extract required values (handle different output formats if needed)
    # outputs is a dict like: {"project-id": "...", "api-url": "...", ...}
    project_id = outputs.get("project-id")
    api_service_name = outputs.get("api-service-name")
    speech_file_bucket = outputs.get("speech-file-bucket")
    api_url = outputs.get("api-url")

    if not all([project_id, api_service_name, speech_file_bucket, api_url]):
        print("Missing required outputs from CDKTF.")
        print(f"Available keys: {list(outputs.keys())}")
        sys.exit(1)

    print("Retrieved configuration:")
    print(f"  project_id: {project_id}")
    print(f"  api_service_name: {api_service_name}")
    print(f"  api_url: {api_url}")
    print(f"  speech_file_bucket: {speech_file_bucket}")

    # 2. Read .env from CDKTF (or Fallback to OS Env)
    cdktf_env = read_env_file(CDKTF_ENV)
    
    # Try to get keys from .env file first, then OS env, then default
    secret_key = cdktf_env.get("XIAOICE_CHAT_SECRET_KEY") or os.environ.get("XIAOICE_CHAT_SECRET_KEY") or "default_secret_key"
    access_key = cdktf_env.get("XIAOICE_CHAT_ACCESS_KEY") or os.environ.get("XIAOICE_CHAT_ACCESS_KEY") or "default_access_key"

    # 3. Update admin_tools/config.py
    admin_config = {
        "project_id": project_id,
        "api": api_service_name,
        "speech_file_bucket": speech_file_bucket
    }
    update_python_config(ADMIN_TOOLS_CONFIG, admin_config)

    # 4. Update presentation-preloader/config.py
    # Note: The original script checked if directory exists, but here we assume structure is fixed or we check file existence
    if os.path.exists(os.path.dirname(PRELOADER_CONFIG)):
        update_python_config(PRELOADER_CONFIG, admin_config)
    else:
        print(f"Skipping {PRELOADER_CONFIG} (directory not found)")

    # 5. Update tests/.env.test
    test_env_data = {
        "API_URL": f"https://{api_url}",
        "XIAOICE_CHAT_SECRET_KEY": secret_key,
        "XIAOICE_CHAT_ACCESS_KEY": access_key
    }
    update_test_env(TESTS_ENV, test_env_data)

    # 6. Update client/web-student/.env
    client_project_id = outputs.get("client-project-id")
    webapp_app_id = outputs.get("webapp-app-id")
    hosting_url = outputs.get("hosting-url")
    firebase_api_key = outputs.get("firebase-api-key")

    if client_project_id and webapp_app_id and firebase_api_key:
        client_env_path = os.path.join(BACKEND_DIR, "..", "client", "web-student", ".env")
        print(f"Updating Client .env at {client_env_path}...")
        
        # Extract sender ID from App ID (format: 1:SENDER_ID:web:...)
        sender_id = webapp_app_id.split(":")[1] if ":" in webapp_app_id else ""

        client_env_data = {
            "VITE_FIREBASE_API_KEY": firebase_api_key,
            "VITE_FIREBASE_AUTH_DOMAIN": f"{client_project_id}.firebaseapp.com",
            "VITE_FIREBASE_PROJECT_ID": client_project_id,
            "VITE_FIREBASE_STORAGE_BUCKET": f"{client_project_id}.firebasestorage.app",
            "VITE_FIREBASE_MESSAGING_SENDER_ID": sender_id,
            "VITE_FIREBASE_APP_ID": webapp_app_id,
            "VITE_FIREBASE_HOSTING_URL": hosting_url
        }
        update_test_env(client_env_path, client_env_data)
    else:
        print("Skipping client .env update: Missing Firebase outputs (api-key, project-id, or app-id)")

if __name__ == "__main__":
    main()
