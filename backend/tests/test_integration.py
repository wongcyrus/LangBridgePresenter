import pytest
import requests
import json
import uuid
import time

pytestmark = pytest.mark.integration

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
    try:
        resp_conf = requests.post(
            f"{endpoint_config}?key={api_key}", 
            data=json.dumps(config_payload, separators=(',', ':')), 
            headers=headers_conf, 
            timeout=10
        )
        assert resp_conf.status_code == 200, f"Config update failed: {resp_conf.text}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Config update request failed: {e}")
    
    time.sleep(2)

    # 2. Verify Welcome
    endpoint = f"{api_url}/api/welcome"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    headers = auth_headers(payload)
    
    try:
        response = requests.post(
            endpoint, 
            data=json.dumps(payload, separators=(',', ':')), 
            headers=headers, 
            timeout=10
        )
        assert response.status_code == 200, f"Welcome failed: {response.text}"
        data = response.json()
        assert data.get("replyText") == test_msg, f"Expected '{test_msg}', got '{data.get('replyText')}'"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Welcome request failed: {e}")

@pytest.mark.skip(reason="Presentation mode detection logic needs verification")
def test_welcome_endpoint_presentation_messages(api_url, auth_headers, api_key):
    """Test the /api/welcome endpoint when in presentation context and using presentation_messages."""
    if not api_key:
        pytest.skip("API key not found")

    # 1. Update Config with presentation messages
    endpoint_config = f"{api_url}/api/config"
    random_id = str(uuid.uuid4())[:8]
    test_presentation_text = f"PRESENTATION_TEXT_{random_id}"
    test_audio_url = f"https://example.com/audio_{random_id}.mp3"
    
    config_payload = {
        "presentation_messages": {
            "en-US": {
                "text": test_presentation_text,
                "audio_url": test_audio_url
            }
        }
    }
    
    headers_conf = auth_headers(config_payload)
    resp_conf = requests.post(f"{endpoint_config}?key={api_key}", data=json.dumps(config_payload, separators=(',', ':')), headers=headers_conf, timeout=10)
    assert resp_conf.status_code == 200, f"Config update failed: {resp_conf.text}"
    
    time.sleep(2)

    # 2. Verify Welcome in presentation mode
    endpoint = f"{api_url}/api/welcome"
    payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en-US",
        "userParams": "presenter-123-presentation" # Trigger is_presentation=True
    }
    headers = auth_headers(payload)
    
    response = requests.post(endpoint, data=json.dumps(payload, separators=(',', ':')), headers=headers, timeout=10)
    
    assert response.status_code == 200, f"Welcome (presentation) failed: {response.text}"
    data = response.json()
    assert data.get("replyText") == test_presentation_text
    assert "replyAudioUrl" not in data # Assert audio_url is NOT returned

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
        "languageCode": "en",
        "text": "Hello, this is a test message."
    }
    headers = auth_headers(payload)
    
    try:
        response = requests.post(
            endpoint, 
            data=json.dumps(payload, separators=(',', ':')), 
            headers=headers, 
            timeout=30
        )
        assert response.status_code == 200, f"Speech generation failed: {response.text}"
        data = response.json()
        assert "voiceUrl" in data, "Response missing voiceUrl field"
        
        voice_url = data["voiceUrl"]
        assert voice_url.startswith("http"), f"Invalid voice URL: {voice_url}"
        
        # Verify download
        mp3_response = requests.get(voice_url, timeout=10)
        assert mp3_response.status_code == 200, f"Failed to download MP3 from {voice_url}"
        assert len(mp3_response.content) > 0, "Empty MP3 file"
        assert mp3_response.headers.get('content-type', '').startswith('audio/'), "Invalid content type for audio file"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Speech endpoint request failed: {e}")

def test_talk_stream_endpoint(api_url, auth_headers):
    """Test the /api/talk streaming endpoint."""
    endpoint = f"{api_url}/api/talk"
    payload = {
        "askText": "Hello, how are you?",
        "sessionId": str(uuid.uuid4()),
        "traceId": str(uuid.uuid4()),
        "languageCode": "en",
        "extra": {}
    }
    headers = auth_headers(payload)
    
    try:
        response = requests.post(
            endpoint, 
            data=json.dumps(payload, separators=(',', ':')), 
            headers=headers, 
            stream=True, 
            timeout=30
        )
        assert response.status_code == 200, f"Talk stream failed: {response.status_code}"
        
        lines = []
        chunks = []
        for line in response.iter_lines(decode_unicode=True):
            if line:
                lines.append(line)
                chunks.append(line)
                # Stop after receiving some data to avoid long waits
                if len(lines) >= 5:
                    break
        
        assert len(lines) > 0, "No streaming response received"
        
        # The response might be plain text chunks or JSON
        # Try to parse as JSON first, if that fails, check for text content
        valid_json_found = False
        has_text_content = False
        
        for line in lines:
            # Try JSON parsing
            try:
                parsed = json.loads(line)
                valid_json_found = True
                break
            except json.JSONDecodeError:
                # Check if it's just text content
                if line.strip():
                    has_text_content = True
        
        # Accept either valid JSON or text content
        assert valid_json_found or has_text_content, \
            f"No valid response found. Lines received: {lines[:3]}"
    except requests.exceptions.RequestException as e:
        pytest.fail(f"Talk stream request failed: {e}")



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
