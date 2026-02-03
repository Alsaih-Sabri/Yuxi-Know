"""
Test script to debug MinerU Official API authentication
"""

import os
import sys

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get credentials
access_key_id = os.getenv("MINERU_ACCESS_KEY_ID")
secret_access_key = os.getenv("MINERU_SECRET_ACCESS_KEY")

print("=" * 60)
print("MinerU Official API Authentication Test")
print("=" * 60)

# Check if credentials are set
print("\n1. Checking credentials...")
if not access_key_id:
    print("❌ MINERU_ACCESS_KEY_ID is not set in .env file")
    sys.exit(1)
else:
    print(f"✅ MINERU_ACCESS_KEY_ID: {access_key_id[:10]}...{access_key_id[-4:]}")

if not secret_access_key:
    print("❌ MINERU_SECRET_ACCESS_KEY is not set in .env file")
    sys.exit(1)
else:
    print(f"✅ MINERU_SECRET_ACCESS_KEY: {secret_access_key[:10]}...{secret_access_key[-4:]}")

# Test API endpoint
api_base = "https://mineru.net/api/v4"
headers = {
    "Content-Type": "application/json",
    "X-Access-Key-Id": access_key_id,
    "X-Secret-Access-Key": secret_access_key,
}

print(f"\n2. Testing API endpoint: {api_base}")
print(f"   Headers: X-Access-Key-Id, X-Secret-Access-Key")

# Try a simple health check request
test_data = {"url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf", "is_ocr": True}

print("\n3. Sending test request...")
try:
    response = requests.post(f"{api_base}/extract/task", headers=headers, json=test_data, timeout=10)

    print(f"\n4. Response Status: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")

    try:
        response_json = response.json()
        print(f"   Response Body: {response_json}")
    except Exception:
        print(f"   Response Body (text): {response.text[:500]}")

    if response.status_code == 401:
        print("\n❌ Authentication Failed (401 Unauthorized)")
        print("   Possible issues:")
        print("   - Access Key ID or Secret Access Key is incorrect")
        print("   - Keys may have expired")
        print("   - Keys may not have been activated yet")
    elif response.status_code == 403:
        print("\n❌ Permission Denied (403 Forbidden)")
        print("   Your keys are valid but don't have permission for this operation")
    elif response.status_code == 200:
        print("\n✅ Authentication Successful!")
        result = response.json()
        if result.get("code") == 0:
            print("   API is working correctly")
        else:
            print(f"   API returned error: {result.get('msg', 'Unknown error')}")
    else:
        print(f"\n⚠️  Unexpected status code: {response.status_code}")

except requests.exceptions.Timeout:
    print("\n❌ Request timed out")
except requests.exceptions.ConnectionError:
    print("\n❌ Connection error - cannot reach MinerU API")
except Exception as e:
    print(f"\n❌ Error: {str(e)}")

print("\n" + "=" * 60)
print("Test completed")
print("=" * 60)
