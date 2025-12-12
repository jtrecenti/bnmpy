# Test Suite

This test suite helps verify that the BNMP portal scraper works correctly and debug authentication issues.

## Test Categories

### Unit Tests
Basic functionality tests that don't require API access:
```bash
pytest tests/ -v -m "not integration and not browser"
```

### Integration Tests
Tests that require real API access and valid cookies:
```bash
pytest tests/ -v -m integration
```

### Browser Tests
Tests that require manual browser interaction:
```bash
pytest tests/ -v -m browser -s
```

## Debugging Authentication Issues

### Step 1: Capture Browser Request
Use the browser inspector to capture what the browser actually sends:

```bash
python scripts/inspect_browser.py
```

This will:
1. Open a browser
2. Navigate to the portal
3. Wait for you to solve the captcha
4. Capture API request details when you make a search
5. Save results to `browser_inspection.json`

### Step 2: Compare Requests
Compare what we're sending vs what the browser sends:

```bash
python scripts/compare_requests.py
```

This will show:
- Headers we're sending vs browser headers
- Cookies we're using vs browser cookies
- Missing or different values

### Step 3: Run Integration Test
Test with your current cookies:

```bash
pytest tests/test_integration.py::TestIntegration::test_full_workflow_with_saved_cookies -v -s
```

## Running All Tests

```bash
# Unit tests only (default)
pytest tests/ -v

# All tests including integration
pytest tests/ -v -m "integration or not (integration or browser)"

# With coverage
pytest tests/ --cov=bnmpy --cov-report=html
```

