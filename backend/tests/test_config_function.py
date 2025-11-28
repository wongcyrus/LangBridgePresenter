import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import json

# 1. Mock functions_framework before importing main
mock_ff = MagicMock()
def http_decorator(func):
    return func
mock_ff.http = http_decorator
sys.modules['functions_framework'] = mock_ff

# 2. Add function path to sys.path
# Assuming we run pytest from root or backend/
# File is in backend/tests/test_config_function.py
# Function is in backend/functions/config/main.py
func_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../functions/config'))
sys.path.append(func_path)

# 3. Import the function
# We need to mock google.cloud.firestore inside the module when it runs, 
# or just rely on patch in tests if the module imports it at top level but doesn't use it immediately.
# main.py does `from google.cloud import firestore`. 
# We should mock google.cloud to avoid import errors if not installed in test env.
mock_google = MagicMock()
sys.modules['google'] = mock_google
sys.modules['google.cloud'] = mock_google
sys.modules['google.cloud.firestore'] = MagicMock()

# Also mock firestore_utils
sys.modules['firestore_utils'] = MagicMock()

try:
    from main import config
except ImportError as e:
    # If verify fails because of other imports
    print(f"Import failed: {e}")
    raise

class TestConfigFunction(unittest.TestCase):
    def setUp(self):
        self.mock_request = MagicMock()
        self.mock_request.method = 'POST'

    @patch('main.firestore.Client')
    def test_populate_messages_from_latest_languages(self, mock_firestore_client):
        # Setup
        latest_languages = {
            "en": {"text": "Hello English"},
            "zh": {"text": "Hello Chinese"}
        }
        request_json = {
            "presentation_messages": {}, # Empty
            "latest_languages": latest_languages,
            "context": "Fallback Context"
        }
        self.mock_request.get_json.return_value = request_json
        
        # Mock Firestore
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Execute
        response = config(self.mock_request)
        
        # Verify response
        # response is (body, code, headers)
        self.assertEqual(response[1], 200)
        
        # Verify call to firestore set
        # We expect config_data['presentation_messages'] to be populated from latest_languages
        # The call is doc_ref.set(config_data)
        args, _ = mock_doc_ref.set.call_args
        config_data = args[0]
        
        expected_messages = {
            "en": "Hello English",
            "zh": "Hello Chinese"
        }
        self.assertEqual(config_data['presentation_messages'], expected_messages)

    @patch('main.firestore.Client')
    def test_fallback_to_context(self, mock_firestore_client):
        # Setup
        request_json = {
            "presentation_messages": {},
            "latest_languages": {}, # Empty
            "context": "Fallback Context"
        }
        self.mock_request.get_json.return_value = request_json
        
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Execute
        config(self.mock_request)
        
        # Verify
        args, _ = mock_doc_ref.set.call_args
        config_data = args[0]
        self.assertEqual(config_data['presentation_messages'], {"en": "Fallback Context"})

    @patch('main.firestore.Client')
    def test_existing_presentation_messages_not_overwritten(self, mock_firestore_client):
        # Setup
        latest_languages = {
            "en": {"text": "Hello English"},
        }
        request_json = {
            "presentation_messages": {"fr": "Bonjour"},
            "latest_languages": latest_languages,
            "context": "Fallback Context"
        }
        self.mock_request.get_json.return_value = request_json
        
        mock_db = MagicMock()
        mock_firestore_client.return_value = mock_db
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref
        
        # Execute
        config(self.mock_request)
        
        # Verify
        args, _ = mock_doc_ref.set.call_args
        config_data = args[0]
        # Should stay as provided
        self.assertEqual(config_data['presentation_messages'], {"fr": "Bonjour"})
