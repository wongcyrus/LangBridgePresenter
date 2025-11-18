#!/usr/bin/env python3
"""
Test scripts for Xiaoice Class Assistant Cloud Functions
"""

import hashlib
import json
import os
import sys
import time
import uuid
import requests


def calculate_signature(body_string: str, secret_key: str, timestamp: str) -> str:
    """Calculate signature for authentication using v2 algorithm"""
    params = {"bodyString": body_string, "secretKey": secret_key, "timestamp": timestamp}
    signature_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
    return hashlib.sha512(signature_string.encode("utf-8")).hexdigest().upper()


def get_auth_keys():
    """Return (secret_key, access_key) from env with sensible fallbacks.

    Prefers camelCase variables exported by run_tests.sh, and falls back to
    CDKTF-style uppercase keys or test defaults.
    """
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


def test_talk_stream():
    """Test the /api/talk streaming endpoint"""
    print("Testing /api/talk streaming endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/api/talk"
    
    secret_key, access_key = get_auth_keys()
    
    timestamp = str(int(time.time() * 1000))
    session_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    payload = {
        "askText": "Hello, can you help me with the class?",
        "sessionId": session_id,
        "traceId": trace_id,
        "languageCode": "en",
        "extra": {}
    }
    
    body_string = json.dumps(payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            data=body_string,
            headers=headers,
            stream=True,
            timeout=30
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            for line in response.iter_lines(decode_unicode=True):
                if line:
                    print(f"Received: {line}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_welcome():
    """Test the /api/welcome endpoint"""
    print("Testing /api/welcome endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/api/welcome"
    
    secret_key, access_key = get_auth_keys()
    
    timestamp = str(int(time.time() * 1000))
    session_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    payload = {
        "traceId": trace_id,
        "sessionId": session_id,
        "languageCode": "en"
    }
    
    body_string = json.dumps(payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_goodbye():
    """Test the /api/goodbye endpoint"""
    print("Testing /api/goodbye endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/api/goodbye"
    
    secret_key, access_key = get_auth_keys()
    
    timestamp = str(int(time.time() * 1000))
    session_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    payload = {
        "traceId": trace_id,
        "sessionId": session_id,
        "languageCode": "en"
    }
    
    body_string = json.dumps(payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            data=body_string,  # Use data instead of json
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_recquestions():
    """Test the /api/recquestions endpoint"""
    print("Testing /api/recquestions endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/api/recquestions"
    
    secret_key, access_key = get_auth_keys()
    
    timestamp = str(int(time.time() * 1000))
    trace_id = str(uuid.uuid4())
    
    payload = {
        "traceId": trace_id,
        "languageCode": "en"
    }
    
    body_string = json.dumps(payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    try:
        response = requests.post(
            f"{base_url}{endpoint}",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_config():
    """Test the /api/config endpoint"""
    print("Testing /api/config endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/api/config"
    
    # Read API key from api_key.json
    api_key_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "admin_tools",
        "api_key.json"
    )
    
    try:
        with open(api_key_path, 'r') as f:
            api_key_data = json.load(f)
            api_key = api_key_data.get("key_string")
            if not api_key:
                print(f"❌ No key_string found in {api_key_path}")
                return
            print(f"✅ Loaded API key from {api_key_path}")
    except FileNotFoundError:
        print(f"❌ API key file not found: {api_key_path}")
        return
    except Exception as e:
        print(f"❌ Error reading API key: {e}")
        return
    
    payload = {
        "presentation_messages": {
            "en": "Welcome to today's presentation!",
            "zh": "欢迎参加今天的演示！"
        },
        "welcome_messages": {
            "en": "Hello! Welcome to our updated service!",
            "zh": "您好！欢迎使用我们更新的服务！"
        },
        "goodbye_messages": {
            "en": "Thank you for using our service! Goodbye!",
            "zh": "感谢您使用我们的服务！再见！"
        },
        "recommended_questions": {
            "en": [
                "How can I get started?",
                "What features are available?",
                "Can you help me with configuration?"
            ],
            "zh": [
                "我该如何开始？",
                "有哪些功能可用？",
                "您能帮我配置吗？"
            ]
        },
        "talk_responses": {
            "en": "I understand your question. Let me provide you with detailed assistance.",
            "zh": "我理解您的问题。让我为您提供详细的帮助。"
        }
    }
    
    body_string = json.dumps(payload, separators=(',', ':'))
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            f"{base_url}{endpoint}?key={api_key}",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_config_generate_presentation():
    """Test config endpoint with agent-generated presentation messages"""
    print("Testing config with agent-generated presentation messages...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/api/config"
    secret_key, access_key = get_auth_keys()
    
    # Read API key from api_key.json
    api_key_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "admin_tools",
        "api_key.json"
    )
    
    try:
        with open(api_key_path, 'r') as f:
            api_key_data = json.load(f)
            api_key = api_key_data.get("key_string")
            if not api_key:
                print(f"❌ No key_string found in {api_key_path}")
                return
            print(f"✅ Loaded API key from {api_key_path}")
    except FileNotFoundError:
        print(f"❌ API key file not found: {api_key_path}")
        return
    except Exception as e:
        print(f"❌ Error reading API key: {e}")
        return
    
    payload = {
        "generate_presentation": True,
        "languages": ["en", "zh"],
        "context": "quarterly business review",
        "presentation_messages": {},
        "welcome_messages": {
            "en": "Welcome!",
            "zh": "欢迎！"
        },
        "goodbye_messages": {
            "en": "Goodbye!",
            "zh": "再见！"
        }
    }
    
    body_string = json.dumps(payload, separators=(',', ':'))
    timestamp = str(int(time.time() * 1000))
    signature = calculate_signature(body_string, secret_key, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    try:
        print("Sending request to generate presentation messages...")
        response = requests.post(
            f"{base_url}{endpoint}?key={api_key}",
            data=body_string,
            headers=headers,
            timeout=60
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Config updated successfully with generated messages")
        else:
            print(f"❌ Config update failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")


def test_config_and_verify_all():
    """Test config update with random values and verify all APIs return them"""
    print("Testing config update and verification...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    secret_key, access_key = get_auth_keys()
    
    # Read API key from api_key.json
    api_key_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "admin_tools",
        "api_key.json"
    )
    
    try:
        with open(api_key_path, 'r') as f:
            api_key_data = json.load(f)
            api_key = api_key_data.get("key_string")
            if not api_key:
                print(f"❌ No key_string found in {api_key_path}")
                return
            print(f"✅ Loaded API key from {api_key_path}")
    except FileNotFoundError:
        print(f"❌ API key file not found: {api_key_path}")
        return
    except Exception as e:
        print(f"❌ Error reading API key: {e}")
        return
    
    # Generate random test values
    random_id = str(uuid.uuid4())[:8]
    test_presentation = f"RANDOM_PRESENTATION_{random_id}"
    test_welcome = f"RANDOM_WELCOME_{random_id}"
    test_goodbye = f"RANDOM_GOODBYE_{random_id}"
    test_question = f"RANDOM_QUESTION_{random_id}"
    test_talk = f"RANDOM_TALK_{random_id}"
    
    print(f"Using random test ID: {random_id}")
    
    # Step 1: Update configuration with random values
    print("Step 1: Updating configuration with random values...")
    
    config_payload = {
        "presentation_messages": {
            "en": test_presentation,
            "zh": f"中文_{test_presentation}"
        },
        "welcome_messages": {
            "en": test_welcome,
            "zh": f"中文_{test_welcome}"
        },
        "goodbye_messages": {
            "en": test_goodbye,
            "zh": f"中文_{test_goodbye}"
        },
        "recommended_questions": {
            "en": [test_question, "What else can you do?"],
            "zh": [f"中文_{test_question}", "你还能做什么？"]
        },
        "talk_responses": {
            "en": test_talk,
            "zh": f"中文_{test_talk}"
        }
    }
    
    body_string = json.dumps(config_payload, separators=(',', ':'))
    timestamp = str(int(time.time() * 1000))
    signature = calculate_signature(body_string, secret_key, timestamp)
    
    headers = {
        "Content-Type": "application/json",
        "X-Timestamp": timestamp,
        "X-Sign": signature,
        "X-Key": access_key
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/config?key={api_key}",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        print(f"Config update status: {response.status_code}")
        print(f"Config response: {response.text}")
        
        if response.status_code != 200:
            print("❌ Config update failed, stopping test")
            return
        else:
            print("✅ Config updated successfully")
            
    except Exception as e:
        print(f"❌ Config update error: {e}")
        return
    
    # Wait for Firestore to update
    time.sleep(3)
    
    # Step 2: Test welcome endpoint
    print(f"\nStep 2: Testing welcome endpoint for '{test_welcome}'...")
    timestamp = str(int(time.time() * 1000))
    welcome_payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    body_string = json.dumps(welcome_payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    headers["X-Timestamp"] = timestamp
    headers["X-Sign"] = signature
    
    try:
        response = requests.post(
            f"{base_url}/api/welcome",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            welcome_data = response.json()
            reply_text = welcome_data.get("replyText", "")
            if test_welcome in reply_text:
                print(f"✅ Welcome message contains random value: {reply_text}")
            else:
                print(f"❌ Welcome message missing random value: {reply_text}")
        else:
            print(f"❌ Welcome error: {response.text}")
            
    except Exception as e:
        print(f"❌ Welcome test error: {e}")
    
    # Step 3: Test goodbye endpoint
    print(f"\nStep 3: Testing goodbye endpoint for '{test_goodbye}'...")
    timestamp = str(int(time.time() * 1000))
    goodbye_payload = {
        "traceId": str(uuid.uuid4()),
        "sessionId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    body_string = json.dumps(goodbye_payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    headers["X-Timestamp"] = timestamp
    headers["X-Sign"] = signature
    
    try:
        response = requests.post(
            f"{base_url}/api/goodbye",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            goodbye_data = response.json()
            reply_text = goodbye_data.get("replyText", "")
            if test_goodbye in reply_text:
                print(f"✅ Goodbye message contains random value: {reply_text}")
            else:
                print(f"❌ Goodbye message missing random value: {reply_text}")
        else:
            print(f"❌ Goodbye error: {response.text}")
            
    except Exception as e:
        print(f"❌ Goodbye test error: {e}")
    
    # Step 4: Test recquestions endpoint
    print(f"\nStep 4: Testing recquestions endpoint for '{test_question}'...")
    timestamp = str(int(time.time() * 1000))
    recq_payload = {
        "traceId": str(uuid.uuid4()),
        "languageCode": "en"
    }
    
    body_string = json.dumps(recq_payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    headers["X-Timestamp"] = timestamp
    headers["X-Sign"] = signature
    
    try:
        response = requests.post(
            f"{base_url}/api/recquestions",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            recq_data = response.json()
            questions = recq_data.get("data", [])
            if any(test_question in q for q in questions):
                print(f"✅ Recommended questions contain random value: {questions}")
            else:
                print(f"❌ Recommended questions missing random value: {questions}")
        else:
            print(f"❌ Recquestions error: {response.text}")
            
    except Exception as e:
        print(f"❌ Recquestions test error: {e}")
    
    # Step 5: Test talk endpoint
    print(f"\nStep 5: Testing talk endpoint for '{test_talk}'...")
    timestamp = str(int(time.time() * 1000))
    talk_payload = {
        "askText": "What is the current temperature of Hong Kong?",
        "sessionId": str(uuid.uuid4()),
        "traceId": str(uuid.uuid4()),
        "languageCode": "en",
        "extra": {}
    }
    
    body_string = json.dumps(talk_payload, separators=(',', ':'))
    signature = calculate_signature(body_string, secret_key, timestamp)
    headers["X-Timestamp"] = timestamp
    headers["X-Sign"] = signature
    
    try:
        response = requests.post(
            f"{base_url}/api/talk",
            data=body_string,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            content = response.text
            if test_talk in content:
                print(f"✅ Talk response contains random value")
            else:
                print(f"❌ Talk response missing random value")
            print(f"Talk response preview: {content[:200]}...")
        else:
            print(f"❌ Talk error: {response.text}")
            
    except Exception as e:
        print(f"❌ Talk test error: {e}")
    
    print(f"\n=== Test Summary for Random ID: {random_id} ===")
    print("Configuration update and verification test completed.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_type = sys.argv[1]
        if test_type == "talk":
            test_talk_stream()
        elif test_type == "welcome":
            test_welcome()
        elif test_type == "goodbye":
            test_goodbye()
        elif test_type == "recquestions":
            test_recquestions()
        elif test_type == "config":
            test_config()
        elif test_type == "generate":
            test_config_generate_presentation()
        elif test_type == "full":
            test_config_and_verify_all()
        else:
            print(
                "Usage: python test_functions.py "
                "[talk|welcome|goodbye|recquestions|config|generate|full]"
            )
    else:
        print("Running comprehensive test...")
        test_config_and_verify_all()
