# Testing Guide - BNMP Portal Scraper

This guide helps you verify that the BNMP portal scraper works correctly and debug authentication issues.

## Quick Start

### 1. Run Unit Tests
```bash
pytest tests/ -v -m "not integration and not browser"
```

### 2. Inspect Browser (Capture Real Request)
```bash
python scripts/inspect_browser.py
```

This opens a browser, waits for you to solve the captcha, and captures the actual API request details when you make a search. Results are saved to `browser_inspection.json`.

### 3. Compare Your Request with Browser Request
```bash
python scripts/compare_requests.py
```

This compares:
- Headers you're sending vs browser headers
- Cookies you're using vs browser cookies
- Identifies missing or different values

### 4. Test with Your Cookies
```bash
pytest tests/test_integration.py::TestIntegration::test_full_workflow_with_saved_cookies -v -s
```

## Debugging 401 Unauthorized Error

If you're getting a 401 error, follow these steps:

### Step 1: Verify Cookies Are Valid
Check if your `cookies.json` file exists and contains valid cookies:
```python
from bnmpy import load_cookies
cookies, fingerprint = load_cookies("cookies.json")
print(f"Cookies: {len(cookies)}")
print(f"Cookie names: {[c.get('name') for c in cookies]}")
```

### Step 2: Capture Browser Request
Run the browser inspector to see what the browser actually sends:
```bash
python scripts/inspect_browser.py
```

### Step 3: Compare Requests
Use the comparison tool to find differences:
```bash
python scripts/compare_requests.py
```

Look for:
- Missing headers (especially `Authorization`, `fingerprint`, etc.)
- Different header values
- Missing cookies
- Cookie value differences

### Step 4: Check Cookie Expiration
The `portalbnmp` cookie contains a JWT token. Check if it's expired:
```python
import json
import base64
from bnmpy import load_cookies

cookies, _ = load_cookies("cookies.json")
for cookie in cookies:
    if cookie.get('name') == 'portalbnmp':
        token = cookie.get('value', '')
        # JWT tokens have 3 parts separated by dots
        parts = token.split('.')
        if len(parts) == 3:
            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            payload += '=' * (4 - len(payload) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(payload))
            print(f"Token expires at: {decoded.get('exp')}")
            import time
            if decoded.get('exp', 0) < time.time():
                print("⚠ Token is expired!")
```

### Step 5: Get Fresh Session
If cookies are expired, get a new session:
```python
from bnmpy import get_session_with_playwright, save_cookies

cookies, fingerprint = get_session_with_playwright()
save_cookies(cookies, "cookies.json", fingerprint)
```

## Test Files

- `tests/test_session.py` - Session management tests
- `tests/test_api_client.py` - API client tests (includes integration test)
- `tests/test_integration.py` - End-to-end workflow tests
- `tests/test_browser_inspector.py` - Browser inspection tests

## Scripts

- `scripts/inspect_browser.py` - Capture browser API requests
- `scripts/compare_requests.py` - Compare our requests with browser requests
- `scripts/run_tests.py` - Run tests with different options

## Common Issues

### Issue: 401 Unauthorized
**Possible causes:**
1. Cookies expired
2. Missing fingerprint header
3. Missing or incorrect Authorization header
4. Cookie domain/path mismatch

**Solution:** Use browser inspector to capture working request and compare.

### Issue: Cookies Not Loading
**Check:**
- File exists and is valid JSON
- File format matches expected structure
- Cookie values are not empty

### Issue: Fingerprint Not Found
**Solution:** The fingerprint might be generated dynamically. Check browser inspection to see if it's in headers or needs to be extracted differently.

## Proving It Works

To prove the code works:

1. **Run browser inspector** and capture a successful API call
2. **Save the cookies** from that session
3. **Run integration test** with those cookies
4. **Verify response** is 200 with actual data

Example successful test output:
```
✓ API call successful!
  Response keys: ['content', 'totalElements', 'totalPages']
  Content items: 10
```

