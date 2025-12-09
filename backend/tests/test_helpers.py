"""Helper utilities for tests."""
import json
import hashlib
import time
from typing import Dict


def create_test_payload(language_code: str = "en", **kwargs) -> Dict:
    """Create a standard test payload with common fields."""
    import uuid
    
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": language_code
    }
    payload.update(kwargs)
    return payload


def calculate_signature_v2(body_string: str, secret_key: str, timestamp: str) -> str:
    """Calculate signature for authentication using v2 algorithm."""
    params = {
        "bodyString": body_string,
        "secretKey": secret_key,
        "timestamp": timestamp
    }
    signature_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hashlib.sha512(signature_string.encode("utf-8")).hexdigest().upper()


def create_auth_headers(payload: Dict, secret_key: str, access_key: str) -> Dict:
    """Create authentication headers for a payload."""
    timestamp = str(int(time.time() * 1000))
    body_string = json.dumps(payload, separators=(',', ':'))
    signature = calculate_signature_v2(body_string, secret_key, timestamp)
    
    return {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }


def assert_valid_response(response, expected_fields: list = None):
    """Assert that a response is valid and contains expected fields."""
    assert response.status_code == 200, \
        f"Expected 200, got {response.status_code}: {response.text}"
    
    try:
        data = response.json()
    except json.JSONDecodeError:
        raise AssertionError(f"Response is not valid JSON: {response.text}")
    
    if expected_fields:
        for field in expected_fields:
            assert field in data, f"Response missing expected field: {field}"
    
    return data


def wait_for_config_propagation(seconds: int = 2):
    """Wait for config changes to propagate through the system."""
    time.sleep(seconds)
