"""
Test if MinerU requires a login/token exchange flow
"""
import requests
import json

ACCESS_KEY_ID = "0gpe1zld1exmnkgzzbay"
SECRET_ACCESS_KEY = "kbyq4lwwzvq8rdmmbpqpgelz1eea3kp10glvoyr7"

API_BASE = "https://mineru.net/api/v4"

def test_login_endpoints():
    """Test various login/auth endpoints"""
    
    print("=" * 60)
    print("Testing MinerU Login/Auth Endpoints")
    print("=" * 60)
    
    # Try different login endpoints
    login_endpoints = [
        "/auth/login",
        "/login",
        "/user/login",
        "/auth/token",
        "/token",
    ]
    
    for endpoint in login_endpoints:
        url = f"{API_BASE}{endpoint}"
        print(f"\n{'=' * 60}")
        print(f"Testing: {url}")
        print(f"{'=' * 60}")
        
        # Try POST with credentials in body
        try:
            data = {
                "access_key_id": ACCESS_KEY_ID,
                "secret_access_key": SECRET_ACCESS_KEY,
            }
            response = requests.post(url, json=data, timeout=5)
            print(f"POST with JSON body - Status: {response.status_code}")
            if response.status_code != 404:
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"POST failed: {str(e)}")
        
        # Try with form data
        try:
            data = {
                "accessKeyId": ACCESS_KEY_ID,
                "secretAccessKey": SECRET_ACCESS_KEY,
            }
            response = requests.post(url, data=data, timeout=5)
            print(f"POST with form data - Status: {response.status_code}")
            if response.status_code != 404:
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"POST form failed: {str(e)}")
    
    # Try the main site login
    print(f"\n{'=' * 60}")
    print("Testing main site endpoints")
    print(f"{'=' * 60}")
    
    main_endpoints = [
        "https://mineru.net/api/auth/login",
        "https://mineru.net/login",
        "https://mineru.net/api/login",
    ]
    
    for url in main_endpoints:
        print(f"\nTrying: {url}")
        try:
            response = requests.post(
                url,
                json={
                    "access_key_id": ACCESS_KEY_ID,
                    "secret_access_key": SECRET_ACCESS_KEY,
                },
                timeout=5
            )
            print(f"Status: {response.status_code}")
            if response.status_code != 404:
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text[:200]}")
        except Exception as e:
            print(f"Error: {str(e)}")

def test_with_cookies():
    """Test if we need to establish a session first"""
    print(f"\n{'=' * 60}")
    print("Testing with session/cookies")
    print(f"{'=' * 60}")
    
    session = requests.Session()
    
    # First, try to get the main page to establish cookies
    try:
        print("\n1. Getting main page to establish session...")
        response = session.get("https://mineru.net/", timeout=5)
        print(f"Status: {response.status_code}")
        print(f"Cookies: {session.cookies.get_dict()}")
    except Exception as e:
        print(f"Error: {str(e)}")
    
    # Now try the API call with the session
    try:
        print("\n2. Trying API call with session cookies...")
        headers = {
            "Content-Type": "application/json",
            "X-Access-Key-Id": ACCESS_KEY_ID,
            "X-Secret-Access-Key": SECRET_ACCESS_KEY,
        }
        response = session.post(
            f"{API_BASE}/extract/task",
            headers=headers,
            json={"url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf", "is_ocr": True},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        try:
            print(f"Response: {response.json()}")
        except:
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_login_endpoints()
    test_with_cookies()
    
    print(f"\n{'=' * 60}")
    print("CONCLUSION:")
    print("If all tests fail, MinerU API might require:")
    print("1. Web-based login first to get session token")
    print("2. Different API endpoint/version")
    print("3. Account activation or payment")
    print("4. Contact MinerU support for correct auth method")
    print(f"{'=' * 60}")
