# Test Suite Summary

## Overview

A comprehensive test suite has been created to verify the BNMP portal scraper works correctly and debug authentication issues.

## Quick Test Commands

```bash
# Run all unit tests (fast, no API calls)
pytest tests/ -v -m "not integration and not browser"

# Test authentication with your cookies
python scripts/test_authentication.py

# Inspect browser to capture real API requests
python scripts/inspect_browser.py

# Compare your request with browser request
python scripts/compare_requests.py

# Run integration test
pytest tests/test_integration.py::TestIntegration::test_full_workflow_with_saved_cookies -v -s
```

## Test Structure

### Unit Tests (`tests/test_session.py`, `tests/test_api_client.py`)
- Test cookie save/load functionality
- Test API client initialization
- Test request structure
- **No API calls required** - fast and reliable

### Integration Tests (`tests/test_api_client.py`, `tests/test_integration.py`)
- Test with real cookies from `cookies.json`
- Make actual API calls
- Verify authentication works
- **Requires valid cookies** - may fail if cookies expired

### Browser Tests (`tests/test_browser_inspector.py`)
- Test browser inspection functionality
- **Requires manual browser interaction**

## Debugging 401 Error

### Step 1: Test Current Setup
```bash
python scripts/test_authentication.py
```

This will:
- Check if cookies exist and are valid
- Check if token is expired
- Make an API call
- Show detailed error if it fails

### Step 2: Capture Browser Request
```bash
python scripts/inspect_browser.py
```

This will:
- Open browser
- Wait for captcha solve
- Capture API request when you make a search
- Save fingerprint and request details

### Step 3: Compare Requests
```bash
python scripts/compare_requests.py
```

This will:
- Compare headers you send vs browser sends
- Compare cookies you use vs browser uses
- Show missing or different values

### Step 4: Fix Issues
Based on comparison results:
- Update headers if missing/different
- Get fresh cookies if expired
- Set fingerprint if missing
- Fix cookie domain/path if wrong

## Files Created

### Test Files
- `tests/__init__.py` - Test package init
- `tests/test_session.py` - Session management tests
- `tests/test_api_client.py` - API client tests (includes integration)
- `tests/test_integration.py` - End-to-end workflow tests
- `tests/test_browser_inspector.py` - Browser inspection tests
- `pytest.ini` - Pytest configuration

### Scripts
- `scripts/inspect_browser.py` - Capture browser API requests
- `scripts/compare_requests.py` - Compare requests
- `scripts/test_authentication.py` - Quick auth test
- `scripts/run_tests.py` - Test runner with options

### Documentation
- `TESTING_GUIDE.md` - Comprehensive testing guide
- `tests/README.md` - Test suite documentation

### Code
- `bnmpy/browser_inspector.py` - Browser inspection utilities

## Proving It Works

To prove the code works end-to-end:

1. **Get fresh session:**
   ```python
   from bnmpy import get_session_with_playwright, save_cookies
   cookies, fingerprint = get_session_with_playwright()
   save_cookies(cookies, "cookies.json", fingerprint)
   ```

2. **Run authentication test:**
   ```bash
   python scripts/test_authentication.py
   ```

3. **Expected output:**
   ```
   ✓ SUCCESS! API call worked!
   Response data:
     Keys: ['content', 'totalElements', 'totalPages']
     Content items: 10
   ```

4. **Run integration test:**
   ```bash
   pytest tests/test_integration.py::TestIntegration::test_full_workflow_with_saved_cookies -v -s
   ```

5. **Expected result:** Test passes with 200 status code

## Next Steps

If you're still getting 401 errors:

1. Run `python scripts/inspect_browser.py` to capture what browser sends
2. Run `python scripts/compare_requests.py` to see differences
3. Check if fingerprint is being captured correctly
4. Verify cookies are not expired
5. Check if any additional headers are needed

The test suite will help identify exactly what's missing or different between your requests and the browser's working requests.

