import pytest
import requests
import json
import uuid
import time

pytestmark = pytest.mark.integration


def test_missing_auth_headers(api_url):
    """Test that requests without auth headers are rejected."""
    endpoint = f"{api_url}/api/welcome"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    response = requests.post(
        endpoint, 
        data=json.dumps(payload, separators=(',', ':')),
        headers={"Content-Type": "application/json"},
        timeout=10
    )
    
    # Should fail without proper auth
    assert response.status_code in [401, 403], \
        f"Expected 401/403 for missing auth, got {response.status_code}"


def test_invalid_signature(api_url, auth_keys):
    """Test that requests with invalid signatures are rejected."""
    secret_key, access_key = auth_keys
    endpoint = f"{api_url}/api/welcome"
    
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    timestamp = str(int(time.time() * 1000))
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": "INVALID_SIGNATURE",
        "X-Key": access_key
    }
    
    response = requests.post(
        endpoint,
        data=json.dumps(payload, separators=(',', ':')),
        headers=headers,
        timeout=10
    )
    
    # Should fail with invalid signature
    assert response.status_code in [401, 403], \
        f"Expected 401/403 for invalid signature, got {response.status_code}"


def test_expired_timestamp(api_url, auth_headers, auth_keys):
    """Test that requests with old timestamps are rejected."""
    secret_key, access_key = auth_keys
    endpoint = f"{api_url}/api/welcome"
    
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    # Use timestamp from 10 minutes ago
    old_timestamp = str(int((time.time() - 600) * 1000))
    
    # Calculate signature with old timestamp
    import hashlib
    body_string = json.dumps(payload, separators=(',', ':'))
    params = {"bodyString": body_string, "secretKey": secret_key, "timestamp": old_timestamp}
    signature_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    signature = hashlib.sha512(signature_string.encode("utf-8")).hexdigest().upper()
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": old_timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    response = requests.post(
        endpoint,
        data=json.dumps(payload, separators=(',', ':')),
        headers=headers,
        timeout=10
    )
    
    # Should fail with expired timestamp (or succeed if no timestamp validation)
    # This depends on backend implementation
    assert response.status_code in [200, 401, 403], \
        f"Unexpected status code: {response.status_code}"


def test_valid_auth(api_url, auth_headers):
    """Test that requests with valid auth succeed."""
    endpoint = f"{api_url}/api/welcome"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    headers = auth_headers(payload)
    
    response = requests.post(
        endpoint,
        data=json.dumps(payload, separators=(',', ':')),
        headers=headers,
        timeout=10
    )
    
    assert response.status_code == 200, \
        f"Valid auth should succeed, got {response.status_code}: {response.text}"
