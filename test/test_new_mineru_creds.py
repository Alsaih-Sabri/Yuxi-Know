"""
Test script for new MinerU Official API credentials
"""
import requests
import json

# New credentials from the screenshot
ACCESS_KEY_ID = "0gpe1zld1exmnkgzzbay"
SECRET_ACCESS_KEY = "kbyq4lwwzvq8rdmmbpqpgelz1eea3kp10glvoyr7"

API_BASE = "https://mineru.net/api/v4"

def test_new_credentials():
    """Test MinerU Official API with new credentials"""
    
    print("=" * 60)
    print("Testing NEW MinerU Official API Credentials")
    print("=" * 60)
    print(f"\nAccess Key ID: {ACCESS_KEY_ID}")
    print(f"Secret Access Key: {SECRET_ACCESS_KEY[:10]}...")
    print(f"API Base: {API_BASE}")
    print(f"Status: 启用密钥 (Enabled)\n")
    
    headers = {
        "Content-Type": "application/json",
        "X-Access-Key-Id": ACCESS_KEY_ID,
        "X-Secret-Access-Key": SECRET_ACCESS_KEY,
    }
    
    test_data = {
        "url": "https://cdn-mineru.openxlab.org.cn/demo/example.pdf",
        "is_ocr": True
    }
    
    print(f"{'=' * 60}")
    print("Testing Authentication")
    print(f"{'=' * 60}")
    
    try:
        response = requests.post(
            f"{API_BASE}/extract/task",
            headers=headers,
            json=test_data,
            timeout=10
        )
        
        print(f"\n✅ Status Code: {response.status_code}")
        
        try:
            response_json = response.json()
            print(f"\n📋 Response:")
            print(json.dumps(response_json, indent=2, ensure_ascii=False))
            
            if response.status_code == 200 and response_json.get("code") == 0:
                print(f"\n🎉 SUCCESS! MinerU API authentication working!")
                print(f"Task ID: {response_json.get('data', {}).get('task_id', 'N/A')}")
                return True
            elif response.status_code == 401:
                print(f"\n❌ FAILED: Authentication error")
                print(f"Error: {response_json.get('msg', 'Unknown error')}")
                return False
            else:
                print(f"\n⚠️  Unexpected response")
                return False
                
        except Exception as e:
            print(f"\n❌ Response parsing error: {str(e)}")
            print(f"Response Text: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Request failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_new_credentials()
    
    if success:
        print(f"\n{'=' * 60}")
        print("✅ CREDENTIALS ARE VALID!")
        print("Update your .env file with:")
        print(f"MINERU_ACCESS_KEY_ID={ACCESS_KEY_ID}")
        print(f"MINERU_SECRET_ACCESS_KEY={SECRET_ACCESS_KEY}")
        print("Then restart: docker compose restart api")
        print(f"{'=' * 60}")
    else:
        print(f"\n{'=' * 60}")
        print("❌ CREDENTIALS STILL NOT WORKING")
        print("Please check your MinerU account dashboard")
        print(f"{'=' * 60}")
