import os
import pytest
import time
import hashlib
import json
import uuid
from typing import Dict

@pytest.fixture(scope="session")
def api_url():
    """Fixture to return the base API URL."""
    # Load from .env.test if available
    env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.test")
    if os.path.exists(env_file_path):
        import dotenv
        dotenv.load_dotenv(env_file_path)

    url = os.getenv("API_URL")
    if not url:
        pytest.skip("API_URL environment variable not set or found in .env.test")
    
    # Normalize URL: remove trailing slash and optional trailing /api
    # This ensures that if the user provides '.../api', we don't end up with '.../api/api/...'
    url = url.rstrip("/")
    if url.endswith("/api"):
        url = url[:-4]
        
    return url

@pytest.fixture(scope="session")
def auth_keys():
    """Return (secret_key, access_key) tuple."""
    # Load from .env.test if available. Note: This assumes dotenv has been loaded by api_url fixture already, 
    # but we include it here for robustness if auth_keys is called independently.
    env_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env.test")
    if os.path.exists(env_file_path):
        import dotenv
        dotenv.load_dotenv(env_file_path)

    secret_key = (
        os.getenv("XiaoiceChatSecretKey")
        or os.getenv("XIAOICE_CHAT_SECRET_KEY")
        or "test_secret_key"
    )
    access_key = (
        os.getenv("XiaoiceChatAccessKey")
        or os.getenv("XIAOICE_CHAT_ACCESS_KEY")
        or "test_access_key"
    )
    return secret_key, access_key

@pytest.fixture(scope="session")
def api_key():
    """Fixture to load the admin API key from the file system."""
    api_key_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "admin_tools",
        "api_key.json"
    )
    try:
        with open(api_key_path, 'r') as f:
            data = json.load(f)
            return data.get("key_string")
    except FileNotFoundError:
        return None

def calculate_signature(body_string: str, secret_key: str, timestamp: str) -> str:
    """Calculate signature for authentication using v2 algorithm."""
    params = {"bodyString": body_string, "secretKey": secret_key, "timestamp": timestamp}
    signature_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hashlib.sha512(signature_string.encode("utf-8")).hexdigest().upper()

@pytest.fixture
def auth_headers(auth_keys):
    """Factory fixture to generate headers for a specific payload."""
    secret_key, access_key = auth_keys

    def _create_headers(payload: Dict) -> Dict:
        timestamp = str(int(time.time() * 1000))
        body_string = json.dumps(payload, separators=(',', ':'))
        signature = calculate_signature(body_string, secret_key, timestamp)
        
        return {
            "Content-Type": "application/json",
            "X-Timestamp": timestamp,
            "X-Sign": signature,
            "X-Key": access_key
        }
    return _create_headers
