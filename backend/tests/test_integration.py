import pytest
import requests
import json
import uuid
import time

def test_welcome_endpoint(api_url, auth_headers, api_key):
    """Test the /api/welcome endpoint with dynamic config update."""
    if not api_key:
        pytest.skip("API key not found")

    # 1. Update Config
    endpoint_config = f"{api_url}/api/config"
    random_id = str(uuid.uuid4())[:8]
    test_msg = f"WELCOME_{random_id}"
    
    config_payload = {
        "welcome_messages": {"en": test_msg, "zh": f"CN_{test_msg}"}
    }
    
    headers_conf = auth_headers(config_payload)
    resp_conf = requests.post(f"{endpoint_config}?key={api_key}", data=json.dumps(config_payload, separators=(',', ':')), headers=headers_conf, timeout=10)
    assert resp_conf.status_code == 200, f"Config update failed: {resp_conf.text}"
    
    time.sleep(2)

    # 2. Verify Welcome
    endpoint = f"{api_url}/api/welcome"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    headers = auth_headers(payload)
    
    response = requests.post(endpoint, data=json.dumps(payload, separators=(',', ':')), headers=headers, timeout=10)
    
    assert response.status_code == 200, f"Welcome failed: {response.text}"
    data = response.json()
    assert data.get("replyText") == test_msg

def test_goodbye_endpoint(api_url, auth_headers, api_key):
    """Test the /api/goodbye endpoint with dynamic config update."""
    if not api_key:
        pytest.skip("API key not found")

    # 1. Update Config
    endpoint_config = f"{api_url}/api/config"
    random_id = str(uuid.uuid4())[:8]
    test_msg = f"GOODBYE_{random_id}"
    
    config_payload = {
        "goodbye_messages": {"en": test_msg, "zh": f"CN_{test_msg}"}
    }
    
    headers_conf = auth_headers(config_payload)
    resp_conf = requests.post(f"{endpoint_config}?key={api_key}", data=json.dumps(config_payload, separators=(',', ':')), headers=headers_conf, timeout=10)
    assert resp_conf.status_code == 200, f"Config update failed: {resp_conf.text}"
    
    time.sleep(2)

    # 2. Verify Goodbye
    endpoint = f"{api_url}/api/goodbye"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    headers = auth_headers(payload)
    
    response = requests.post(endpoint, data=json.dumps(payload, separators=(',', ':')), headers=headers, timeout=10)
    
    assert response.status_code == 200, f"Goodbye failed: {response.text}"
    data = response.json()
    assert data.get("replyText") == test_msg

def test_recquestions_endpoint(api_url, auth_headers, api_key):
    """Test the /api/recquestions endpoint with dynamic config update."""
    if not api_key:
        pytest.skip("API key not found")

    # 1. Update Config
    endpoint_config = f"{api_url}/api/config"
    random_id = str(uuid.uuid4())[:8]
    q1 = f"Q1_{random_id}"
    q2 = f"Q2_{random_id}"
    
    config_payload = {
        "recommended_questions": {"en": [q1, q2], "zh": ["Q3", "Q4"]}
    }
    
    headers_conf = auth_headers(config_payload)
    resp_conf = requests.post(f"{endpoint_config}?key={api_key}", data=json.dumps(config_payload, separators=(',', ':')), headers=headers_conf, timeout=10)
    assert resp_conf.status_code == 200, f"Config update failed: {resp_conf.text}"
    
    time.sleep(2)

    # 2. Verify RecQuestions
    endpoint = f"{api_url}/api/recquestions"
    payload = {
        "traceId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    headers = auth_headers(payload)
    
    response = requests.post(endpoint, data=json.dumps(payload, separators=(',', ':')), headers=headers, timeout=10)
    
    assert response.status_code == 200, f"Recquestions failed: {response.text}"
    data = response.json()
    assert "data" in data
    assert isinstance(data["data"], list)
    assert q1 in data["data"]
    assert q2 in data["data"]

def test_speech_endpoint(api_url, auth_headers):
    """Test the /api/speech endpoint and verify MP3 download."""
    endpoint = f"{api_url}/api/speech"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    headers = auth_headers(payload)
    
    response = requests.post(endpoint, data=json.dumps(payload, separators=(',', ':')), headers=headers, timeout=30)
    
    assert response.status_code == 200, f"Speech generation failed: {response.text}"
    data = response.json()
    assert "voiceUrl" in data
    
    voice_url = data["voiceUrl"]
    assert voice_url.startswith("http"), "Invalid voice URL"
    
    # Verify download
    mp3_response = requests.get(voice_url, timeout=10)
    assert mp3_response.status_code == 200, "Failed to download generated MP3"
    assert len(mp3_response.content) > 0, "Empty MP3 file"

def test_talk_stream_endpoint(api_url, auth_headers):
    """Test the /api/talk streaming endpoint."""
    endpoint = f"{api_url}/api/talk"
    payload = {
        "askText": "Hello",
        "sessionId": str(uuid.uuid4()),
        "traceId": str(uuid.uuid4()),
        "languageCode": "en",
        "extra": {}
    }
    headers = auth_headers(payload)
    
    response = requests.post(endpoint, data=json.dumps(payload, separators=(',', ':')), headers=headers, stream=True, timeout=30)
    
    assert response.status_code == 200, f"Talk stream failed: {response.text}"
    
    lines = list(response.iter_lines(decode_unicode=True))
    assert len(lines) > 0, "No streaming response received"



def test_config_broadcast_error_simulation(api_url, auth_headers, api_key):
    """Test config update with 'generate_presentation' flag."""
    if not api_key:
        pytest.skip("API key not found")
        
    endpoint = f"{api_url}/api/config"
    
    payload = {
        "generate_presentation": True,
        "languages": ["en"],
        "context": "Test Context",
        "presentation_messages": {},
        "welcome_messages": {"en": "Welcome"},
        "goodbye_messages": {"en": "Bye"}
    }
    
    headers = auth_headers(payload)
    response = requests.post(f"{endpoint}?key={api_key}", data=json.dumps(payload, separators=(',', ':')), headers=headers, timeout=60)
    
    # We accept 200 (success) or specific error codes if backend handles them gracefully
    # The original test accepted 200 even if broadcast failed internally
    assert response.status_code == 200, f"Config generation request failed: {response.text}"
    assert response.json().get("success") is True
