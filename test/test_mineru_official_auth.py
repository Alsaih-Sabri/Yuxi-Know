"""
Test script to debug MinerU Official API authentication
"""
import os
import requests
import json

# Your credentials
ACCESS_KEY_ID = "3b5wr1jylzdbg9joq7xg"
SECRET_ACCESS_KEY = "kbyq4lwwzvq8rdmmbpqpgelz1eea3kp10glvoyr7"

API_BASE = "https://mineru.net/api/v4"

def test_authentication():
    """Test MinerU Official API authentication"""
    
    print("=" * 60)
    print("Testing MinerU Official API Authentication")
    print("=" * 60)
    print(f"\nAccess Key ID: {ACCESS_KEY_ID}")
    print(f"Secret Access Key: {SECRET_ACCESS_KEY[:10]}...")
    print(f"API Base: {API_BASE}")
    
    # Test with different header combinations
    test_cases = [
        {
            "name": "X-Access-Key-Id and X-Secret-Access-Key",
            "headers": {
                "Content-Type": "application/json",
                "X-Access-Key-Id": ACCESS_KEY_ID,
                "X-Secret-Access-Key": SECRET_ACCESS_KEY,
            }
        },
        {
            "name": "access_key_id and secret_access_key",
            "headers": {
                "Content-Type": "application/json",
                "access_key_id": ACCESS_KEY_ID,
                "secret_access_key": SECRET_ACCESS_KEY,
            }
        },
        {
            "name": "Authorization Bearer",
            "headers": {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ACCESS_KEY_ID}:{SECRET_ACCESS_KEY}",
            }
        },
        {
            "name": "X-API-Key",
            "headers": {
                "Content-Type": "application/json",
                "X-API-Key": ACCESS_KEY_ID,
                "X-API-Secret": SECRET_ACCESS_KEY,
            }
        },
    ]
    
    test_data = {
        "url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
        "is_ocr": True
    }
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'=' * 60}")
        print(f"Test {i}: {test_case['name']}")
        print(f"{'=' * 60}")
        print(f"Headers: {json.dumps(test_case['headers'], indent=2)}")
        
        try:
            response = requests.post(
                f"{API_BASE}/extract/task",
                headers=test_case['headers'],
                json=test_data,
                timeout=10
            )
            
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            try:
                response_json = response.json()
                print(f"Response Body: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
            except:
                print(f"Response Text: {response.text}")
                
        except Exception as e:
            print(f"Error: {str(e)}")
    
    # Try to get API documentation or info endpoint
    print(f"\n{'=' * 60}")
    print("Testing API Info Endpoints")
    print(f"{'=' * 60}")
    
    info_endpoints = [
        "/info",
        "/health",
        "/ping",
        "/v4/info",
        "/extract/info",
    ]
    
    for endpoint in info_endpoints:
        try:
            url = f"{API_BASE}{endpoint}"
            print(f"\nTrying: {url}")
            response = requests.get(url, timeout=5)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_authentication()
