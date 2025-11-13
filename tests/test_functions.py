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
    """Calculate signature for authentication"""
    string_to_checksum = body_string + secret_key + timestamp
    sha512 = hashlib.sha512()
    sha512.update(string_to_checksum.encode("utf-8"))
    return sha512.hexdigest().replace("-", "")


def test_talk_stream():
    """Test the /talk streaming endpoint"""
    print("Testing /talk streaming endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/talk"
    
    secret_key = os.getenv("ChatSecretKey", "test_secret_key")
    access_key = os.getenv("ChatAccessKey", "test_access_key")
    
    timestamp = str(int(time.time() * 1000))
    session_id = str(uuid.uuid4())
    trace_id = str(uuid.uuid4())
    
    payload = {
        "askText": "Hello, can you help me with the class?",
        "sessionId": session_id,
        "traceId": trace_id,
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
            json=payload,
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
    """Test the /welcome endpoint"""
    print("Testing /welcome endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/welcome"
    
    secret_key = os.getenv("ChatSecretKey", "test_secret_key")
    access_key = os.getenv("ChatAccessKey", "test_access_key")
    
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
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_goodbye():
    """Test the /goodbye endpoint"""
    print("Testing /goodbye endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/goodbye"
    
    secret_key = os.getenv("ChatSecretKey", "test_secret_key")
    access_key = os.getenv("ChatAccessKey", "test_access_key")
    
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
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


def test_recquestions():
    """Test the /recquestions endpoint"""
    print("Testing /recquestions endpoint...")
    
    base_url = os.getenv("API_URL", "https://your-api-gateway-url")
    endpoint = "/recquestions"
    
    secret_key = os.getenv("ChatSecretKey", "test_secret_key")
    access_key = os.getenv("ChatAccessKey", "test_access_key")
    
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
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")


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
        else:
            print("Usage: python test_functions.py [talk|welcome|goodbye|recquestions]")
    else:
        print("Running all function tests...")
        test_welcome()
        print("\n" + "="*50 + "\n")
        test_talk_stream()
        print("\n" + "="*50 + "\n")
        test_recquestions()
        print("\n" + "="*50 + "\n")
        test_goodbye()
