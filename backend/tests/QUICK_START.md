# Quick Start Guide

## First Time Setup (5 minutes)

1. **Copy environment template:**
   ```bash
   cd backend/tests
   cp .env.test.template .env.test
   ```

2. **Edit `.env.test` with your credentials:**
   ```bash
   nano .env.test  # or use your favorite editor
   ```
   
   Add:
   ```
   API_URL=https://your-gateway-url.gateway.dev
   XIAOICE_CHAT_SECRET_KEY=your_secret_key
   XIAOICE_CHAT_ACCESS_KEY=your_access_key
   ```

3. **Run tests:**
   ```bash
   ./run_tests.sh
   ```

## Common Commands

### Run all tests
```bash
./run_tests.sh
```

### Run only fast tests (skip slow admin tools tests)
```bash
./run_tests.sh -m "not slow"
```

### Run only integration tests
```bash
./run_tests.sh -m integration
```

### Run only unit tests
```bash
./run_tests.sh -m unit
```

### Run specific test file
```bash
./run_tests.sh test_auth.py
```

### Run specific test
```bash
./run_tests.sh test_integration.py::test_welcome_endpoint
```

### Run with detailed output
```bash
./run_tests.sh -vv
```

### Run and stop on first failure
```bash
./run_tests.sh -x
```

## Test Markers

Tests are organized with markers for easy filtering:

- `@pytest.mark.integration` - Tests that hit the deployed API
- `@pytest.mark.unit` - Tests that run locally with mocks
- `@pytest.mark.slow` - Tests that take >5 seconds
- `@pytest.mark.admin` - Tests for admin tools

## Troubleshooting

### "API_URL not set"
→ Create `.env.test` file with your API URL

### "Auth keys not found"
→ Add `XIAOICE_CHAT_SECRET_KEY` and `XIAOICE_CHAT_ACCESS_KEY` to `.env.test`

### "API key not found" (for config tests)
→ Generate and save `backend/admin_tools/api_key.json`:
```bash
cd ../admin_tools
python create_api_key.py live-sync "Live Sync Tester" \
  --project-id langbridge-presenter-d2 \
  --api-service langbridgeapi-1uv4f2dvtlkj9.apigateway.langbridge-presenter-d2.cloud.goog \
  --database langbridge
cp "$(ls -1t api_key_*.json | head -n 1)" api_key.json
```
Or export `API_GATEWAY_KEY` directly when running scripts/tests that call `/api/config`.

### Tests timeout
→ Check your network connection and API availability

### Import errors
→ Run `./run_tests.sh` which handles dependencies automatically

## What Gets Tested

✅ Authentication and authorization  
✅ Welcome/goodbye messages  
✅ Recommended questions  
✅ Text-to-speech generation  
✅ Streaming chat responses  
✅ Configuration updates  
✅ Admin tools (export/import cache)  
✅ Config function logic  

## Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [../docs/](../../docs/) for architecture details
- See [test_helpers.py](test_helpers.py) for reusable utilities
