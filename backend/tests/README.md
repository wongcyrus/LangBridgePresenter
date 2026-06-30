# LangBridge Backend Tests

Comprehensive test suite for the LangBridge backend API and admin tools.

## Test Structure

```
backend/tests/
├── conftest.py              # Pytest fixtures and configuration
├── pytest.ini               # Pytest settings
├── requirements.txt         # Test dependencies
├── run_tests.sh            # Test runner script
├── .env.test.template      # Template for environment variables
├── .env.test               # Your local environment (gitignored)
├── test_integration.py     # API endpoint integration tests
├── test_admin_tools.py     # Admin tools integration tests
├── test_config_function.py # Config function unit tests
├── test_auth.py            # Authentication tests
├── test_helpers.py         # Test utility functions
├── test_voice_chat_admin_function.py # Voice-chat admin API unit tests
└── test_manage_admin_users.py        # Admin user script unit tests
```

## Setup

1. **Create environment file:**
   ```bash
   cp .env.test.template .env.test
   ```

2. **Edit `.env.test` with your values:**
   ```bash
   API_URL=https://your-api-url.cloudfunctions.net/api
   XIAOICE_CHAT_SECRET_KEY=your_secret_key_here
   XIAOICE_CHAT_ACCESS_KEY=your_access_key_here
   ```

3. **Run tests:**
   ```bash
   ./run_tests.sh
   ```

## Running Tests

### Run all tests
```bash
./run_tests.sh
```

### Run specific test file
```bash
./run_tests.sh test_integration.py
```

### Run specific test function
```bash
./run_tests.sh test_integration.py::test_welcome_endpoint
```

### Run with verbose output
```bash
./run_tests.sh -vv
```

### Run with coverage
```bash
pytest --cov=../functions --cov-report=html
```

## Test Categories

### Integration Tests (`test_integration.py`)
Tests the deployed API endpoints:
- `/api/welcome` - Welcome message endpoint
- `/api/goodbye` - Goodbye message endpoint
- `/api/recquestions` - Recommended questions
- `/api/speech` - Text-to-speech generation
- `/api/talk` - Streaming chat endpoint
- `/api/config` - Configuration updates

### Admin Tools Tests (`test_admin_tools.py`)
Tests the admin tools functionality:
- Export cache to Excel
- Import cache from Excel
- Cache modification workflow
- Firestore integration

### Config Function Tests (`test_config_function.py`)
Unit tests for the config Cloud Function:
- Message population logic
- Fallback behavior
- Configuration merging

### Auth Tests (`test_auth.py`)
Tests authentication and authorization:
- Missing auth headers
- Invalid signatures
- Expired timestamps
- Valid authentication

### Voice Chat Admin Tests (`test_voice_chat_admin_function.py`)
Unit tests for the voice-chat admin Cloud Function:
- unauthenticated request rejection
- usage dashboard response formatting
- limit update request handling
- Firestore-backed admin access check

### Admin User Script Tests (`test_manage_admin_users.py`)
Unit tests for `manage_admin_users.py`:
- admin doc id normalization
- grant/revoke Firestore writes

## Fixtures

### `api_url`
Returns the base API URL from `.env.test`.

### `auth_keys`
Returns tuple of (secret_key, access_key) from environment.

### `auth_headers`
Factory fixture that generates authentication headers for a payload.

### `api_key`
Loads the admin API key from `backend/admin_tools/api_key.json`.

### `db`
Returns a Firestore client connected to the project.

## Writing New Tests

1. **Use fixtures for common setup:**
   ```python
   def test_my_endpoint(api_url, auth_headers):
       endpoint = f"{api_url}/api/myendpoint"
       payload = {"key": "value"}
       headers = auth_headers(payload)
       response = requests.post(endpoint, json=payload, headers=headers)
       assert response.status_code == 200
   ```

2. **Use helper functions:**
   ```python
   from test_helpers import create_test_payload, assert_valid_response
   
   def test_with_helpers(api_url, auth_headers):
       payload = create_test_payload(language_code="en", extra_field="value")
       headers = auth_headers(payload)
       response = requests.post(f"{api_url}/api/endpoint", json=payload, headers=headers)
       data = assert_valid_response(response, expected_fields=["replyText"])
   ```

3. **Handle errors gracefully:**
   ```python
   try:
       response = requests.post(endpoint, json=payload, headers=headers, timeout=10)
       assert response.status_code == 200
   except requests.exceptions.RequestException as e:
       pytest.fail(f"Request failed: {e}")
   ```

## Troubleshooting

### Tests skip with "API_URL not set"
- Ensure `.env.test` exists and contains `API_URL`
- Check that the URL is correct and accessible

### Tests fail with authentication errors
- Verify `XIAOICE_CHAT_SECRET_KEY` and `XIAOICE_CHAT_ACCESS_KEY` are correct
- Check that the keys match the deployed backend configuration

### Admin tools tests fail
- Ensure you have proper Firestore credentials
- Check that `backend/admin_tools/config.py` has correct project settings
- Verify you have write permissions to the Firestore database

### Import errors
- Run `./run_tests.sh` which sets up the virtual environment
- Or manually: `pip install -r requirements.txt`

## CI/CD Integration

To run tests in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Run Backend Tests
  env:
    API_URL: ${{ secrets.API_URL }}
    XIAOICE_CHAT_SECRET_KEY: ${{ secrets.SECRET_KEY }}
    XIAOICE_CHAT_ACCESS_KEY: ${{ secrets.ACCESS_KEY }}
  run: |
    cd backend/tests
    pip install -r requirements.txt
    pytest -v --tb=short
```

## Best Practices

1. **Use unique IDs** - Generate UUIDs for test data to avoid collisions
2. **Clean up resources** - Use fixtures with teardown to clean up test data
3. **Test isolation** - Each test should be independent
4. **Meaningful assertions** - Include descriptive error messages
5. **Timeout requests** - Always set timeouts on HTTP requests
6. **Handle exceptions** - Catch and report network/API errors clearly
